from pymongo import MongoClient
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
MONGO_URI  = "mongodb+srv://ecommify_user:16yIqU2uU9Us@ecommify.00axlib.mongodb.net/"
DB_NAME    = "ecommify"

THREADS      = 10
DURATION_SEC = 30
WARMUP_SEC   = 3

def q1_find_order_id(db):
    list(db.orders_reviews.find({"order_id": "e481f51cbdc54678b7cc49136f2d6af7"}).limit(5))

def q2_find_review_score(db):
    list(db.orders_reviews.find({"review_score": 5}).limit(20))

def q3_compound_esr(db):
    list(db.orders_reviews.find(
        {"review_score": 5},
        sort=[("review_creation_date", -1)]
    ).limit(20))

def q4_partial_index(db):
    list(db.orders_reviews.find(
        {"review_score": 2},
        sort=[("review_creation_date", -1)]
    ).limit(50))

def q5_zip_code(db):
    list(db.geolocation.find(
        {"geolocation_zip_code_prefix": 1001}
    ).limit(10))

def q6_aggregation_pipeline(db):
    pipeline = [
        {"$match": {"review_score": 5}},
        {"$limit": 500},
        {"$lookup": {
            "from": "geolocation",
            "localField": "customer_zip_code_prefix",
            "foreignField": "geolocation_zip_code_prefix",
            "as": "geo_info"
        }},
        {"$unwind": {"path": "$geo_info", "preserveNullAndEmptyArrays": True}},
        {"$group": {
            "_id": "$review_score",
            "total_reviews": {"$sum": 1},
            "avg_score": {"$avg": "$review_score"}
        }},
        {"$addFields": {
            "performance_label": {
                "$cond": [{"$gte": ["$avg_score", 4.5]}, "Excelente", "Bueno"]
            }
        }},
        {"$sort": {"total_reviews": -1}}
    ]
    list(db.orders_reviews.aggregate(pipeline))

OPERATIONS = {
    "Q1_find_order_id": {
        "fn":          q1_find_order_id,
        "description": "find() por order_id — índice regular",
        "index":       "idx_order_id",
        "expected":    "IXSCAN",
    },
    "Q2_find_review_score": {
        "fn":          q2_find_review_score,
        "description": "find() por review_score — índice regular",
        "index":       "idx_review_score",
        "expected":    "IXSCAN",
    },
    "Q3_compound_ESR": {
        "fn":          q3_compound_esr,
        "description": "Compuesto ESR {score, date} — SORT eliminado",
        "index":       "idx_score_date",
        "expected":    "IXSCAN sin SORT",
    },
    "Q4_partial_index": {
        "fn":          q4_partial_index,
        "description": "Índice parcial compuesto reviews <= 2 — SORT eliminado",
        "index":       "idx_negative_reviews",
        "expected":    "IXSCAN partial sin SORT",
    },
    "Q5_zip_code": {
        "fn":          q5_zip_code,
        "description": "find() geolocation por zip_code",
        "index":       "idx_zip_code",
        "expected":    "IXSCAN",
    },
    "Q6_aggregation": {
        "fn":          q6_aggregation_pipeline,
        "description": "Aggregation pipeline 6 stages ($lookup + $group)",
        "index":       "pipeline optimizado",
        "expected":    "IXSCAN → $lookup → $group",
    },
}

# ─── RUNNER ──────────────────────────────────────────────────────────────────
class MongoRunner:
    def __init__(self, uri, db_name, fn):
        self.uri     = uri
        self.db_name = db_name
        self.fn      = fn
        self.results = []
        self.errors  = 0
        self._running = False

    def _worker(self):
        try:
            client = MongoClient(self.uri, serverSelectionTimeoutMS=5000)
            db     = client[self.db_name]

            time.sleep(WARMUP_SEC)

            end_time = time.time() + DURATION_SEC
            while self._running and time.time() < end_time:
                t0 = time.perf_counter()
                try:
                    self.fn(db)
                    self.results.append((time.perf_counter() - t0) * 1000)
                except Exception:
                    self.errors += 1

            client.close()
        except Exception:
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
            "count":      len(r),
            "throughput": round(len(r) / DURATION_SEC, 1),
            "mean_ms":    round(statistics.mean(r), 2),
            "median_ms":  round(statistics.median(r), 2),
            "p95_ms":     round(r[int(len(r) * 0.95)], 2),
            "p99_ms":     round(r[int(len(r) * 0.99)], 2),
            "min_ms":     round(min(r), 2),
            "max_ms":     round(max(r), 2),
            "errors":     self.errors,
        }

# ─── EXPLAIN PLAN CHECKER ────────────────────────────────────────────────────
def check_explain_plans(uri, db_name):
    """Verifica que los planes de ejecución usen IXSCAN, no COLLSCAN"""
    print("\n" + "=" * 70)
    print("  VERIFY — Planes de ejecución (explain)")
    print("=" * 70)

    client = MongoClient(uri)
    db     = client[db_name]

    checks = [
        {
            "name":    "reviews — order_id",
            "explain": db.orders_reviews.find(
                {"order_id": "e481f51cbdc54678b7cc49136f2d6af7"}
            ).explain()
        },
        {
            "name":    "reviews — score + date (ESR compound, igualdad exacta)",
            "explain": db.orders_reviews.find(
                {"review_score": 5},
                sort=[("review_creation_date", -1)]
            ).explain()
        },
        {
            "name":    "reviews — negative (idx_negative_reviews, parcial)",
            "explain": db.orders_reviews.find(
                {"review_score": 2},
                sort=[("review_creation_date", -1)]
            ).explain()
        },
        {
            "name":    "geolocation — zip_code",
            "explain": db.geolocation.find(
                {"geolocation_zip_code_prefix": 1001}
            ).explain()
        },
    ]

    rows = []
    for c in checks:
        try:
            stage = c["explain"]["queryPlanner"]["winningPlan"].get("stage", "?")
            # Bajar un nivel si hay FETCH wrapping IXSCAN
            if stage == "FETCH":
                input_stage = c["explain"]["queryPlanner"]["winningPlan"].get("inputStage", {})
                stage = f"FETCH → {input_stage.get('stage', '?')}"
            ok = "IXSCAN" in stage
            rows.append([c["name"], stage, "✅ OK" if ok else "❌ COLLSCAN"])
        except Exception as e:
            rows.append([c["name"], "ERROR", str(e)])

    print(tabulate(rows, headers=["Query", "Stage", "Status"], tablefmt="grid"))
    client.close()

# ─── EJECUCIÓN PRINCIPAL ─────────────────────────────────────────────────────
def run_all():
    print("=" * 70)
    print(f"  Ecommify — MongoDB Atlas Load Test")
    print(f"  Threads: {THREADS}  |  Duration: {DURATION_SEC}s  |  {datetime.now():%Y-%m-%d %H:%M}")
    print("=" * 70)

    # Verificar conexión
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        client.server_info()
        db = client[DB_NAME]
        colls = db.list_collection_names()
        print(f"\n✅ Conectado a Atlas. Colecciones: {colls}")
        client.close()
    except Exception as e:
        print(f"\n❌ Error de conexión: {e}")
        return

    # Verificar planes de ejecución primero
    check_explain_plans(MONGO_URI, DB_NAME)

    # Pruebas de carga
    all_stats = {}
    for name, op in OPERATIONS.items():
        print(f"\n▶ {name}: {op['description']}")
        runner = MongoRunner(MONGO_URI, DB_NAME, op["fn"])
        runner.run(THREADS)
        s = runner.stats()
        if s:
            all_stats[name] = {**s, "description": op["description"], "expected": op["expected"]}
            print(f"   Throughput: {s['throughput']} q/s  |  P50: {s['median_ms']} ms  |  P95: {s['p95_ms']} ms  |  Errores: {s['errors']}")
        else:
            print(f"   ❌ Sin resultados (verificar colección)")

    # ─── TABLA RESUMEN ────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("  RESUMEN DE RESULTADOS")
    print("=" * 70)

    rows = []
    for name, s in all_stats.items():
        rows.append([
            name,
            s["description"][:38],
            f"{s['throughput']} q/s",
            f"{s['median_ms']} ms",
            f"{s['p95_ms']} ms",
            s["errors"],
        ])

    print(tabulate(rows, headers=["Query", "Descripción", "Throughput", "P50", "P95", "Errores"], tablefmt="grid"))

    # ─── GRÁFICA ─────────────────────────────────────────────────────────────
    if all_stats:
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))
        fig.suptitle("Ecommify — MongoDB Load Test (10 threads, 30s)", fontsize=13, fontweight="bold")

        names  = list(all_stats.keys())
        labels = [n.replace("_", "\n") for n in names]
        tput   = [all_stats[n]["throughput"] for n in names]
        p50    = [all_stats[n]["median_ms"]  for n in names]
        p95    = [all_stats[n]["p95_ms"]     for n in names]

        colors = ["#13AA52", "#0D8A3E", "#065A2A", "#00C76F", "#008844", "#004422"]

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
        ax2.bar([i - 0.2 for i in x], p50, width=0.35, label="P50 (median)", color="#13AA52")
        ax2.bar([i + 0.2 for i in x], p95, width=0.35, label="P95", color="#C00000")
        ax2.set_title("Latencia P50 vs P95 (ms)", fontweight="bold")
        ax2.set_ylabel("ms")
        ax2.set_xticks(list(x))
        ax2.set_xticklabels(labels, fontsize=8)
        ax2.legend()

        plt.tight_layout()
        fname = f"mongodb_load_test_{datetime.now():%Y%m%d_%H%M}.png"
        plt.savefig(fname, dpi=150, bbox_inches="tight")
        print(f"\n📊 Gráfica guardada: {fname}")

    # ─── CSV ─────────────────────────────────────────────────────────────────
    df = pd.DataFrame(all_stats).T
    csv_name = f"mongodb_load_test_{datetime.now():%Y%m%d_%H%M}.csv"
    df.to_csv(csv_name)
    print(f"📄 CSV guardado: {csv_name}")

    return all_stats

if __name__ == "__main__":
    run_all()
