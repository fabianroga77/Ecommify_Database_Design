import psycopg2
import threading
import time
import statistics
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from tabulate import tabulate
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# ─── CONFIGURACIÓN ───────────────────────────────────────────────────────────
DATABASE_URL = "postgresql://postgres.vahbyjbuikmthdnwawik:basededatos77@aws-1-us-east-2.pooler.supabase.com:5432/postgres"

THREADS      = 10      
DURATION_SEC = 30     
WARMUP_SEC   = 3     

# ─── QUERIES DE PRUEBA ───────────────────────────────────────────────────────
QUERIES = {
    "Q1_customer_btree": {
        "sql": """
            SELECT o.order_id, o.order_status, o.order_purchase_timestamp
            FROM orders o
            WHERE o.customer_id = (
                SELECT customer_id FROM customers LIMIT 1 OFFSET 100
            )
            LIMIT 10;
        """,
        "description": "Filtro por customer_id — índice BTree",
        "index": "idx_orders_v2_customer"
    },
    "Q2_status_btree": {
        "sql": """
            SELECT order_id, order_status, order_purchase_timestamp
            FROM orders
            WHERE order_status = 'delivered'
            LIMIT 50;
        """,
        "description": "Filtro por status — índice BTree",
        "index": "idx_orders_v2_status"
    },
    "Q3_jsonb_gin": {
        "sql": """
            SELECT product_id, product_category_name,
                   product_specifications->>'weight_g' AS weight
            FROM products
            WHERE product_specifications @> '{"weight_g": 500}'::jsonb
            LIMIT 20;
        """,
        "description": "Búsqueda JSONB — índice GIN",
        "index": "idx_products_v2_specifications"
    },
    "Q4_tstzrange_gist": {
        "sql": """
            SELECT order_id, delivery_window
            FROM orders
            WHERE delivery_window @> NOW()::timestamptz
            LIMIT 20;
        """,
        "description": "Rango temporal — índice GiST",
        "index": "idx_orders_v2_delivery_window"
    },
    "Q5_join_multitable": {
        "sql": """
            SELECT
                o.order_id,
                o.order_status,
                COUNT(oi.order_item_id) AS items,
                SUM(op.payment_value)   AS total_paid
            FROM orders o
            JOIN order_items    oi ON o.order_id = oi.order_id
            JOIN order_payments op ON o.order_id = op.order_id
            WHERE o.order_status = 'delivered'
            GROUP BY o.order_id, o.order_status
            ORDER BY total_paid DESC
            LIMIT 20;
        """,
        "description": "JOIN multi-tabla (orders + items + payments)",
        "index": "múltiples índices"
    },
    "Q6_materialized_view": {
        "sql": """
            SELECT category, month, orders_count, revenue
            FROM mv_sales_by_category_monthly
            ORDER BY revenue DESC
            LIMIT 20;
        """,
        "description": "Vista materializada mv_sales_by_category_monthly",
        "index": "idx_mv_sales_cat_month"
    },
}

# ─── RUNNER DE PRUEBA ────────────────────────────────────────────────────────
class QueryRunner:
    def __init__(self, db_url, sql):
        self.db_url   = db_url
        self.sql      = sql
        self.results  = []
        self.errors   = 0
        self._running = False

    def _worker(self):
        try:
            conn = psycopg2.connect(self.db_url)
            conn.autocommit = True
            cur  = conn.cursor()

            # Warmup
            time.sleep(WARMUP_SEC)

            end_time = time.time() + DURATION_SEC
            while self._running and time.time() < end_time:
                t0 = time.perf_counter()
                try:
                    cur.execute(self.sql)
                    cur.fetchall()
                    elapsed_ms = (time.perf_counter() - t0) * 1000
                    self.results.append(elapsed_ms)
                except Exception:
                    self.errors += 1

            cur.close()
            conn.close()
        except Exception as e:
            self.errors += 1

    def run(self, n_threads):
        self._running = True
        threads = [threading.Thread(target=self._worker) for _ in range(n_threads)]
        for t in threads:
            t.start()
        time.sleep(WARMUP_SEC + DURATION_SEC + 1)
        self._running = False
        for t in threads:
            t.join(timeout=5)

    def stats(self):
        if not self.results:
            return None
        r = sorted(self.results)
        return {
            "count":       len(r),
            "throughput":  round(len(r) / DURATION_SEC, 1),
            "mean_ms":     round(statistics.mean(r), 2),
            "median_ms":   round(statistics.median(r), 2),
            "p95_ms":      round(r[int(len(r) * 0.95)], 2),
            "p99_ms":      round(r[int(len(r) * 0.99)], 2),
            "min_ms":      round(min(r), 2),
            "max_ms":      round(max(r), 2),
            "errors":      self.errors,
        }

# ─── EXPLAIN ANTES / DESPUÉS ─────────────────────────────────────────────────
EXPLAIN_QUERIES = {
    "Q1_customer_btree": {
        "before": """
            EXPLAIN (ANALYZE, FORMAT TEXT)
            SELECT order_id, order_status
            FROM orders
            WHERE customer_id = '8d50f5eadf50201ccdcedfb9e2ac8455';
        """,
        "after_idx": "idx_orders_v2_customer",
    },
    "Q3_jsonb_gin": {
        "before": """
            EXPLAIN (ANALYZE, FORMAT TEXT)
            SELECT product_id FROM products_v2
            WHERE product_specifications @> '{"weight_g": 500}'::jsonb;
        """,
        "after_idx": "idx_products_v2_specifications",
    },
}

# ─── EJECUCIÓN PRINCIPAL ─────────────────────────────────────────────────────
def run_all():
    print("=" * 70)
    print(f"  Ecommify — PostgreSQL Load Test")
    print(f"  Threads: {THREADS}  |  Duration: {DURATION_SEC}s  |  {datetime.now():%Y-%m-%d %H:%M}")
    print("=" * 70)

    all_stats = {}

    for name, q in QUERIES.items():
        print(f"\n▶ {name}: {q['description']}")
        runner = QueryRunner(DATABASE_URL, q["sql"])
        runner.run(THREADS)
        s = runner.stats()
        if s:
            all_stats[name] = {**s, "description": q["description"], "index": q["index"]}
            print(f"   Throughput: {s['throughput']} q/s  |  P50: {s['median_ms']} ms  |  P95: {s['p95_ms']} ms  |  Errores: {s['errors']}")
        else:
            print(f"   ❌ Sin resultados (verificar conexión o tabla)")

    # ─── TABLA RESUMEN ────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("  RESUMEN DE RESULTADOS")
    print("=" * 70)

    rows = []
    for name, s in all_stats.items():
        rows.append([
            name,
            s["description"][:40],
            f"{s['throughput']} q/s",
            f"{s['median_ms']} ms",
            f"{s['p95_ms']} ms",
            f"{s['p99_ms']} ms",
            s["errors"],
        ])

    headers = ["Query", "Descripción", "Throughput", "P50", "P95", "P99", "Errores"]
    print(tabulate(rows, headers=headers, tablefmt="grid"))

    # ─── GRÁFICA ─────────────────────────────────────────────────────────────
    if all_stats:
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))
        fig.suptitle("Ecommify — PostgreSQL Load Test (10 threads, 30s)", fontsize=13, fontweight="bold")

        names  = list(all_stats.keys())
        labels = [n.replace("_", "\n") for n in names]
        tput   = [all_stats[n]["throughput"] for n in names]
        p50    = [all_stats[n]["median_ms"]  for n in names]
        p95    = [all_stats[n]["p95_ms"]     for n in names]

        colors = ["#2E75B6", "#336699", "#1F3864", "#00B0F0", "#13AA52", "#375623"]

        ax1 = axes[0]
        bars = ax1.bar(labels, tput, color=colors[:len(names)], edgecolor="white")
        ax1.set_title("Throughput (queries/segundo)", fontweight="bold")
        ax1.set_ylabel("q/s")
        ax1.tick_params(axis="x", labelsize=8)
        for bar, val in zip(bars, tput):
            ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                     f"{val}", ha="center", va="bottom", fontsize=8)

        ax2 = axes[1]
        x = range(len(names))
        ax2.bar([i - 0.2 for i in x], p50, width=0.35, label="P50 (median)", color="#2E75B6")
        ax2.bar([i + 0.2 for i in x], p95, width=0.35, label="P95", color="#C00000")
        ax2.set_title("Latencia P50 vs P95 (ms)", fontweight="bold")
        ax2.set_ylabel("ms")
        ax2.set_xticks(list(x))
        ax2.set_xticklabels(labels, fontsize=8)
        ax2.legend()

        plt.tight_layout()
        fname = f"postgresql_load_test_{datetime.now():%Y%m%d_%H%M}.png"
        plt.savefig(fname, dpi=150, bbox_inches="tight")
        print(f"\n📊 Gráfica guardada: {fname}")

    # ─── CSV ─────────────────────────────────────────────────────────────────
    df = pd.DataFrame(all_stats).T
    csv_name = f"postgresql_load_test_{datetime.now():%Y%m%d_%H%M}.csv"
    df.to_csv(csv_name)
    print(f"📄 CSV guardado: {csv_name}")

    return all_stats

if __name__ == "__main__":
    run_all()
