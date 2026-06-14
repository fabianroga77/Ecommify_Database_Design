# Diseño Teórico de Sharding y Replica Sets — Ecommify MongoDB
**Maestría en Arquitectura de Software | Unidad 5**

---

## 1. Contexto y Justificación

Ecommify maneja dos colecciones de alto volumen en MongoDB:

| Colección | Volumen estimado | Crecimiento mensual |
|---|---|---|
| `orders_reviews` | ~100k documentos (dataset Olist) | ~8k docs/mes |
| `geolocation` | ~1M documentos | ~50k docs/mes |

A escala de producción (proyección a 3 años), `geolocation` superaría los 50M de documentos, justificando una estrategia de sharding.

---

## 2. Configuración de Shard Key

### 2.1 Colección `orders_reviews`

**Shard key seleccionada:** `{ order_id: "hashed" }`

**Justificación:**
- `order_id` es el campo de acceso primario en todos los queries analíticos.
- La estrategia **hashed** garantiza distribución uniforme entre shards, evitando hotspots que ocurrirían con una shard key basada en fecha (`review_creation_date`), ya que todas las escrituras del mismo día irían al mismo shard.
- Cardinalidad alta (cada `order_id` es único) → divisible indefinidamente.

**Alternativa descartada:** `{ review_score: 1, review_creation_date: 1 }`
- `review_score` solo tiene 5 valores posibles → jumbo chunks inevitables.

```javascript
// Habilitar sharding en la base de datos
sh.enableSharding("ecommify");

// Crear shard key hash sobre order_id
sh.shardCollection(
  "ecommify.orders_reviews",
  { order_id: "hashed" },
  false,    // unique: false
  { numInitialChunks: 6 }  // 2 chunks por shard inicial (3 shards)
);
```

---

### 2.2 Colección `geolocation`

**Shard key seleccionada:** `{ geolocation_state: 1, geolocation_zip_code_prefix: 1 }`

**Justificación:**
- Sharding por zona geográfica agrupa datos relacionados en el mismo shard → **localidad de datos** para queries regionales.
- `geolocation_state` tiene 27 valores (estados brasileños) → cardinalidad suficiente.
- `geolocation_zip_code_prefix` como segundo campo evita jumbo chunks dentro de un estado.
- Patrón de acceso predominante: `WHERE state = 'SP' AND zip BETWEEN X AND Y` → shard primario sirve el query sin scatter-gather.

```javascript
sh.shardCollection(
  "ecommify.geolocation",
  { geolocation_state: 1, geolocation_zip_code_prefix: 1 }
);
```

---

## 3. Simulación de Distribución de Datos

Con 3 shards y distribución del dataset Olist (~1M docs geolocation):

| Shard | Estados asignados | % Documentos (estimado) |
|---|---|---|
| shard-01 | SP, RJ, ES | ~40% |
| shard-02 | MG, BA, RS, SC, PR | ~35% |
| shard-03 | Resto (20 estados) | ~25% |

> **Nota:** La concentración en SP (~40% de órdenes Olist) podría generar un shard-01 más cargado. Mitigación: usar `zone sharding` para dividir SP en zonas norte/sur por ZIP prefix.

```javascript
// Zone sharding para SP (mitigación de hotspot)
sh.addShardToZone("shard-01a", "SP-norte");
sh.addShardToZone("shard-01b", "SP-sul");

sh.updateZoneKeyRange(
  "ecommify.geolocation",
  { geolocation_state: "SP", geolocation_zip_code_prefix: 1000 },
  { geolocation_state: "SP", geolocation_zip_code_prefix: 9000 },
  "SP-norte"
);
sh.updateZoneKeyRange(
  "ecommify.geolocation",
  { geolocation_state: "SP", geolocation_zip_code_prefix: 9001 },
  { geolocation_state: "SP", geolocation_zip_code_prefix: 99999 },
  "SP-sul"
);
```

---

## 4. Configuración de Replica Set

### 4.1 Topología recomendada

```
PRIMARY (São Paulo)          ← Recibe todas las escrituras
    │
    ├── SECONDARY-1 (São Paulo)   ← Replica síncrona local — failover rápido
    │
    └── SECONDARY-2 (Rio de Janeiro)  ← Replica para DR — latencia ~15ms
         │
         └── HIDDEN / DELAYED (São Paulo)  ← Backup con delay de 1h — protección ante errores humanos
```

Configuración en `mongod`:
```javascript
rs.initiate({
  _id: "ecommifyRS",
  members: [
    { _id: 0, host: "mongo-primary:27017",   priority: 10 },
    { _id: 1, host: "mongo-secondary1:27017", priority: 5  },
    { _id: 2, host: "mongo-secondary2:27017", priority: 1,
      tags: { region: "rj", use: "dr" } },
    { _id: 3, host: "mongo-hidden:27017",
      hidden: true, priority: 0,
      secondaryDelaySecs: 3600  // 1 hora de delay
    }
  ]
});
```

### 4.2 Consideraciones de latencia

| Ruta | Latencia estimada | Impacto |
|---|---|---|
| Primary → Secondary-1 (SP local) | < 2ms | Oplog replication sin impacto perceptible |
| Primary → Secondary-2 (RJ) | ~15ms | Aceptable para DR; no usar en operaciones síncronas |
| Primary → Hidden (SP delay) | < 2ms + 1h delay | Solo para recuperación ante errores |

---

## 5. Estrategias de Read/Write Concern

### 5.1 Write Concern diferenciado por operación

| Operación | Write Concern | Justificación |
|---|---|---|
| Insertar nueva reseña (crítico) | `{ w: "majority", j: true, wtimeout: 5000 }` | Garantiza durabilidad; la reseña no se puede perder |
| Insertar geo batch (ETL) | `{ w: 1, j: false }` | Velocidad sobre durabilidad; datos re-importables |
| Actualizar score calculado | `{ w: 2, j: true }` | Consistencia en 2 nodos antes de confirmar |
| Log de auditoría | `{ w: 0 }` | Fire-and-forget; impacto mínimo en latencia |

```javascript
// Ejemplo: insertar reseña con write concern majority
db.orders_reviews.insertOne(
  { order_id: "abc123", review_score: 5, review_creation_date: "2018-06-01 10:00:00" },
  { writeConcern: { w: "majority", j: true, wtimeout: 5000 } }
);

// Ejemplo: batch ETL de geolocalización con write concern relajado
db.geolocation.insertMany(
  geoBatch,
  { writeConcern: { w: 1, j: false }, ordered: false }
);
```

### 5.2 Read Concern diferenciado por operación

| Operación | Read Concern | Justificación |
|---|---|---|
| Dashboard analítico (reportes) | `"majority"` | Lee datos confirmados por mayoría; evita lecturas de datos revertidos |
| Autocompletar ciudad (UI) | `"local"` | Latencia mínima; datos de geo no cambian frecuentemente |
| Reportes financieros | `"linearizable"` | Garantía máxima de consistencia; acepta latencia alta |
| Monitoreo en tiempo real | `"available"` | Máxima disponibilidad; tolera lecturas stale |

```javascript
// Dashboard analítico
db.orders_reviews.find(
  { review_score: { $lte: 3 } },
  { readConcern: { level: "majority" } }
);

// Autocompletar
db.geolocation.find(
  { geolocation_state: "SP" },
  { readConcern: { level: "local" } }
);
```

---

## 6. Limitaciones del Free Tier y Workarounds

| Limitación (MongoDB Atlas Free M0) | Workaround implementado |
|---|---|
| Sharding no disponible en M0/M2/M5 | Diseño documentado como teórico; validación en Atlas M10+ o local con `mongos` |
| Sin Performance Advisor en M0 | Uso de `.explain("executionStats")` manual + `db.currentOp()` |
| Sin slow query log en M0 | `db.setProfilingLevel(1, { slowms: 100 })` para capturar queries lentas |
| RAM limitada a 512MB en M0 | `allowDiskUse: true` en todos los pipelines; proyecciones tempranas |
| Sin replica set configurable en M0 | Atlas gestiona replica set automáticamente (3 nodos en M0) |

