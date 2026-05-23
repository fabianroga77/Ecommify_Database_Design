# Ecommify — Database Design (Segunda Entrega)

**Universidad de La Sabana · Bases de Datos**
Estudiantes: 0000393177 · 0000393134 · 0000399159 · 0000393714

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
