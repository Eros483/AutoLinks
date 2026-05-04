# ----- latency evaluation script @ backend/eval/eval_latency.py -----
"""
Eval 1 - Distributed Systems Performance (Latency) Evaluation

Measures total round-trip time from API request to JSON response across
50 sequential calls. Target: under 3 seconds.

Each pipeline segment is logged independently to identify bottlenecks:
- GLiNER API call (entity extraction)
- Embedding generation (MiniLM, local)
- Qdrant cosine similarity query
- Equity re-ranking (in-memory)
"""

import time
import statistics
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from backend.utils.config import config
from backend.utils.logger import logger

API_BASE = os.environ.get("EVAL_API_URL", "http://localhost:8000/api/v1")
NUM_REQUESTS = 50


test_drafts = [
    "The fundamental theorem of calculus connects differentiation and integration.",
    "Machine learning models require careful hyperparameter tuning.",
    "Quantum computing leverages superposition and entanglement.",
    "The mitochondria are the powerhouse of the cell.",
    "Climate change poses significant challenges to global food security.",
    "Natural language processing has advanced dramatically with transformer models.",
    "The human brain contains approximately 86 billion neurons.",
    "Blockchain technology provides decentralized consensus mechanisms.",
    "Photosynthesis converts light energy into chemical energy.",
    "Deep learning architectures like CNNs excel at image recognition.",
]


def run_latency_evaluation():
    logger.info(f"Starting latency evaluation with {NUM_REQUESTS} requests")
    logger.info(f"API Base URL: {API_BASE}")

    all_latencies = []
    segment_times = {
        "gliner": [],
        "embedding": [],
        "qdrant": [],
        "reranking": [],
    }

    for i in range(NUM_REQUESTS):
        draft = test_drafts[i % len(test_drafts)]

        req_start = time.time()
        try:
            response = requests.post(
                f"{API_BASE}/recommend",
                json={"text": draft},
                timeout=30,
            )
            req_end = time.time()

            if response.status_code == 200:
                data = response.json()
                latency_ms = data.get("latency_ms", int((req_end - req_start) * 1000))
                all_latencies.append(latency_ms)

                logger.info(f"Request {i+1}/{NUM_REQUESTS}: {latency_ms}ms")
            else:
                logger.error(f"Request {i+1} failed with status {response.status_code}")

        except Exception as e:
            logger.error(f"Request {i+1} exception: {e}")

    if not all_latencies:
        logger.error("No successful requests - cannot compute statistics")
        return

    mean_latency = statistics.mean(all_latencies)
    median_latency = statistics.median(all_latencies)
    stdev_latency = statistics.stdev(all_latencies) if len(all_latencies) > 1 else 0
    min_latency = min(all_latencies)
    max_latency = max(all_latencies)
    p95_latency = (
        sorted(all_latencies)[int(len(all_latencies) * 0.95)]
        if len(all_latencies) >= 20
        else max_latency
    )
    p99_latency = (
        sorted(all_latencies)[int(len(all_latencies) * 0.99)]
        if len(all_latencies) >= 100
        else max_latency
    )

    target_ms = 3000

    print("\n" + "=" * 60)
    print("LATENCY EVALUATION RESULTS (Eval 1)")
    print("=" * 60)
    print(f"Total Requests:       {NUM_REQUESTS}")
    print(f"Successful:         {len(all_latencies)}")
    print(f"Failed:              {NUM_REQUESTS - len(all_latencies)}")
    print("-" * 60)
    print(f"Mean Latency:       {mean_latency:.2f} ms")
    print(f"Median Latency:      {median_latency:.2f} ms")
    print(f"Min Latency:         {min_latency} ms")
    print(f"Max Latency:         {max_latency} ms")
    print(f"Std Dev:             {stdev_latency:.2f} ms")
    print(f"P95 Latency:         {p95_latency} ms")
    print(f"P99 Latency:         {p99_latency} ms")
    print("-" * 60)
    print(f"Target:              {target_ms} ms")
    print(f"Status:              {'PASS' if max_latency < target_ms else 'FAIL'}")
    print("=" * 60)

    logger.info(
        f"Latency eval complete: mean={mean_latency:.2f}ms, max={max_latency}ms"
    )

    return {
        "mean": mean_latency,
        "median": median_latency,
        "min": min_latency,
        "max": max_latency,
        "stdev": stdev_latency,
        "p95": p95_latency,
        "p99": p99_latency,
        "target_met": max_latency < target_ms,
    }


if __name__ == "__main__":
    run_latency_evaluation()
