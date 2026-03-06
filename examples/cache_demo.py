"""
Lightweight demo: run pipeline twice on same input and report cache hit and timing.
Usage: python examples/cache_demo.py [artifact_file]
If no file given, uses a small in-memory blob. Output is deterministic.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

# Add src so hashen is importable
EXAMPLES = Path(__file__).resolve().parent
SRC = EXAMPLES.parent / "src"
sys.path.insert(0, str(SRC))

from hashen.orchestrator import run_pipeline


def main() -> int:
    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
        if not path.exists():
            print(f"File not found: {path}", file=sys.stderr)
            return 1
        artifact_bytes = path.read_bytes()
    else:
        artifact_bytes = b"cache_demo_same_input_" * 20

    config = {
        "h2_min": 0.0,
        "h2_max": 4.0,
        "h2_bins": 16,
        "h1_subset_size": 32,
    }
    run_id = "cache_demo"

    # First run: cold
    t0 = time.perf_counter()
    r1 = run_pipeline(artifact_bytes, run_id, config, target_id="demo")
    t1 = time.perf_counter()
    first_ms = (t1 - t0) * 1000

    # Second run: should hit cache (same artifact, same config)
    t2 = time.perf_counter()
    r2 = run_pipeline(artifact_bytes, run_id + "_2", config, target_id="demo")
    t3 = time.perf_counter()
    second_ms = (t3 - t2) * 1000

    print("Run 1 (cold):", f"{first_ms:.2f} ms", "cache_hit =", r1.get("cache_hit"))
    print("Run 2 (warm):", f"{second_ms:.2f} ms", "cache_hit =", r2.get("cache_hit"))
    if r2.get("cache_outcome"):
        co = r2["cache_outcome"]
        print("  cache_reason:", co.get("cache_reason"))
        print("  validation_subset_size:", co.get("validation_subset_size"))
        print("  mean_abs_diff:", co.get("mean_abs_diff"))
    if r1.get("cache_hit") is False and r2.get("cache_hit") is True:
        print("Cache hit on second run as expected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
