# Ecommify — Database Design (Proyecto Final)

**Maestría en Arquitectura de Software — Base de Datos I**
**Universidad de La Sabana**

**Grupo E18:**
Jorge Eliecer Rojas Quiñones · David Panesso Sánchez · Juan Esteban Gómez Roa · Fabian Rojas

---

Implementación técnica completa de la capa de datos para **Ecommify**, plataforma
e-commerce basada en el dataset Olist (Brasil). Arquitectura híbrida con
**PostgreSQL** (Supabase) para datos transaccionales y **MongoDB Atlas** para el
módulo analítico de reseñas y geolocalización.

Este repositorio consolida las cuatro entregas del curso. La entrega final agrega
evaluación de rendimiento bajo carga, análisis comparativo PostgreSQL vs MongoDB
y análisis arquitectónico basado en el Teorema CAP.

---

## Estructura del repositorio

```
Ecommify_Database_Design/
│
├── docs/
│   ├── Diagrama/
│   │   └── DiagramaER.svg
│   ├── Presentacion_Ejecutiva.pdf
│   ├── Presentacion_Ejecutiva.pptx
│   └── Informe_Tecnico_Integral.docx
│
├── evidencias/
│   ├── ecommify_comparative_20260620_1818.csv
│   ├── ecommify_comparative_20260620_1818.png
│   ├── mongodb_load_test_20260620_1810.csv
│   ├── mongodb_load_test_20260620_1810.png
│   ├── mongodb_load_test_20260620_1813.csv
│   ├── mongodb_load_test_20260620_1813.png
│   ├── postgresql_load_test_20260620_1757.csv
│   ├── postgresql_load_test_20260620_1757.png
│   ├── postgresql_load_test_20260620_1800.csv
│   └── postgresql_load_test_20260620_1800.png
│
├── mongo/
│   ├── aggregations/
│   │   └── 01_pipeline_sales_analytics.js
│   ├── indexes/
│   │   ├── 01_indexes_orders_reviews.js
│   │   └── 02_indexes_geolocation.js
│   ├── schema/
│   │   ├── geolocation.json
│   │   └── orders_reviews.json          ⚠️ verificar nombre exacto en el repo
│   ├── sharding/
│   │   └── 01_sharding_design.md
│   └── script_video.js
│
├── notebooks/
│   ├── Data_Exploration_Analysis.ipynb
│   ├── load_test_postgresql.py
│   ├── load_test_mongodb.py
│   └── comparative_analysis.py
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
│   ├── indexes/
│   │   └── 07_indexes_postgresql.sql
│   ├── seed_data/
│   │   └── (CSVs del dataset Olist)
│   └── script_video.sql
│
└── README.md
```

> ⚠️ El nombre `orders_reviews.json` arriba asume que el typo histórico
> (`orders_revies.json`) ya fue corregido. Verificar en el repo real antes
> de la entrega; si no se corrigió, renombrar el archivo y actualizar
> cualquier referencia a él.

---

## Nombres reales de tablas/colecciones — nota importante

Durante la ejecución de las pruebas de carga (notebooks) se confirmó contra los
clusters reales:

- Las tablas finales en PostgreSQL se llaman **`orders`** y **`products`**
  (sin sufijo `_v2`) — el renombrado del script 05 ya las dejó así. Solo los
  **índices** conservan el nombre histórico `_v2` (`idx_orders_v2_customer`,
  `idx_products_v2_specifications`, etc.), lo cual es válido y no requiere
  corrección — es un nombre de objeto, no afecta funcionalidad.
- La colección en MongoDB se llama **`orders_reviews`** (no `reviews`).
- La vista materializada `mv_sales_by_category_monthly` usa las columnas
  `category, month, orders_count, revenue, freight_total, avg_ticket`.

Estos nombres ya están reflejados correctamente en `notebooks/load_test_postgresql.py`
y `notebooks/load_test_mongodb.py`.

---

## Arquitectura

```
PostgreSQL (Supabase)                    MongoDB Atlas
  ├── customers, sellers                   ├── geolocation
  ├── orders (delivery_window TSTZRANGE)   │     (índices: zip_code, state+city)
  ├── order_items, order_payments          └── orders_reviews
  ├── products (specifications JSONB,            (índices: order_id, review_score,
  │             photo_urls TEXT[])                score+date compound ESR,
  ├── Vistas materializadas:                      negative reviews partial+compound)
  │   mv_sales_by_category_monthly
  │   mv_customer_segments
  └── Mantenimiento: triggers updated_at, pg_cron
```

PostgreSQL y MongoDB no comparten datos duplicados; se conectan únicamente vía
referencias a nivel de aplicación (`order_id`, `customer_zip_code_prefix`).

---

## Setup — PostgreSQL (Supabase)

### 1. Crear proyecto
[supabase.com](https://supabase.com) → **New project** → región recomendada:
South America o la más cercana disponible en el plan Free.

### 2. Extensiones requeridas

```sql
CREATE EXTENSION IF NOT EXISTS pg_trgm;    -- Búsqueda fuzzy
CREATE EXTENSION IF NOT EXISTS btree_gist; -- GiST sobre tipos base
```

### 3. Ejecutar scripts en orden (SQL Editor de Supabase)

```
postgresql/schema/01 CREACION DE TABLAS ESQUEMA ORIGINAL.sql
postgresql/schema/02 CREACION DE TABLAS CON TIPOS AVANZADOS.sql
postgresql/queries/03 MIGRACIONES A TABLAS CON TIPOS AVANZADOS.sql
postgresql/queries/04. CONSULTAS DE EJEMPLO CON TIPOS AVANZADOS.sql
postgresql/queries/05. DESACOPLAMIENTO ESQUEMA ANTIGUO.sql
postgresql/queries/06. VISTAS MATERIALIZADAS Y MANTENIMIENTO.sql
postgresql/indexes/07_indexes_postgresql.sql
```

### 4. Connection string — usar Session Pooler, no Direct Connection

En Atlas/Supabase → **Connect → Direct** → seleccionar **Session pooler**
(no "Direct connection"). La conexión directa usa IPv6 por defecto, que no es
compatible con entornos como Google Colab. El Session pooler usa IPv4 sin
costo adicional.

```
postgresql://postgres.[PROJECT_REF]:[PASSWORD]@[POOLER_HOST]:5432/postgres
```

---

## Setup — MongoDB Atlas

### 1. Crear cluster
[cloud.mongodb.com](https://cloud.mongodb.com) → **Build a Cluster** → Free (M0)
→ Database name: `ecommify`

### 2. Crear colecciones con validación de esquema

```javascript
// Colección: orders_reviews — copiar mongo/schema/orders_reviews.json
// Colección: geolocation    — copiar mongo/schema/geolocation.json
// Validation Level: Moderate | Validation Action: Warn
```

### 3. Cargar datos y crear índices

```javascript
load("mongo/indexes/01_indexes_orders_reviews.js");
load("mongo/indexes/02_indexes_geolocation.js");

db.orders_reviews.getIndexes();
db.geolocation.getIndexes();
```

### 4. Ejecutar aggregation pipeline

```javascript
load("mongo/aggregations/01_pipeline_sales_analytics.js");
```

### 5. Whitelist de red

Atlas → Network Access → Add IP Address → **Allow Access from Anywhere**
(0.0.0.0/0) — necesario para conectar desde Google Colab.

---

## Decisiones técnicas clave

### PostgreSQL — tipos avanzados

| Tipo | Campo | Justificación |
|---|---|---|
| `JSONB` | `products.product_specifications` | Atributos físicos variables; indexable con GIN |
| `TEXT[]` | `products.photo_urls` | Lista ordenada de URLs |
| `TSTZRANGE` | `orders.delivery_window` | Ventana de entrega; consultas de overlap/contención con GiST |

### PostgreSQL — estrategia de indexación

| Índice | Tipo | Caso de uso |
|---|---|---|
| `idx_orders_v2_customer` | BTree | Filtro por cliente |
| `idx_orders_v2_status` | BTree | Filtro por estado de orden |
| `idx_products_v2_specifications` | GIN | Consultas `@>` sobre JSONB |
| `idx_orders_v2_delivery_window` | GiST | Overlap/contención en TSTZRANGE |
| `idx_products_v2_category_trgm` | GIN trigram | Búsqueda fuzzy (`pg_trgm`) |
| `idx_mv_sales_cat_month` | UNIQUE BTree | Soporte de la vista materializada |

### MongoDB — modelado e indexación

| Colección | Patrón | Índices reales |
|---|---|---|
| `orders_reviews` | Documentos por reseña | `idx_order_id`, `idx_review_score`, `idx_score_date` (compound ESR), `idx_negative_reviews` (partial compound, `review_score <= 2`) |
| `geolocation` | Documento por zip code | `idx_zip_code`, `idx_state_city` (compound) |

> ⚠️ El índice `2dsphere` mencionado en versiones anteriores del README no
> fue confirmado en el cluster actual. Verificar con `db.geolocation.getIndexes()`
> antes de afirmarlo en el informe — si no existe, no incluirlo como evidencia.

---

## Evaluación de rendimiento (Proyecto Final)

Pruebas de carga ejecutadas con 10 threads concurrentes durante 30 segundos
contra los clusters reales (Supabase Session Pooler + MongoDB Atlas M0).
Scripts en `notebooks/`, evidencia completa en `evidencias/`.

### Resultados — PostgreSQL

| Query | Throughput | P50 | Índice |
|---|---|---|---|
| Filtro customer_id | 482.7 q/s | 20.7 ms | BTree |
| Filtro order_status | 481.0 q/s | 21.0 ms | BTree |
| JSONB `@>` | 475.0 q/s | 20.8 ms | GIN |
| TSTZRANGE `@>` | 487.1 q/s | 20.4 ms | GiST |
| **JOIN multi-tabla (en vivo)** | **3.8 q/s** | **2,550 ms** | múltiples (cuello de botella) |
| Vista materializada | 464.1 q/s | 21.4 ms | UNIQUE BTree |

**Hallazgo:** el JOIN en vivo (orders + order_items + order_payments con filtro
`order_status='delivered'`) tarda 2,550 ms porque el filtro no es selectivo
(descarta solo ~3% de las filas). La vista materializada con el mismo cálculo
responde en 21 ms — **mejora de 99.2%**.

### Resultados — MongoDB

| Query | Throughput | P50 | Índice |
|---|---|---|---|
| find order_id | 103.2 q/s | 41.6 ms | Regular |
| find review_score | 103.2 q/s | 43.8 ms | Regular |
| Compound ESR (score=5 + sort fecha) | 103.1 q/s | 42.4 ms | Compound |
| Partial compound (score=2 + sort fecha) | 103.3 q/s | 42.1 ms | Partial compound |
| find zip_code | 103.2 q/s | 40.8 ms | Regular |
| Aggregation pipeline (6 stages) | 38.5 q/s | 251.0 ms | Optimizado |

**Hallazgo 1:** el pipeline con `$match: {review_score: {$gte: 4}}` (77% de la
colección) antes de un `$lookup` tardaba 34,714 ms. Acotando con igualdad
exacta + `$limit(500)` antes del lookup → 251 ms (**mejora 99.3%**).

**Hallazgo 2:** el índice compuesto ESR no elimina el `SORT` en memoria si el
campo de equality se filtra con `$gte` (rango) en vez de igualdad exacta —
la regla ESR exige igualdad antes de range/sort. Confirmado con `explain()`.

### Análisis comparativo

Ver `evidencias/ecommify_comparative_20260620_1818.png/csv` para la tabla de
8 aspectos evaluados (ganador por aspecto + justificación empírica) y el
detalle de 5 cuellos de botella identificados con causa raíz.

---

## Reproducir las pruebas de carga

```python
# En Google Colab
!pip install psycopg2-binary pymongo pandas matplotlib tabulate -q

exec(open("load_test_postgresql.py").read()); run_all()
exec(open("load_test_mongodb.py").read());    run_all()
exec(open("comparative_analysis.py").read()); run()
```

Las credenciales ya están en los scripts (cluster del proyecto). Para un
cluster distinto, editar `DATABASE_URL` (usar Session Pooler) y `MONGO_URI`.

---

## Ejecución del notebook de exploración

1. Abrir [Google Colab](https://colab.research.google.com)
2. Subir `notebooks/Data_Exploration_Analysis.ipynb`
3. Subir los CSVs de `postgresql/seed_data/` cuando se solicite
4. **Runtime → Run all**

Dataset: [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)

---

## Limitaciones del free tier y workarounds

| Sistema | Limitación | Workaround |
|---|---|---|
| Supabase Free | Direct Connection usa IPv6 (incompatible con Colab) | Session Pooler (IPv4) |
| Supabase Free | Sin particionamiento declarativo en UI | Scripts DDL directos |
| Atlas M0 | Sharding no disponible | Diseño teórico en `mongo/sharding/` |
| Atlas M0 | Sin Performance Advisor | `.explain("executionStats")` |
| Atlas M0 | RAM limitada | `allowDiskUse: true` en pipelines |

---

## Documento técnico y presentación

- **Informe Técnico Integral:** `docs/Informe_Tecnico_Integral.docx`
- **Presentación Ejecutiva:** `docs/Presentacion_Ejecutiva.pptx`
- **Video de presentación final (12-15 min):** _(enlace pendiente)_

---

## Autores

Jorge Eliecer Rojas Quiñones · David Panesso Sánchez · Juan Esteban Gómez Roa · Fabian Rojas

**Institución:** Universidad de La Sabana
**Programa:** Maestría en Arquitectura de Software
**Curso:** Base de Datos I — Proyecto Final
