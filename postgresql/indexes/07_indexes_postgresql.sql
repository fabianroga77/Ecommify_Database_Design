-- =================================================================
-- 07. ÍNDICES ESPECIALIZADOS — PostgreSQL (Supabase)
-- Ecommify | Maestría en Arquitectura de Software
-- =================================================================
-- Estrategia de indexación con justificación técnica.
-- Validar con: EXPLAIN ANALYZE <query>
-- Tipos usados: B-tree, GIN, GiST, BRIN
-- =================================================================

-- -----------------------------------------------------------------
-- 1. ÍNDICE B-TREE COMPUESTO — orders_v2
--    Caso de uso: filtrar pedidos entregados en un rango de fechas.
--    Columnas: (order_status, order_purchase_timestamp)
--    Regla: columna de baja cardinalidad primero (status ~5 valores)
--    seguida de timestamp para aprovechamiento de rango.
--    Sin este índice: SEQSCAN sobre ~100k filas.
-- -----------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_orders_v2_status_purchase
    ON orders_v2 (order_status, order_purchase_timestamp DESC)
    WHERE order_status IN ('delivered', 'shipped');

COMMENT ON INDEX idx_orders_v2_status_purchase IS
    'B-tree parcial: solo pedidos activos (delivered/shipped). '
    'Reduce tamaño ~70% vs índice completo. '
    'Soporta query: WHERE status = ''delivered'' AND purchase_ts BETWEEN x AND y';

-- -----------------------------------------------------------------
-- 2. ÍNDICE GIN — products_v2.product_specifications (JSONB)
--    Permite consultas @>, ?, ?|, ?& sobre el objeto JSONB.
--    Caso de uso: buscar productos por atributos físicos específicos.
--    Ya definido en schema 02 — se documenta aquí con justificación.
-- -----------------------------------------------------------------
-- Ya existe: idx_products_v2_specifications (GIN sobre product_specifications)
-- EXPLAIN ANALYZE SELECT * FROM products_v2
--   WHERE product_specifications @> '{"weight_g": 500}';
-- Resultado esperado: Bitmap Index Scan on idx_products_v2_specifications

-- -----------------------------------------------------------------
-- 3. ÍNDICE GiST — orders_v2.delivery_window (TSTZRANGE)
--    Habilita operadores de rango: @>, &&, <@
--    Caso de uso: encontrar pedidos cuya ventana de entrega
--    se superpone con una fecha específica (SLA analysis).
--    Ya definido en schema 02 — documentado aquí.
-- -----------------------------------------------------------------
-- Ya existe: idx_orders_v2_delivery_window (GiST sobre delivery_window)
-- EXPLAIN ANALYZE SELECT * FROM orders_v2
--   WHERE delivery_window && tstzrange('2018-06-01', '2018-06-30');
-- Resultado esperado: Index Scan using idx_orders_v2_delivery_window

-- -----------------------------------------------------------------
-- 4. ÍNDICE BRIN — orders_v2.order_purchase_timestamp
--    Recomendado para tablas muy grandes con datos insertados
--    en orden cronológico (correlación natural con bloques de disco).
--    BRIN ocupa ~200x menos espacio que B-tree para timestamps secuenciales.
--    Caso de uso: reports históricos que escanean rangos amplios de fechas.
-- -----------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_orders_v2_purchase_brin
    ON orders_v2 USING BRIN (order_purchase_timestamp)
    WITH (pages_per_range = 32);

COMMENT ON INDEX idx_orders_v2_purchase_brin IS
    'BRIN sobre timestamp de compra. '
    'Asume inserción cronológica (datos históricos Olist). '
    'Ocupa ~100KB vs ~8MB de B-tree equivalente. '
    'Útil para reports de rango amplio (por año/semestre).';

-- -----------------------------------------------------------------
-- 5. ÍNDICE GIN — pg_trgm sobre product_category_name
--    Habilita búsqueda fuzzy (LIKE '%term%', similitud %)
--    Caso de uso: buscador de categorías con tolerancia a errores tipográficos.
--    Ya definido en schema 02 — documentado aquí.
-- -----------------------------------------------------------------
-- Ya existe: idx_products_v2_category_trgm (GIN trigram)
-- EXPLAIN ANALYZE SELECT * FROM products_v2
--   WHERE product_category_name % 'beleza';
-- Resultado esperado: Bitmap Index Scan on idx_products_v2_category_trgm

-- -----------------------------------------------------------------
-- 6. ÍNDICE COMPUESTO — order_items para queries de revenue
--    Caso de uso crítico: cálculo de ingresos por seller y producto.
--    Query frecuente en reportes de comisiones.
-- -----------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_order_items_seller_product_price
    ON order_items (seller_id, product_id, price DESC);

COMMENT ON INDEX idx_order_items_seller_product_price IS
    'B-tree compuesto para queries de revenue por vendedor. '
    'Cubre: SELECT seller_id, SUM(price) FROM order_items '
    'WHERE seller_id = X GROUP BY product_id ORDER BY price DESC. '
    'Index-only scan posible si se agrega freight_value al INCLUDE.';

-- Versión con INCLUDE para habilitar Index-Only Scan
CREATE INDEX IF NOT EXISTS idx_order_items_seller_revenue_covering
    ON order_items (seller_id, product_id)
    INCLUDE (price, freight_value);

COMMENT ON INDEX idx_order_items_seller_revenue_covering IS
    'Covering index: incluye price y freight_value para evitar heap fetch. '
    'Habilita Index-Only Scan en queries de revenue — elimina acceso a tabla.';

-- -----------------------------------------------------------------
-- 7. ÍNDICE PARCIAL B-TREE — order_payments tipo crédito
--    Solo indexa pagos con tarjeta de crédito (tipo más frecuente).
--    Caso de uso: análisis de cuotas y riesgo crediticio.
-- -----------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_payments_credit_installments
    ON order_payments (order_id, payment_installments DESC)
    WHERE payment_type = 'credit_card';

COMMENT ON INDEX idx_payments_credit_installments IS
    'Índice parcial: solo pagos credit_card (~75% del volumen). '
    'Soporta análisis de cuotas: WHERE payment_type = ''credit_card'' '
    'AND payment_installments > 1 ORDER BY installments DESC.';

-- =================================================================
-- VALIDACIÓN — Ejecutar EXPLAIN ANALYZE para comparar antes/después
-- =================================================================

-- Q1: Pedidos entregados en 2018 (usa idx_orders_v2_status_purchase)
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT order_id, customer_id, order_purchase_timestamp
FROM orders_v2
WHERE order_status = 'delivered'
  AND order_purchase_timestamp BETWEEN '2018-01-01' AND '2018-12-31';

-- Q2: Productos con peso > 500g (usa idx_products_v2_specifications GIN)
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT product_id, product_category_name
FROM products_v2
WHERE (product_specifications->>'weight_g')::int > 500
ORDER BY product_category_name;

-- Q3: Revenue por seller (usa idx_order_items_seller_revenue_covering)
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT seller_id,
       SUM(price)          AS revenue,
       SUM(freight_value)  AS freight,
       COUNT(*)            AS items
FROM order_items
WHERE seller_id = '3442f8959a84dea7ee197c632cb2df15'
GROUP BY seller_id;

-- Q4: Pagos a cuotas con tarjeta (usa idx_payments_credit_installments)
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT order_id, payment_installments, payment_value
FROM order_payments
WHERE payment_type = 'credit_card'
  AND payment_installments > 3
ORDER BY payment_installments DESC;
