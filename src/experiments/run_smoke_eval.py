"""
src.experiments.run_smoke_eval

Day-2 runner:
- loads prompts from config dataset_path (JSONL)
- calls ModelRouter (mock or openai)
- evaluates enabled metrics (factuality, toxicity, latency)
- produces JSON report + threshold pass/fail
"""

from __future__ import annotations

import argparse
import json
import os
from typing import Any, Dict, List

from src.common.config import load_config
from src.common.logger import get_logger
from src.inference.model_router import ModelRouter
from src.evaluation.latency import measure_latency_ms
from src.evaluation.toxicity import evaluate_toxicity
from src.evaluation.factuality import evaluate_factuality

logger = get_logger(__name__)


def _read_jsonl(path: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def run_smoke(cfg: Dict[str, Any]) -> Dict[str, Any]:
    eval_cfg = cfg.get("evaluation", {}) or {}
    thresholds = cfg.get("thresholds", {}) or {}

    enabled = eval_cfg.get("enabled_metrics", []) or []
    dataset_path = str(eval_cfg.get("dataset_path", "data/golden/smoke.jsonl"))
    sample_size = int(eval_cfg.get("sample_size", 50))

    if not os.path.exists(dataset_path):
        raise FileNotFoundError(f"Dataset missing: {dataset_path}. Create it (data/golden/smoke.jsonl).")

    rows = _read_jsonl(dataset_path)
    if not rows:
        raise ValueError(f"Dataset empty: {dataset_path}")

    rows = rows[: min(sample_size, len(rows))]

    router = ModelRouter(cfg)

    per_item: List[Dict[str, Any]] = []
    latency_samples: List[float] = []
    toxicity_scores: List[float] = []
    factuality_scores: List[float] = []

    for item in rows:
        prompt = item.get("prompt", "")
        reference = item.get("reference")

        # Measure inference latency (single call)
        lat = measure_latency_ms(lambda: router.generate(prompt), repeats=1)
        lat_ms = float(lat["latencies_ms"][0])
        latency_samples.append(lat_ms)

        resp = router.generate(prompt)
        result: Dict[str, Any] = {
            "id": item.get("id"),
            "prompt": prompt,
            "model": resp.model_name,
            "provider": resp.provider,
            "response": resp.text,
            "latency_ms": lat_ms,
        }

        if "toxicity" in enabled:
            tox = evaluate_toxicity(resp.text)
            toxicity_scores.append(float(tox["score"]))
            result["toxicity"] = tox

        if "factuality" in enabled:
            fac = evaluate_factuality(resp.text, reference=reference)
            factuality_scores.append(float(fac["score"]))
            result["factuality"] = fac

        per_item.append(result)

    # Aggregate
    latency_samples_sorted = sorted(latency_samples)
    p95_idx = int(round(0.95 * (len(latency_samples_sorted) - 1)))
    p95_idx = max(0, min(p95_idx, len(latency_samples_sorted) - 1))
    latency_p95 = float(latency_samples_sorted[p95_idx])

    toxicity_mean = float(sum(toxicity_scores) / len(toxicity_scores)) if toxicity_scores else 0.0
    factuality_mean = float(sum(factuality_scores) / len(factuality_scores)) if factuality_scores else 0.0

    # Threshold checks
    tox_max = float(thresholds.get("toxicity_max", 1.0))
    lat_p95_max = float(thresholds.get("latency_p95_ms", 1e9))

    checks = {
        "toxicity_mean_ok": toxicity_mean <= tox_max,
        "latency_p95_ok": latency_p95 <= lat_p95_max,
    }
    checks["all_ok"] = all(checks.values())

    report = {
        "environment": cfg.get("environment"),
        "provider": cfg.get("inference", {}).get("provider"),
        "default_model": cfg.get("inference", {}).get("default_model"),
        "n_samples": len(rows),
        "metrics": {
            "latency_p95_ms": latency_p95,
            "toxicity_mean": toxicity_mean,
            "factuality_mean": factuality_mean,
        },
        "thresholds": {
            "toxicity_max": tox_max,
            "latency_p95_ms": lat_p95_max,
        },
        "checks": checks,
        "items": per_item,
    }
    return report


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True, help="Path to YAML config, e.g. configs/dev.yaml")
    args = ap.parse_args()

    cfg = load_config(args.config)
    report = run_smoke(cfg)

    os.makedirs("artifacts/reports", exist_ok=True)
    out_path = "artifacts/reports/smoke_report.json"
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2)

    logger.info("Wrote report: %s", out_path)
    logger.info("Checks: %s", report["checks"])


if __name__ == "__main__":
    main()
