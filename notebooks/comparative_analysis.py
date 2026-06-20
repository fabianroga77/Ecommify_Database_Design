import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from tabulate import tabulate
from datetime import datetime
import glob
import os

USE_REFERENCE_DATA = False

POSTGRESQL_CSV = sorted(glob.glob("postgresql_load_test_*.csv"))[-1] if glob.glob("postgresql_load_test_*.csv") else None
MONGODB_CSV    = sorted(glob.glob("mongodb_load_test_*.csv"))[-1]    if glob.glob("mongodb_load_test_*.csv")    else None

REFERENCE_PG = {
    "Q1_customer_btree":   {"throughput": 482.7, "median_ms": 20.72,   "p95_ms": 22.06,   "errors": 0},
    "Q2_status_btree":     {"throughput": 481.0, "median_ms": 20.99,   "p95_ms": 22.02,   "errors": 0},
    "Q3_jsonb_gin":        {"throughput": 475.0, "median_ms": 20.81,   "p95_ms": 22.69,   "errors": 0},
    "Q4_tstzrange_gist":   {"throughput": 487.1, "median_ms": 20.35,   "p95_ms": 21.80,   "errors": 0},
    "Q5_join_multitable":  {"throughput": 3.8,   "median_ms": 2550.17, "p95_ms": 3813.59, "errors": 0},
    "Q6_materialized_view":{"throughput": 464.1, "median_ms": 21.42,   "p95_ms": 22.66,   "errors": 0},
}

REFERENCE_MG = {
    "Q1_find_order_id":    {"throughput": 103.1, "median_ms": 40.69, "p95_ms": 612.62, "errors": 0},
    "Q2_find_review_score":{"throughput": 103.2, "median_ms": 39.71, "p95_ms": 615.75, "errors": 0},
    "Q3_compound_ESR":     {"throughput": 103.1, "median_ms": 43.62, "p95_ms": 595.39, "errors": 0},
    "Q4_partial_index":    {"throughput": 103.1, "median_ms": 43.30, "p95_ms": 597.80, "errors": 0},
    "Q5_zip_code":         {"throughput": 103.0, "median_ms": 42.19, "p95_ms": 598.66, "errors": 0},
    "Q6_aggregation":      {"throughput": 32.2,  "median_ms": 269.94,"p95_ms": 553.66, "errors": 0},
}

# ─── CARGA DE DATOS ──────────────────────────────────────────────────────────
def load_data():
    if USE_REFERENCE_DATA or not POSTGRESQL_CSV or not MONGODB_CSV:
        print("📌 Usando datos de referencia (free tier — Colombia → AWS Oregon us-west-2)")
        pg = pd.DataFrame(REFERENCE_PG).T
        mg = pd.DataFrame(REFERENCE_MG).T
    else:
        print(f"📂 Cargando: {POSTGRESQL_CSV}")
        print(f"📂 Cargando: {MONGODB_CSV}")
        pg = pd.read_csv(POSTGRESQL_CSV, index_col=0)
        mg = pd.read_csv(MONGODB_CSV, index_col=0)
    return pg, mg

# ─── TABLA COMPARATIVA ───────────────────────────────────────────────────────
def print_comparative_table(pg, mg):
    print("\n" + "=" * 80)
    print("  TABLA COMPARATIVA — PostgreSQL vs MongoDB (10 threads, 30s)")
    print("=" * 80)

    rows = [
        # [ Aspecto, PG valor, MG valor, Ganador, Justificación ]
        ["Consultas indexadas simples",
         f"{pg.loc['Q1_customer_btree','throughput']:.0f} q/s",
         f"{mg.loc['Q1_find_order_id','throughput']:.0f} q/s",
         "PostgreSQL (4.7x)",
         "Session Pooler de Supabase + BTree muy eficiente en queries puntuales"],
        ["Latencia P50 — query simple",
         f"{pg.loc['Q1_customer_btree','median_ms']:.1f} ms",
         f"{mg.loc['Q1_find_order_id','median_ms']:.1f} ms",
         "PostgreSQL",
         "~21ms vs ~41ms — diferencia de driver/pooling, no del modelo de datos"],
        ["Búsqueda JSONB / documentos",
         f"{pg.loc['Q3_jsonb_gin','throughput']:.0f} q/s",
         f"{mg.loc['Q3_compound_ESR','throughput']:.0f} q/s",
         "PostgreSQL",
         "GIN sobre JSONB compite directamente con el modelo nativo de Mongo"],
        ["JOINs multi-tabla (en vivo)",
         f"{pg.loc['Q5_join_multitable','throughput']:.1f} q/s",
         "No aplica (sin joins nativos)",
         "Cuello de botella PG",
         "2,550ms promedio — degrada 65x vs queries indexadas simples"],
        ["Aggregation analítica compleja",
         f"{pg.loc['Q6_materialized_view','throughput']:.0f} q/s (vista mat.)",
         f"{mg.loc['Q6_aggregation','throughput']:.1f} q/s (pipeline)",
         "PostgreSQL*",
         "*Vista materializada precomputa — comparación no es 1:1 con pipeline ad-hoc"],
        ["Mismo cálculo, vivo vs precomputado",
         f"JOIN {pg.loc['Q5_join_multitable','median_ms']:.0f}ms → Vista {pg.loc['Q6_materialized_view','median_ms']:.0f}ms",
         f"$match amplio 34,714ms → optimizado {mg.loc['Q6_aggregation','median_ms']:.0f}ms",
         "Empate (mismo patrón)",
         "Ambos motores mejoran ~99% con la optimización correcta (vista / filtro selectivo)"],
        ["Estabilidad bajo concurrencia (10 threads)",
         "0 errores en 5/6 queries",
         "0 errores en 6/6 queries",
         "Empate",
         "Ambos clusters free tier soportaron 10 threads sin caídas"],
        ["Degradación bajo carga (P95/P50)",
         f"{round(pg.loc['Q5_join_multitable','p95_ms']/pg.loc['Q5_join_multitable','median_ms'],1)}x JOIN en vivo",
         f"{round(mg.loc['Q1_find_order_id','p95_ms']/mg.loc['Q1_find_order_id','median_ms'],1)}x incluso en query simple",
         "Contexto distinto",
         "MongoDB tiene latencia de red base más alta (Atlas) en todas las queries"],
    ]

    print(tabulate(rows,
                   headers=["Aspecto", "PostgreSQL", "MongoDB", "Ganador", "Justificación"],
                   tablefmt="grid"))

# ─── CUELLOS DE BOTELLA ──────────────────────────────────────────────────────
def print_bottlenecks(pg, mg):
    print("\n" + "=" * 80)
    print("  CUELLOS DE BOTELLA IDENTIFICADOS")
    print("=" * 80)

    bottlenecks = [
        ["🔴 CRÍTICO",  "PostgreSQL",
         "JOIN multi-tabla en vivo (Q5)",
         f"P50={pg.loc['Q5_join_multitable','median_ms']:.0f}ms, P95={pg.loc['Q5_join_multitable','p95_ms']:.0f}ms — 65x más lento que queries indexadas simples. EXPLAIN ANALYZE confirmó Merge Join escaneando ~96K filas de orders + ~104K de order_payments por el filtro order_status='delivered' que solo descarta 2,963 de ~99K filas (no selectivo)",
         "Vista materializada mv_sales_by_category_monthly: mismo cálculo en 21ms (mejora 99.2%)"],
        ["🔴 CRÍTICO (resuelto)",  "MongoDB",
         "Aggregation pipeline con $match no selectivo (Q6)",
         "Causa raíz: $match: {review_score: {$gte: 4}} devolvía 76,470 de 99,000 docs (77%) antes del $lookup, multiplicando el costo del join. Medido: 34,714ms con $gte amplio",
         "$match con igualdad exacta (review_score=5) + $limit(500) antes del $lookup: 270ms (mejora 99.2%)"],
        ["🟡 RESUELTO",  "MongoDB",
         "Índice compuesto ESR no eliminaba el SORT (Q3, Q4)",
         "Causa raíz: filtrar con $gte (rango) en el campo de igualdad de un índice {score,date} no permite a Mongo usar el orden del índice para el sort — la regla ESR exige igualdad exacta antes del sort, no rango",
         "Cambiar a igualdad exacta (review_score=5 / review_score=2): SORT eliminado, confirmado con explain()"],
        ["🟢 MENOR", "Ambos",
         "Latencia de red base Colombia → clusters free tier",
         "PostgreSQL (Supabase, Session Pooler, us-east-2): ~20ms base. MongoDB (Atlas M0): ~40ms base, P95 sube a ~600ms en todas las queries incluso las bien indexadas",
         "Migrar a región más cercana (sa-east-1) o upgrade a tier dedicado reduciría la brecha"],
        ["🟢 MENOR",    "Supabase",
         "Direct Connection usa IPv6 (incompatible con Colab)",
         "Conexión directa falló inicialmente; Colab no soporta IPv6 nativo",
         "Usar Session Pooler (IPv4 proxied) — sin costo adicional en free tier"],
    ]

    print(tabulate(bottlenecks,
                   headers=["Severidad", "Motor", "Cuello de botella", "Evidencia", "Mitigación"],
                   tablefmt="grid"))

# ─── GRÁFICA COMPARATIVA ─────────────────────────────────────────────────────
def plot_comparison(pg, mg):
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle("Ecommify — Análisis Comparativo PostgreSQL vs MongoDB\n(10 threads concurrentes, 30 segundos, free tier)",
                 fontsize=13, fontweight="bold")

    # ── 1. Throughput side by side ──
    ax = axes[0, 0]
    pg_tput = list(pg["throughput"].astype(float))
    mg_tput = list(mg["throughput"].astype(float))
    pg_labels = [l.replace("Q", "PG-Q").replace("_", "\n") for l in pg.index]
    mg_labels = [l.replace("Q", "MG-Q").replace("_", "\n") for l in mg.index]
    x1 = np.arange(len(pg_tput))
    x2 = np.arange(len(mg_tput)) + len(pg_tput) + 1

    bars1 = ax.bar(x1, pg_tput, color="#2E75B6", label="PostgreSQL", alpha=0.85)
    bars2 = ax.bar(x2, mg_tput, color="#13AA52", label="MongoDB",    alpha=0.85)
    ax.set_title("Throughput por query (q/s)", fontweight="bold")
    ax.set_ylabel("queries / segundo")
    ax.set_xticks(list(x1) + list(x2))
    ax.set_xticklabels(pg_labels + mg_labels, fontsize=7)
    ax.legend()
    ax.axvline(x=len(pg_tput) - 0.5 + 0.5, color="gray", linestyle="--", linewidth=0.8)
    for bar, val in zip(list(bars1) + list(bars2), pg_tput + mg_tput):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                str(val), ha="center", va="bottom", fontsize=7)

    # ── 2. Latencia P50 vs P95 PostgreSQL ──
    ax = axes[0, 1]
    p50 = pg["median_ms"].astype(float)
    p95 = pg["p95_ms"].astype(float)
    x = np.arange(len(pg.index))
    ax.bar(x - 0.2, p50, 0.35, label="P50", color="#2E75B6")
    ax.bar(x + 0.2, p95, 0.35, label="P95", color="#C00000")
    ax.set_title("PostgreSQL — Latencia P50 vs P95 (ms)", fontweight="bold")
    ax.set_ylabel("ms")
    ax.set_xticks(x)
    ax.set_xticklabels([l.replace("_", "\n") for l in pg.index], fontsize=8)
    ax.legend()

    # ── 3. Latencia P50 vs P95 MongoDB ──
    ax = axes[1, 0]
    p50 = mg["median_ms"].astype(float)
    p95 = mg["p95_ms"].astype(float)
    x = np.arange(len(mg.index))
    ax.bar(x - 0.2, p50, 0.35, label="P50", color="#13AA52")
    ax.bar(x + 0.2, p95, 0.35, label="P95", color="#C00000")
    ax.set_title("MongoDB — Latencia P50 vs P95 (ms)", fontweight="bold")
    ax.set_ylabel("ms")
    ax.set_xticks(x)
    ax.set_xticklabels([l.replace("_", "\n") for l in mg.index], fontsize=8)
    ax.legend()

    # ── 4. Degradación bajo carga (P95/P50 ratio) ──
    ax = axes[1, 1]
    pg_ratio = (pg["p95_ms"] / pg["median_ms"]).astype(float)
    mg_ratio = (mg["p95_ms"] / mg["median_ms"]).astype(float)

    all_labels = (
        [f"PG-{l}" for l in pg.index] +
        [f"MG-{l}" for l in mg.index]
    )
    all_ratios = list(pg_ratio) + list(mg_ratio)
    all_colors = ["#2E75B6"] * len(pg_ratio) + ["#13AA52"] * len(mg_ratio)

    bars = ax.bar(range(len(all_labels)), all_ratios, color=all_colors, alpha=0.85)
    ax.axhline(y=2.0, color="orange", linestyle="--", linewidth=1, label="Degradación 2x (alerta)")
    ax.axhline(y=3.0, color="red",    linestyle="--", linewidth=1, label="Degradación 3x (crítico)")
    ax.set_title("Degradación bajo carga (ratio P95/P50)", fontweight="bold")
    ax.set_ylabel("P95 / P50")
    ax.set_xticks(range(len(all_labels)))
    ax.set_xticklabels([l.replace("_", "\n") for l in all_labels], fontsize=6)
    ax.legend(fontsize=8)

    pg_patch = mpatches.Patch(color="#2E75B6", label="PostgreSQL")
    mg_patch = mpatches.Patch(color="#13AA52", label="MongoDB")
    ax.legend(handles=[pg_patch, mg_patch] + ax.get_legend_handles_labels()[0][2:], fontsize=8)

    plt.tight_layout()
    fname = f"ecommify_comparative_{datetime.now():%Y%m%d_%H%M}.png"
    plt.savefig(fname, dpi=150, bbox_inches="tight")
    print(f"\n📊 Gráfica comparativa guardada: {fname}")
    return fname

# ─── REPORTE FINAL CSV ───────────────────────────────────────────────────────
def export_report(pg, mg):
    combined = pd.DataFrame({
        "Motor":       ["PostgreSQL"] * len(pg) + ["MongoDB"] * len(mg),
        "Query":       list(pg.index) + list(mg.index),
        "Throughput":  list(pg["throughput"]) + list(mg["throughput"]),
        "P50_ms":      list(pg["median_ms"])  + list(mg["median_ms"]),
        "P95_ms":      list(pg["p95_ms"])     + list(mg["p95_ms"]),
        "Errores":     list(pg["errors"])     + list(mg["errors"]),
    })
    fname = f"ecommify_comparative_{datetime.now():%Y%m%d_%H%M}.csv"
    combined.to_csv(fname, index=False)
    print(f"📄 Reporte CSV guardado: {fname}")

# ─── MAIN ─────────────────────────────────────────────────────────────────────
def run():
    print("=" * 80)
    print(f"  Ecommify — Análisis Comparativo Final")
    print(f"  {datetime.now():%Y-%m-%d %H:%M}")
    print("=" * 80)

    pg, mg = load_data()

    print("\n📋 PostgreSQL — resumen:")
    print(pg[["throughput","median_ms","p95_ms","errors"]].to_string())

    print("\n📋 MongoDB — resumen:")
    print(mg[["throughput","median_ms","p95_ms","errors"]].to_string())

    print_comparative_table(pg, mg)
    print_bottlenecks(pg, mg)
    plot_comparison(pg, mg)
    export_report(pg, mg)

    print("\n✅ Análisis comparativo completado.")

if __name__ == "__main__":
    run()
