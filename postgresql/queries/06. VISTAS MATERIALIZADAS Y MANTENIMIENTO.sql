-- =================================================================
-- 06. VISTAS MATERIALIZADAS Y MANTENIMIENTO
-- =================================================================

-- 1.1  Ventas mensuales por categoria
-- Soporta dashboards de tendencias por categoria + mes.
-- Source: order_items + products_v2 + orders_v2 + product_category_translation
DROP MATERIALIZED VIEW IF EXISTS mv_sales_by_category_monthly;

CREATE MATERIALIZED VIEW mv_sales_by_category_monthly AS
SELECT
    pct.product_category_name_english       AS category,
    DATE_TRUNC('month', o.order_purchase_timestamp)::date AS month,
    COUNT(DISTINCT o.order_id)              AS orders_count,
    SUM(oi.price)                            AS revenue,
    SUM(oi.freight_value)                    AS freight_total,
    AVG(oi.price)                            AS avg_ticket
FROM   order_items oi
JOIN   orders o                ON o.order_id = oi.order_id
JOIN   products p              ON p.product_id = oi.product_id
LEFT JOIN product_category_translation pct
       ON pct.product_category_name = p.product_category_name
WHERE  o.order_status = 'delivered'
GROUP BY 1, 2;

CREATE UNIQUE INDEX idx_mv_sales_cat_month
    ON mv_sales_by_category_monthly (category, month);


-- 1.2  Segmentos RFM basicos de clientes
-- Soporta dashboards de marketing y segmentacion.
DROP MATERIALIZED VIEW IF EXISTS mv_customer_segments;

CREATE MATERIALIZED VIEW mv_customer_segments AS
SELECT
    c.customer_id,
    c.customer_unique_id,
    MAX(o.order_purchase_timestamp)::date    AS last_purchase,
    COUNT(DISTINCT o.order_id)               AS frequency,
    SUM(oi.price + oi.freight_value)         AS monetary
FROM   customers c
JOIN   orders o   ON o.customer_id = c.customer_id
JOIN   order_items oi ON oi.order_id = o.order_id
WHERE  o.order_status = 'delivered'
GROUP BY c.customer_id, c.customer_unique_id;

CREATE UNIQUE INDEX idx_mv_customer_segments
    ON mv_customer_segments (customer_id);


-- =================================================================
-- 2. TRIGGERS updated_at
-- =================================================================
-- La funcion trg_set_updated_at() ya esta definida en 02_advanced_types.sql
-- Aqui se enganchan en las tablas modificables.

-- Columna updated_at en tablas originales que la necesitan
ALTER TABLE customers    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();
ALTER TABLE sellers      ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();
ALTER TABLE order_items  ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

DROP TRIGGER IF EXISTS trg_customers_updated_at   ON customers;
DROP TRIGGER IF EXISTS trg_sellers_updated_at     ON sellers;
DROP TRIGGER IF EXISTS trg_order_items_updated_at ON order_items;

CREATE TRIGGER trg_customers_updated_at
    BEFORE UPDATE ON customers
    FOR EACH ROW EXECUTE FUNCTION trg_set_updated_at();

CREATE TRIGGER trg_sellers_updated_at
    BEFORE UPDATE ON sellers
    FOR EACH ROW EXECUTE FUNCTION trg_set_updated_at();

CREATE TRIGGER trg_order_items_updated_at
    BEFORE UPDATE ON order_items
    FOR EACH ROW EXECUTE FUNCTION trg_set_updated_at();

-- =================================================================
-- 3. MANTENIMIENTO PROGRAMADO CON pg_cron
-- =================================================================
-- pg_cron permite agendar jobs directamente dentro de PostgreSQL.
-- En Supabase se habilita desde el dashboard (Database > Extensions).
-- Sintaxis cron: minuto hora dia mes dia_semana
-- =================================================================

CREATE EXTENSION IF NOT EXISTS pg_cron;

-- 3.1  Refresh diario de vistas materializadas
-- Se ejecuta a las 03:00 todos los dias (baja carga).
SELECT cron.schedule(
    'refresh_mv_sales_by_category',
    '0 3 * * *',
    $$ REFRESH MATERIALIZED VIEW CONCURRENTLY mv_sales_by_category_monthly; $$
);

SELECT cron.schedule(
    'refresh_mv_customer_segments',
    '15 3 * * *',
    $$ REFRESH MATERIALIZED VIEW CONCURRENTLY mv_customer_segments; $$
);

-- 3.2  VACUUM ANALYZE diario sobre tablas con mayor tasa de cambio
-- Mantiene estadisticas frescas para el planner y libera tuplas muertas.
SELECT cron.schedule(
    'daily_vacuum',
    '30 3 * * *',
    $$ VACUUM ANALYZE orders_v2;
       VACUUM ANALYZE order_items;
       VACUUM ANALYZE order_payments; $$
);

-- 3.3  Consultas para inspeccionar los jobs programados:
SELECT * FROM cron.job;
SELECT * FROM cron.job_run_details ORDER BY start_time DESC LIMIT 20;