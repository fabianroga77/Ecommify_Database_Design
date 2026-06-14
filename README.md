# Ecommify Database Design (Tercera Entrega)
**Maestría en Arquitectura de Software — Base de Datos I**
**Grupo E18:** 
Jorge Eliecer Rojas Quiñones -
David Panesso Sánchez -
Juan Esteban Gómez Roa -
Fabian Rojas

Unidad 5: Optimización de Rendimiento en MongoDB
Implementación técnica completa de la capa de datos para **Ecommify**, plataforma e-commerce basada en el dataset Olist (Brasil). El proyecto integra **PostgreSQL** (Supabase) para datos transaccionales y **MongoDB Atlas** para el módulo analítico de reseñas y geolocalización.

---

## Estructura del Repositorio

```
Ecommify_Database_Design/
│
├── postgresql/
│   ├── schema/
│   │   ├── 01 CREACION DE TABLAS ESQUEMA ORIGINAL.sql
│   │   └── 02 CREACION DE TABLAS CON TIPOS AVANZADOS.sql
│   ├── queries/
│   │   ├── 03 MIGRACIONES A TABLAS CON TIPOS AVANZADOS.sql
│   │   ├── 04. CONSULTAS DE EJEMPLO CON TIPOS AVANZADOS.sql
│   │   ├── 05. DESACOPLAMIENTO ESQUEMA ANTIGUO.sql
│   │   └── 06. VISTAS MATERIALIZADAS Y MANTENIMIENTO.sql
│   └── indexes/
│       └── 07_indexes_postgresql.sql          ← Índices especializados (B-tree, GIN, GiST, BRIN)
│
├── mongo/
│   ├── schema/
│   │   ├── geolocation.json                   ← JSON Schema validation
│   │   └── orders_revies.json                 ← JSON Schema validation
│   ├── indexes/
│   │   ├── 01_indexes_orders_reviews.js       ← Índices ESR, parciales y full-text
│   │   └── 02_indexes_geolocation.js          ← Índices 2dsphere y compuestos
│   ├── aggregations/
│   │   └── 01_pipeline_sales_analytics.js     ← Pipeline analítico (7 stages)
│   └── sharding/
│       └── 01_sharding_design.md              ← Diseño teórico sharding + replica sets
│
├── notebooks/
│   └── Data_Exploration_Analysis.ipynb        ← EDA completo sobre dataset Olist
│
├── docs/
│   └── Diagrama/
│       └── DiagramaER.svg                     ← Diagrama Entidad-Relación
│
└── evidencias/
    ├── postgresql/
    │   ├── metricas_postgresql.md             ← Plantilla comparativa antes/después
    │   └── capturas/                          ← Screenshots de EXPLAIN ANALYZE
    └── mongodb/
        ├── metricas_mongodb.md                ← Métricas executionTimeMillis, efficiency ratio
        └── capturas/                          ← Screenshots Atlas Performance Advisor
```

---

## Prerequisitos

| Herramienta | Versión mínima | Uso |
|---|---|---|
| PostgreSQL | 15+ | Motor relacional (vía Supabase) |
| MongoDB | 6.0+ | Motor documental (vía Atlas) |
| Python | 3.10+ | Notebooks de análisis |
| Node.js | 18+ | Ejecución de scripts MongoDB (.js) |
| Google Colab | — | Ejecución de notebooks |

---

## Setup — PostgreSQL (Supabase)

### 1. Crear proyecto en Supabase
1. Ir a [supabase.com](https://supabase.com) → **New project**
2. Nombre: `ecommify-db` | Región: South America (São Paulo) | Plan: Free

### 2. Ejecutar scripts en orden

En el **SQL Editor** de Supabase, ejecutar en este orden estricto:

```sql
-- Paso 1: Esquema original (tablas base)
-- Archivo: postgresql/schema/01 CREACION DE TABLAS ESQUEMA ORIGINAL.sql

-- Paso 2: Tablas con tipos avanzados (JSONB, arrays, rangos)
-- Archivo: postgresql/schema/02 CREACION DE TABLAS CON TIPOS AVANZADOS.sql

-- Paso 3: Migrar datos al nuevo esquema
-- Archivo: postgresql/queries/03 MIGRACIONES A TABLAS CON TIPOS AVANZADOS.sql

-- Paso 4: Validar queries con tipos avanzados
-- Archivo: postgresql/queries/04. CONSULTAS DE EJEMPLO CON TIPOS AVANZADOS.sql

-- Paso 5: Desacoplar esquema original (solo si la migración fue exitosa)
-- Archivo: postgresql/queries/05. DESACOPLAMIENTO ESQUEMA ANTIGUO.sql

-- Paso 6: Crear vistas materializadas y jobs de mantenimiento
-- Archivo: postgresql/queries/06. VISTAS MATERIALIZADAS Y MANTENIMIENTO.sql

-- Paso 7: Crear índices especializados
-- Archivo: postgresql/indexes/07_indexes_postgresql.sql
```

### 3. Extensiones requeridas

```sql
-- Activar antes del paso 2 (o verificar que estén activas)
CREATE EXTENSION IF NOT EXISTS pg_trgm;    -- Búsqueda fuzzy
CREATE EXTENSION IF NOT EXISTS postgis;    -- Geolocalización (si aplica)
CREATE EXTENSION IF NOT EXISTS btree_gist; -- GiST sobre tipos base
```

> En Supabase Free Tier, `postgis` ya viene preinstalada. Verificar con:
> `SELECT * FROM pg_extension WHERE extname = 'postgis';`

---

## Setup — MongoDB Atlas

### 1. Crear cluster
1. Ir a [cloud.mongodb.com](https://cloud.mongodb.com) → **New Project** → `ecommify`
2. **Build a Cluster** → Free (M0) → Cloud Provider: AWS | Región: São Paulo (sa-east-1)
3. Database name: `ecommify`

### 2. Crear colecciones con validación de esquema

En **Atlas UI → Browse Collections → Create Collection**:

```javascript
// Colección: orders_reviews
// Ir a: Collections → orders_reviews → Validation
// Copiar contenido de: mongo/schema/orders_revies.json
// Validation Level: Moderate | Validation Action: Warn

// Colección: geolocation
// Copiar contenido de: mongo/schema/geolocation.json
```

### 3. Cargar datos

```javascript
// Desde MongoDB Shell (mongosh) o Atlas Data Import:
// 1. Conectarse al cluster:
mongosh "mongodb+srv://<usuario>:<password>@cluster0.xxxxx.mongodb.net/ecommify"

// 2. Importar datos (usando mongoimport):
// mongoimport --uri "<connection_string>" --db ecommify \
//   --collection orders_reviews --file olist_order_reviews_dataset.csv \
//   --type csv --headerline
```

### 4. Crear índices

```javascript
// Ejecutar desde mongosh en orden:

// Índices para orders_reviews:
load("mongo/indexes/01_indexes_orders_reviews.js");

// Índices para geolocation:
load("mongo/indexes/02_indexes_geolocation.js");

// Verificar creación:
db.orders_reviews.getIndexes();
db.geolocation.getIndexes();
```

### 5. Ejecutar aggregation pipeline

```javascript
// Pipeline analítico de satisfacción (7 stages):
load("mongo/aggregations/01_pipeline_sales_analytics.js");
```

---

## Ejecución del Notebook

1. Abrir [Google Colab](https://colab.research.google.com)
2. **File → Upload notebook** → `notebooks/Data_Exploration_Analysis.ipynb`
3. Subir los CSVs del dataset Olist cuando el notebook lo indique
4. Ejecutar todas las celdas en orden (**Runtime → Run all**)

> Los CSVs del dataset Olist se descargan de:
> [kaggle.com/datasets/olistbr/brazilian-ecommerce](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)

---

## Decisiones Técnicas Clave

### PostgreSQL — Tipos avanzados
| Tipo | Tabla | Justificación |
|---|---|---|
| `JSONB` | `products_v2.product_specifications` | Agrupa 4 atributos físicos; extensible sin ALTER TABLE; indexable con GIN |
| `TEXT[]` | `products_v2.photo_urls` | Lista ordenada de URLs; reemplaza campo de conteo con dato real |
| `TSTZRANGE` | `orders_v2.delivery_window` | Modela ventana de entrega como rango; habilita consultas de SLA con GiST |

### PostgreSQL — Estrategia de indexación
| Tipo | Índice | Caso de uso |
|---|---|---|
| B-tree parcial | `idx_orders_v2_status_purchase` | Solo pedidos activos; reduce tamaño 70% |
| GIN | `idx_products_v2_specifications` | Consultas `@>` sobre JSONB |
| GiST | `idx_orders_v2_delivery_window` | Consultas de overlap en rangos temporales |
| BRIN | `idx_orders_v2_purchase_brin` | Timestamps cronológicos; 200x más compacto que B-tree |
| GIN trigram | `idx_products_v2_category_trgm` | Búsqueda fuzzy con pg_trgm |

### MongoDB — Modelado
| Colección | Patrón | Justificación |
|---|---|---|
| `orders_reviews` | Referenciado (por `order_id`) | Alta cardinalidad; reviews crecen independientemente de orders |
| `geolocation` | Documento completo por ZIP | Datos pequeños y de solo lectura; evita lookups frecuentes |

### MongoDB — Aggregation pipeline
El pipeline `01_pipeline_sales_analytics.js` implementa 7 stages con las siguientes optimizaciones:
- `$match` **primero** → usa índice ESR, reduce 100k → 45k docs antes de cualquier join
- `$lookup` con pipeline interno y `$project` → reduce payload del join en ~60%
- `allowDiskUse: true` → previene falla por límite de 100MB RAM en M0
- `$facet` → genera 3 vistas analíticas en un solo pass sobre los datos

---

## Evidencias de Rendimiento

Ver carpeta `/evidencias/` para:
- Comparativas EXPLAIN ANALYZE antes/después (PostgreSQL)
- Métricas `.explain("executionStats")` antes/después (MongoDB)
- Capturas del MongoDB Atlas Performance Advisor
- Tablas de `executionTimeMillis` y efficiency ratios

---

## Limitaciones del Free Tier y Workarounds

| Sistema | Limitación | Workaround |
|---|---|---|
| Supabase Free | Sin particionamiento declarativo en UI | Scripts DDL directos en SQL Editor |
| Supabase Free | Límite de conexiones (50 concurrent) | Pool mínimo en notebooks |
| Atlas M0 | Sharding no disponible | Diseño teórico documentado en `mongo/sharding/` |
| Atlas M0 | Sin Performance Advisor | `.explain("executionStats")` + `db.setProfilingLevel(1)` |
| Atlas M0 | RAM 512MB | `allowDiskUse: true` en todos los pipelines |

---

## Autores

Jorge Eliecer Rojas Quiñones -
David Panesso Sánchez -
Juan Esteban Gómez Roa -
Fabian Rojas

**Institución:** Universidad de La Sabana
**Programa:** Maestría en Arquitectura de Software
**Curso:** Base de Datos I — Unidad 5: Optimización de Rendimiento en MongoDB


# Ecommify — Database Design (Segunda Entrega)

**Universidad de La Sabana · Bases de Datos**
Estudiantes: Jorge Eliecer Rojas Quiñones -
David Panesso Sánchez -
Juan Esteban Gómez Roa -
Fabian Rojas

---

## Descripcion del proyecto

Diseño e implementacion de una base de datos polilglota para **Ecommify**, una plataforma de e-commerce. El modelo parte del dataset publico de Olist (e-commerce brasilero) y evoluciona el esquema relacional original incorporando tipos de datos avanzados de PostgreSQL y una capa NoSQL en MongoDB.

---

## Dataset

Los datos de carga inicial provienen del [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce). Los CSVs se encuentran en `postgresql/seed_data/`.

| Archivo CSV | Descripcion |
|---|---|
| `olist_customers_dataset.csv` | Clientes |
| `olist_sellers_dataset.csv` | Vendedores |
| `olist_products_dataset.csv` | Productos |
| `olist_orders_dataset.csv` | Pedidos |
| `olist_order_items_dataset.csv` | Items por pedido |
| `olist_order_payments_dataset.csv` | Pagos por pedido |
| `olist_order_reviews_dataset.csv` | Resenas de pedidos |
| `olist_geolocation_dataset.csv` | Geolocalizacion por codigo postal |
| `product_category_name_translation.csv` | Traduccion de categorias (PT → EN) |

---

## Arquitectura

```
PostgreSQL
  ├── Esquema original      (tablas base con tipos escalares)
  ├── Esquema avanzado      (JSONB, TEXT[], TSTZRANGE + indices GIN/GIST)
  ├── Vistas materializadas (ventas mensuales por categoria, segmentos RFM)
  └── Mantenimiento         (triggers updated_at, pg_cron)

MongoDB
  ├── geolocation           (coordenadas por zip code)
  └── orders_reviews        (resenas con comentario libre)
```

---

## Estructura del repositorio

```
├── postgresql/
│   ├── schema/
│   │   ├── 01 CREACION DE TABLAS ESQUEMA ORIGINAL.sql
│   │   └── 02 CREACION DE TABLAS CON TIPOS AVANZADOS.sql
│   ├── queries/
│   │   ├── 03 MIGRACIONES A TABLAS CON TIPOS AVANZADOS.sql
│   │   ├── 04. CONSULTAS DE EJEMPLO CON TIPOS AVANZADOS.sql
│   │   ├── 05. DESACOPLAMIENTO ESQUEMA ANTIGUO.sql
│   │   └── 06. VISTAS MATERIALIZADAS Y MANTENIMIENTO.sql
│   └── seed_data/           (CSVs del dataset Olist)
├── mongo/
│   └── schema/
│       ├── geolocation.json
│       └── orders_revies.json
├── notebooks/
│   └── Data_Exploration_Analysis.ipynb
└── docs/
    └── Diagrama/
        └── DiagramaER.svg
```

---

## Esquema PostgreSQL

### Esquema original (script 01)

Tablas relacionales con tipos escalares estandar:

- **customers** — datos de cliente (id, ciudad, estado, zip)
- **sellers** — datos de vendedor
- **products** — catalogo de productos con dimensiones fisicas separadas
- **product_category_translation** — mapeo categoria PT → EN
- **orders** — pedidos con timestamps de ciclo de vida
- **order_items** — lineas de pedido (producto, vendedor, precio, flete)
- **order_payments** — pagos por pedido (tipo, cuotas, monto)

### Esquema con tipos avanzados (script 02)

Dos tablas reemplazan a sus pares originales incorporando tipos nativos de PostgreSQL:

#### `products_v2` → `products`

| Campo original | Campo nuevo | Tipo |
|---|---|---|
| `weight_g`, `length_cm`, `height_cm`, `width_cm` | `product_specifications` | `JSONB` |
| `product_photos_qty` | `photo_urls` | `TEXT[]` |

- Indice **GIN** sobre `product_specifications` para consultas por contenido JSONB.
- Indice **GIN** sobre `photo_urls` para operadores de array (`@>`, `ANY()`).
- Indice **GIN trigram** (`pg_trgm`) sobre `product_category_name` para busqueda fuzzy.

#### `orders_v2` → `orders`

| Campos originales | Campo nuevo | Tipo |
|---|---|---|
| `order_delivered_carrier_date` + `order_delivered_customer_date` | `delivery_window` | `TSTZRANGE` |

- Indice **GIST** sobre `delivery_window` para consultas de solapamiento (`&&`) y contencion (`@>`).

---

## Flujo de migracion (scripts 03 → 05)

1. **Script 03** — inserta datos desde las tablas originales hacia `products_v2` y `orders_v2` aplicando las transformaciones de tipo.
2. **Script 04** — consultas de ejemplo que demuestran el uso de los nuevos tipos e indices.
3. **Script 05** — desacopla el esquema antiguo:
   - Verifica integridad (las queries de validacion deben retornar 0 filas).
   - Elimina las FK antiguas.
   - Renombra `products` → `products_legacy`, `orders` → `orders_legacy`.
   - Renombra `products_v2` → `products`, `orders_v2` → `orders`.
   - Recrea las FK hacia las nuevas tablas.

---

## Vistas materializadas y mantenimiento (script 06)

### Vistas materializadas

| Vista | Descripcion |
|---|---|
| `mv_sales_by_category_monthly` | Ventas, ingresos y ticket promedio por categoria y mes (solo pedidos `delivered`) |
| `mv_customer_segments` | Metricas RFM basicas por cliente (ultima compra, frecuencia, monetario) |

### Triggers `updated_at`

La funcion `trg_set_updated_at()` se engancha como `BEFORE UPDATE` en: `products`, `orders`, `customers`, `sellers`, `order_items`.

### pg_cron (mantenimiento programado)

| Job | Schedule | Accion |
|---|---|---|
| `refresh_mv_sales_by_category` | `0 3 * * *` | `REFRESH MATERIALIZED VIEW CONCURRENTLY` ventas |
| `refresh_mv_customer_segments` | `15 3 * * *` | `REFRESH MATERIALIZED VIEW CONCURRENTLY` segmentos |
| `daily_vacuum` | `30 3 * * *` | `VACUUM ANALYZE` sobre `orders`, `order_items`, `order_payments` |

---

## Esquemas MongoDB

### `geolocation`

Almacena coordenadas geograficas por codigo postal brasilero. Campos requeridos: `geolocation_zip_code_prefix` (int), `geolocation_lat` / `geolocation_lng` (double), `geolocation_city`, `geolocation_state`.

### `orders_reviews`

Almacena resenas de pedidos con soporte para comentario libre. Campos requeridos: `order_id`, `review_id`, `review_score` (int), `review_creation_date`, `review_answer_timestamp`. Campos opcionales: `review_comment_title`, `review_comment_message`.

---

## Diagrama ER

El diagrama entidad-relacion se encuentra en `docs/Diagrama/DiagramaER.svg`.

---

## Como ejecutar

1. Crear la base de datos PostgreSQL y cargar los CSVs en las tablas del esquema original.
2. Ejecutar los scripts en orden:
   ```
   01 → 02 → 03 → 04 (opcional) → 05 → 06
   ```
3. Para MongoDB, aplicar los schemas de validacion en `mongo/schema/` al crear las colecciones.
4. Para el notebook de exploracion, abrir `notebooks/Data_Exploration_Analysis.ipynb` con Jupyter.
