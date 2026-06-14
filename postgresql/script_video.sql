-- BTree - customer_id
DROP INDEX IF EXISTS idx_orders_v2_customer;

EXPLAIN ANALYZE
SELECT *
FROM orders
WHERE customer_id = (
    SELECT customer_id
    FROM orders
    WHERE customer_id IS NOT NULL
    LIMIT 1
);

CREATE INDEX idx_orders_v2_customer
ON orders(customer_id);

EXPLAIN ANALYZE
SELECT *
FROM orders
WHERE customer_id = (
    SELECT customer_id
    FROM orders
    WHERE customer_id IS NOT NULL
    LIMIT 1
);

-- GiST - Rangos

DROP INDEX IF EXISTS idx_orders_v2_delivery_window;

EXPLAIN ANALYZE
SELECT *
FROM orders
WHERE delivery_window &&
tstzrange(
    '2020-01-01',
    '2020-02-01'
);

CREATE INDEX idx_orders_v2_delivery_window
ON orders
USING GIST(delivery_window);

EXPLAIN ANALYZE
SELECT *
FROM orders
WHERE delivery_window &&
tstzrange(
    '2020-01-01',
    '2020-02-01'
);


-- GIN / pg_trgm

DROP INDEX IF EXISTS idx_products_v2_category_trgm;

EXPLAIN ANALYZE
SELECT *
FROM products
WHERE product_category_name % 'pc_gamer';

CREATE INDEX idx_products_v2_category_trgm
ON products
USING GIN(product_category_name gin_trgm_ops);

EXPLAIN ANALYZE
SELECT *
FROM products
WHERE product_category_name % 'pc_gamer';


SELECT product_category_name, count(1)
FROM products group by product_category_name
