// =================================================================
// 01. ÍNDICES — Colección: orders_reviews
// Ecommify | Maestría en Arquitectura de Software
// =================================================================
// Regla ESR aplicada: Equality → Sort → Range
// Validar con: db.orders_reviews.explain("executionStats")
// =================================================================

// ------------------------------------------------------------------
// 1. ÍNDICE COMPUESTO ESR
//    Caso de uso: filtrar reseñas por score (Equality),
//    ordenar por fecha de creación (Sort) y filtrar por rango de fecha (Range).
//    Soporta queries analíticas de satisfacción de clientes.
// ------------------------------------------------------------------
db.orders_reviews.createIndex(
  {
    review_score: 1,               // E — Equality: filtros exactos por calificación
    review_creation_date: 1,       // S — Sort: orden cronológico
    review_answer_timestamp: 1     // R — Range: ventana de respuesta
  },
  {
    name: "idx_reviews_score_created_answered",
    background: true,
    comment: "ESR: score(E) + creation_date(S) + answer_timestamp(R). Soporta dashboard de satisfacción."
  }
);

// ------------------------------------------------------------------
// 2. ÍNDICE PARCIAL
//    Solo indexa reseñas con score <= 3 (reseñas negativas).
//    Reduce tamaño del índice en ~60% vs. índice completo.
//    Caso de uso: módulo de atención al cliente que solo procesa
//    reseñas negativas para seguimiento.
// ------------------------------------------------------------------
db.orders_reviews.createIndex(
  { review_creation_date: 1, order_id: 1 },
  {
    name: "idx_reviews_negative_partial",
    partialFilterExpression: { review_score: { $lte: 3 } },
    background: true,
    comment: "Índice parcial: solo reseñas negativas (score <= 3). Reduce footprint ~60%."
  }
);

// ------------------------------------------------------------------
// 3. ÍNDICE DE TEXTO (Full-Text Search)
//    Soporta búsqueda sobre comentarios y títulos de reseñas.
//    Caso de uso: análisis de sentimiento y búsqueda por palabras clave.
// ------------------------------------------------------------------
db.orders_reviews.createIndex(
  {
    review_comment_title: "text",
    review_comment_message: "text"
  },
  {
    name: "idx_reviews_fulltext",
    weights: {
      review_comment_title: 10,      // Título tiene mayor peso que el cuerpo
      review_comment_message: 5
    },
    default_language: "portuguese",
    comment: "Full-text: título(w=10) + mensaje(w=5). Idioma portugués (dataset Olist Brasil)."
  }
);

// ------------------------------------------------------------------
// 4. ÍNDICE COMPUESTO — order_id + review_score
//    Caso de uso: lookup desde orders → reviews en pipelines de agregación.
//    Evita COLLSCAN al hacer $lookup por order_id.
// ------------------------------------------------------------------
db.orders_reviews.createIndex(
  { order_id: 1, review_score: -1 },
  {
    name: "idx_reviews_order_score",
    background: true,
    comment: "Soporta $lookup desde colección orders y filtros combinados order+score."
  }
);

// ------------------------------------------------------------------
// VALIDACIÓN — Ejecutar después de crear índices
// ------------------------------------------------------------------
// db.orders_reviews.explain("executionStats").find({ review_score: { $lte: 3 } })
// db.orders_reviews.explain("executionStats").find({ $text: { $search: "produto ruim" } })
// db.orders_reviews.getIndexes()
