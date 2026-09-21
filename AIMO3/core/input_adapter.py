from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import csv

from .pdf_reader import AIMOReferencePDFReader, PDFProblemRecord


@dataclass
class InputProblem:
    problem_id: str
    problem_text: str
    semantic_text: str
    solver_text: str
    expected_answer: int | None = None
    metadata: dict | None = None


class AIMOInputAdapter:
    """
    Unified input layer.

    Priority for AIMO3:
      CSV -> preserves original LaTeX exactly.
      PDF -> reference/upload fallback via leakage-safe reader.
      TXT -> one problem.

    The Kaggle scoring input is CSV (`id`, `problem`), while the reference PDF is
    primarily a notebook/reference document. Therefore CSV should be preferred when
    both are available.
    """

    @staticmethod
    def from_csv(path: str | Path, benchmark_mode: bool = False) -> list[InputProblem]:
        path = Path(path)
        out = []
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            if "problem" not in (reader.fieldnames or []):
                raise ValueError("CSV must contain a `problem` column.")
            for i, row in enumerate(reader):
                pid = str(row.get("id") or f"csv_{i:04d}")
                problem = str(row["problem"])
                expected = None
                if benchmark_mode and row.get("answer") not in (None, ""):
                    expected = int(row["answer"])
                out.append(InputProblem(
                    problem_id=pid,
                    problem_text=problem,
                    semantic_text=problem,
                    solver_text=problem,
                    expected_answer=expected,
                    metadata={"source": str(path), "type": "csv", "solver_text_source": "csv_exact"},
                ))
        return out

    @staticmethod
    def from_pdf(path: str | Path, benchmark_mode: bool = False) -> list[InputProblem]:
        records = AIMOReferencePDFReader(
            path,
            benchmark_mode=benchmark_mode,
            prefer_layout=True,
        ).read()
        return [
            InputProblem(
                problem_id=r.problem_id,
                problem_text=r.problem_text,
                semantic_text=r.semantic_text,
                # v2.7: the math-aware semantic view is the solver source for PDFs.
                # It reconstructs superscripts/subscripts such as 2^{20}, 10^{5},
                # while the layout/plain view is retained only for display/audit.
                solver_text=(r.semantic_text or r.problem_text),
                expected_answer=r.expected_answer,
                metadata={**r.to_dict(), "solver_text_source": "semantic_math" if r.semantic_text else "layout_fallback"},
            )
            for r in records
        ]

    @staticmethod
    def from_text(path: str | Path) -> list[InputProblem]:
        path = Path(path)
        text = path.read_text(encoding="utf-8")
        return [InputProblem(
            problem_id=path.stem,
            problem_text=text.strip(),
            semantic_text=text.strip(),
            solver_text=text.strip(),
            metadata={"source": str(path), "type": "text", "solver_text_source": "text_exact"},
        )]

    @classmethod
    def load(cls, path: str | Path, benchmark_mode: bool = False) -> list[InputProblem]:
        path = Path(path)
        suffix = path.suffix.lower()
        if suffix == ".csv":
            return cls.from_csv(path, benchmark_mode=benchmark_mode)
        if suffix == ".pdf":
            return cls.from_pdf(path, benchmark_mode=benchmark_mode)
        if suffix in {".txt", ".md"}:
            return cls.from_text(path)
        raise ValueError(f"Unsupported input format: {suffix}")
