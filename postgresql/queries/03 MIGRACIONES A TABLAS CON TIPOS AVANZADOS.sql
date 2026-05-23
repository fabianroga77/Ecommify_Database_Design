-- =================================================================
-- 03. MIGRACIONES A TABLAS CON TIPOS AVANZADOS
-- =================================================================

-- 01. Inserta la informacion del esquema original products a la tabla con tipos avanzados products_v2
INSERT INTO products_v2 (
    product_id,
    product_category_name,
    product_name_lenght,
    product_description_lenght,
    product_specifications,
    photo_urls
)
SELECT
    product_id,
    product_category_name,
    product_name_lenght,
    product_description_lenght,
    -- Conversión a JSONB
    jsonb_build_object(
        'weight_g', product_weight_g,
        'length_cm', product_length_cm,
        'height_cm', product_height_cm,
        'width_cm', product_width_cm
    ) AS product_specifications,
    -- Array vacío inicialmente
    ARRAY[]::TEXT[] AS photo_urls
FROM products;

-- 02. Inserta la informacion del esquema original orders a la tabla con tipos avanzados orders_v2

INSERT INTO orders_v2 (
    order_id,
    customer_id,
    order_status,
    order_purchase_timestamp,
    order_approved_at,
    delivery_window,
    order_estimated_delivery_date
)
SELECT
    order_id,
    customer_id,
    order_status,
    order_purchase_timestamp,
    order_approved_at,
    CASE
        WHEN order_delivered_carrier_date IS NOT NULL
         AND order_delivered_customer_date IS NOT NULL
         AND order_delivered_carrier_date <= order_delivered_customer_date
        THEN tstzrange(
            order_delivered_carrier_date AT TIME ZONE 'UTC',
            order_delivered_customer_date AT TIME ZONE 'UTC',
            '[]'
        )
        -- Si los datos vienen invertidos, los corrige
        WHEN order_delivered_carrier_date IS NOT NULL
         AND order_delivered_customer_date IS NOT NULL
        THEN tstzrange(
            order_delivered_customer_date AT TIME ZONE 'UTC',
            order_delivered_carrier_date AT TIME ZONE 'UTC',
            '[]'
        )
        -- Si alguna fecha es NULL
        ELSE NULL
    END AS delivery_window,
    order_estimated_delivery_date
FROM orders;
	