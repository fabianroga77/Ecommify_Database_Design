-- =================================================================
-- 04. CONSULTAS DE EJEMPLO CON TIPOS AVANZADOS
-- =================================================================

-- Q1) Productos con peso > 1000g (usa indice GIN sobre JSONB):
     SELECT product_id
     FROM   products_v2
     WHERE  (product_specifications->>'weight_g')::int > 1000;

-- Q2) Productos con al menos 3 fotos (usa cardinality):
     SELECT product_id
     FROM   products_v2
     WHERE  cardinality(photo_urls) >= 3;

-- Q3) Pedidos entregados durante una ventana especifica (usa GIST):
     SELECT order_id
     FROM   orders_v2
     WHERE  delivery_window && tstzrange('2018-01-01','2018-02-01');

-- Q4) Busqueda fuzzy de categoria (usa pg_trgm):
     SELECT DISTINCT product_category_name
     FROM   products_v2
     WHERE  product_category_name % 'beleza';