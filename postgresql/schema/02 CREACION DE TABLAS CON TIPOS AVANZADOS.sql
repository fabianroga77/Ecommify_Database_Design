-- =================================================================
-- 02. CREACION DE TABLAS CON TIPOS AVANZADOS
-- =================================================================


-- 1. products_v2  (reemplaza products)
-- =================================================================
-- Transformaciones:
--   weight_g + length_cm + height_cm + width_cm  --> product_specifications (JSONB)
--   (URLs de imagenes)                            --> photo_urls (TEXT[])
-- Campos sin transformacion: product_id, product_category_name,
-- product_name_lenght, product_description_lenght (se mantienen).
-- product_photos_qty se ELIMINA porque queda implicito en
-- cardinality(photo_urls).
-- =================================================================

CREATE TABLE products_v2 (
    product_id                  VARCHAR(50)   PRIMARY KEY,
    product_category_name       VARCHAR(100),
    product_name_lenght         INT,
    product_description_lenght  INT,
    -- JSONB: agrupa los 4 atributos fisicos originales en un solo objeto.
    -- Permite extension futura (color, material, etc.) sin ALTER TABLE.
    product_specifications      JSONB         NOT NULL DEFAULT '{}'::jsonb,
    -- TEXT[]: URLs reales de las imagenes del producto, ordenadas.
    -- Reemplaza product_photos_qty (cantidad) como una lista
    photo_urls                  TEXT[]        NOT NULL DEFAULT '{}',
    created_at                  TIMESTAMPTZ   DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ   DEFAULT NOW()
);

COMMENT ON COLUMN products_v2.product_specifications IS
  'Objeto JSONB con dimensiones fisicas: {"weight_g":INT, "length_cm":NUM, "height_cm":NUM, "width_cm":NUM}. Indexado con GIN para consultas por contenido.';

COMMENT ON COLUMN products_v2.photo_urls IS
  'Array de URLs de imagenes del producto. TEXT[] preserva orden y soporta operadores @> y ANY(). Reemplaza product_photos_qty (la cantidad ahora es cardinality(photo_urls)).';

-- Indices que aprovechan los tipos avanzados
CREATE INDEX idx_products_v2_specifications
    ON products_v2 USING GIN (product_specifications);

CREATE INDEX idx_products_v2_photo_urls
    ON products_v2 USING GIN (photo_urls);

-- Trigger updated_at
create or replace
function public.trg_set_updated_at()
 returns trigger
 language plpgsql
as $function$
begin
    NEW.updated_at = NOW();
return new;
end;
$function$;

CREATE TRIGGER trg_products_v2_updated_at
    BEFORE UPDATE ON products_v2
    FOR EACH ROW EXECUTE FUNCTION trg_set_updated_at();
   

-- 2. orders_v2  (reemplaza orders)
-- =================================================================
-- Transformaciones:
--   delivered_carrier_date + delivered_customer_date  --> delivery_window (TSTZRANGE)
--   payment_type + installments + value (origen: order_payments)
--                                                      --> payment_details (JSONB array)
-- Campos sin transformacion: order_id, customer_id, order_status,
-- order_purchase_timestamp, order_approved_at,
-- order_estimated_delivery_date (se mantienen).
-- =================================================================

CREATE TABLE orders_v2 (
    order_id                       VARCHAR(50)   PRIMARY KEY,
    customer_id                    VARCHAR(50)   NOT NULL,
    order_status                   VARCHAR(20),
    order_purchase_timestamp       TIMESTAMP,
    order_approved_at              TIMESTAMP,
    -- TSTZRANGE: ventana de entrega [carrier .. customer].
    -- Soporta operadores @> (contains), && (overlap) con indice GIST.
    delivery_window                TSTZRANGE,
    order_estimated_delivery_date  TIMESTAMP,
    updated_at                     TIMESTAMPTZ   DEFAULT NOW(),

    CONSTRAINT fk_orders_v2_customer
        FOREIGN KEY (customer_id)
        REFERENCES customers(customer_id)
);

COMMENT ON COLUMN orders_v2.delivery_window IS
  'Ventana temporal de entrega [delivered_carrier_date .. delivered_customer_date]. TSTZRANGE permite consultas con @>, &&, y agregaciones de SLA con indice GIST.';

-- Indices avanzados
CREATE INDEX idx_orders_v2_delivery_window
    ON orders_v2 USING GIST (delivery_window);

-- Indices de soporte para queries frecuentes
CREATE INDEX idx_orders_v2_customer
    ON orders_v2 (customer_id);

CREATE INDEX idx_orders_v2_status
    ON orders_v2 (order_status);

CREATE INDEX idx_orders_v2_purchase_ts
    ON orders_v2 (order_purchase_timestamp);

-- Trigger updated_at
CREATE TRIGGER trg_orders_v2_updated_at
    BEFORE UPDATE ON orders_v2
    FOR EACH ROW EXECUTE FUNCTION trg_set_updated_at();


  -- =================================================================
-- 3. Extensiones requeridas
-- =================================================================
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Indice GIN trigram para busqueda fuzzy en categorias de producto
CREATE INDEX IF NOT EXISTS idx_products_v2_category_trgm
    ON products_v2 USING GIN (product_category_name gin_trgm_ops);