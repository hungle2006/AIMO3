from __future__ import annotations

from pathlib import Path
import argparse
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from core.config import load_config, prepare_environment
from core.model_manager import ModelManager
from core.pipeline import FullOlympiadPipeline
from core.reporting import save_result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--problem", required=True)
    ap.add_argument("--id", default="problem_001")
    ap.add_argument("--config", default=str(ROOT / "config_v2_11_0.yaml"))
    ap.add_argument("--preload", action="store_true")
    args = ap.parse_args()

    cfg = load_config(args.config)
    prepare_environment(cfg)
    manager = ModelManager(cfg)
    if args.preload:
        manager.preload()

    pipe = FullOlympiadPipeline(cfg, manager)
    result = pipe.run(args.problem, problem_id=args.id)
    jp, mp = save_result(result, cfg["project"]["output_dir"])

    print("\n" + "=" * 80)
    print("STATUS:", result["status"])
    print("CANDIDATE ANSWER:", result.get("candidate_answer"))
    print("VERIFIED ANSWER:", result.get("verified_answer"))
    print("VERIFICATION:", result.get("verification", {}).get("level"), result.get("verification", {}).get("reason"))
    print("MODEL CALLS:", result["metrics"]["model_calls"])
    print("TOKENS:", result["metrics"]["total_tokens"])
    print("LATENCY:", round(result["metrics"]["latency_sec"], 2), "sec")
    print("Saved:", jp)
    print("Saved:", mp)


if __name__ == "__main__":
    main()
