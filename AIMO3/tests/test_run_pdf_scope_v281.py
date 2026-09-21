from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "run_pdf_pipeline.py"

tree = ast.parse(SRC.read_text(encoding="utf-8"))
main_fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")

# Regression for Kaggle crash:
# An import like `from core.pipeline import FullOlympiadPipeline` inside main()
# makes the name local to the entire function and causes UnboundLocalError on
# the normal (non --engine-only) path before that branch executes.
for node in ast.walk(main_fn):
    if isinstance(node, ast.ImportFrom):
        for alias in node.names:
            assert alias.asname != "FullOlympiadPipeline"
            assert alias.name != "FullOlympiadPipeline", (
                "FullOlympiadPipeline must not be imported inside main(); "
                "it shadows the module-level binding and crashes normal runs."
            )

code = compile(SRC.read_text(encoding="utf-8"), str(SRC), "exec")
ns = {"__name__": "run_pdf_pipeline_scope_test", "__file__": str(SRC)}
exec(code, ns)
assert "FullOlympiadPipeline" not in ns["main"].__code__.co_varnames

print("test_run_pdf_scope_v281: PASS")
