// =================================================================
// 02. ÍNDICES — Colección: geolocation
// Ecommify | Maestría en Arquitectura de Software
// =================================================================
// Colección con datos de geolocalización por ZIP code.
// Prioridad: búsquedas por estado + ciudad + coordenadas.
// =================================================================

// ------------------------------------------------------------------
// 1. ÍNDICE COMPUESTO ESR
//    Caso de uso: buscar zonas de entrega por estado (Equality),
//    ordenar por ciudad (Sort), filtrar coordenadas (Range).
//    Soporta el módulo de logística y cobertura geográfica.
// ------------------------------------------------------------------
db.geolocation.createIndex(
  {
    geolocation_state: 1,          // E — Equality: filtro por estado (SP, RJ, etc.)
    geolocation_city: 1,           // S — Sort: orden alfabético por ciudad
    geolocation_zip_code_prefix: 1 // R — Range: rangos de ZIP para cobertura
  },
  {
    name: "idx_geo_state_city_zip",
    background: true,
    comment: "ESR: state(E) + city(S) + zip(R). Consultas de cobertura logística por región."
  }
);

// ------------------------------------------------------------------
// 2. ÍNDICE 2DSPHERE — Consultas geoespaciales
//    Permite queries como $near, $geoWithin, $geoIntersects.
//    Requiere que lat/lng estén en formato GeoJSON o campos separados.
//    Caso de uso: encontrar vendedores/clientes cercanos a un punto.
// ------------------------------------------------------------------
db.geolocation.createIndex(
  { location: "2dsphere" },
  {
    name: "idx_geo_2dsphere",
    background: true,
    comment: "Índice geoespacial 2dsphere. Requiere campo 'location' en formato GeoJSON Point."
  }
);

// ------------------------------------------------------------------
// 3. ÍNDICE PARCIAL — Solo estados con alto volumen (SP, RJ, MG)
//    Justificación: el 65% de órdenes Olist provienen de SP, RJ y MG.
//    Reduce índice a 1/3 del tamaño manteniendo cobertura del caso más frecuente.
// ------------------------------------------------------------------
db.geolocation.createIndex(
  { geolocation_zip_code_prefix: 1, geolocation_city: 1 },
  {
    name: "idx_geo_zip_city_high_volume_partial",
    partialFilterExpression: {
      geolocation_state: { $in: ["SP", "RJ", "MG"] }
    },
    background: true,
    comment: "Índice parcial: solo estados SP/RJ/MG (65% del volumen). Optimiza lookup frecuente."
  }
);

// ------------------------------------------------------------------
// 4. ÍNDICE DE TEXTO — Búsqueda por nombre de ciudad
//    Caso de uso: autocompletar en formularios de dirección.
// ------------------------------------------------------------------
db.geolocation.createIndex(
  { geolocation_city: "text" },
  {
    name: "idx_geo_city_text",
    default_language: "portuguese",
    comment: "Full-text sobre ciudad. Soporta autocompletar y búsqueda aproximada de localidades."
  }
);

// ------------------------------------------------------------------
// VALIDACIÓN
// ------------------------------------------------------------------
// db.geolocation.explain("executionStats").find({ geolocation_state: "SP", geolocation_zip_code_prefix: { $gte: 1000, $lte: 5000 } })
// db.geolocation.getIndexes()
