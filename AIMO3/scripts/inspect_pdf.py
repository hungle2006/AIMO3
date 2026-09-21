from pathlib import Path
import argparse
import sys
import json

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.input_adapter import AIMOInputAdapter

ap = argparse.ArgumentParser()
ap.add_argument("input")
ap.add_argument("--benchmark-reference", action="store_true")
ap.add_argument("--show", type=int, default=None)
args = ap.parse_args()

items = AIMOInputAdapter.load(args.input, benchmark_mode=args.benchmark_reference)
print("Problems:", len(items))

for x in items:
    m = x.metadata or {}
    print({
        "id": x.problem_id,
        "number": m.get("problem_number"),
        "pages": [m.get("page_start"), m.get("page_end")],
        "engine": m.get("extraction_engine"),
        "has_statement_images": m.get("has_statement_images"),
        "expected_answer": x.expected_answer if args.benchmark_reference else None,
        "chars": len(x.problem_text),
    })

if args.show is not None:
    for x in items:
        if (x.metadata or {}).get("problem_number") == args.show:
            print("\n--- LAYOUT-SAFE PROBLEM TEXT ---\n")
            print(x.problem_text)
            print("\n--- MATH-AWARE SEMANTIC TEXT ---\n")
            print(x.semantic_text)
