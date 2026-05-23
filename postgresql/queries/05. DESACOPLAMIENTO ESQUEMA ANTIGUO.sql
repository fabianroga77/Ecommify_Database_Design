-- =================================================================
-- 05. DESACOPLAMIENTO ESQUEMA ANTIGUO
-- =================================================================

-- 01 Consultas para verificar que los datos migraron correctamente, deben retornar 0 rows
SELECT oi.product_id
FROM order_items oi
LEFT JOIN products_v2 p
    ON p.product_id = oi.product_id
WHERE p.product_id IS NULL;


SELECT oi.order_id
FROM order_items oi
LEFT JOIN orders_v2 o
    ON o.order_id = oi.order_id
WHERE o.order_id IS NULL;


SELECT op.order_id
FROM order_payments op
LEFT JOIN orders_v2 o
    ON o.order_id = op.order_id
WHERE o.order_id IS NULL;


-- 02 Eliminar foreign keys antiguas
ALTER TABLE order_items
DROP CONSTRAINT fk_order_items_product;

ALTER TABLE order_items
DROP CONSTRAINT fk_order_items_order;

ALTER TABLE order_payments
DROP CONSTRAINT fk_order_payments_order;

ALTER TABLE orders
DROP CONSTRAINT fk_orders_customer;


-- 03 Renombrar esquema antiguo
ALTER TABLE products RENAME TO products_legacy;
ALTER TABLE orders RENAME TO orders_legacy;


-- 04 Renombrar esquema nuevo para tener los nombres originales
ALTER TABLE products_v2 RENAME TO products;
ALTER TABLE orders_v2 RENAME TO orders;


-- 05 Crear nuevas FKs hacia V2
ALTER TABLE order_items
ADD CONSTRAINT fk_order_items_product
FOREIGN KEY (product_id)
REFERENCES products(product_id);

ALTER TABLE order_items
ADD CONSTRAINT fk_order_items_order
FOREIGN KEY (order_id)
REFERENCES orders(order_id);

ALTER TABLE order_payments
ADD CONSTRAINT fk_order_payments_order
FOREIGN KEY (order_id)
REFERENCES orders(order_id);