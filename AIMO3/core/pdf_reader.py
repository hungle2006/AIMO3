from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import math
import re
import shutil
import statistics
import subprocess
import unicodedata
from typing import Optional

from .pdf_math_recovery import recover_statement_math


@dataclass
class PDFProblemRecord:
    problem_id: str
    problem_number: int | None
    problem_text: str
    semantic_text: str
    page_start: int | None
    page_end: int | None
    expected_answer: int | None = None
    source_pdf: str | None = None
    extraction_engine: str = "unknown"
    has_statement_images: bool = False
    warnings: list[str] | None = None
    raw_semantic_text: str | None = None
    math_recovery: dict | None = None

    def to_dict(self):
        d = asdict(self)
        d["warnings"] = d.get("warnings") or []
        return d


def _normalize_unicode(s: str) -> str:
    replacements = {
        "\u00ad": "",        # soft hyphen
        "\u200b": "",        # zero width space
        "\ufeff": "",
        "￾": "",
    }
    for a, b in replacements.items():
        s = s.replace(a, b)
    return unicodedata.normalize("NFKC", s)


def _remove_page_number_lines(text: str) -> str:
    lines = text.splitlines()
    out = []
    for line in lines:
        stripped = line.strip()
        # Standalone page number / LaTeX footer.
        if re.fullmatch(r"\d{1,3}", stripped):
            continue
        out.append(line.rstrip())
    return "\n".join(out)


def _trim_outer_blank_lines(text: str) -> str:
    lines = text.splitlines()
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines)


def _compact_for_retrieval(text: str) -> str:
    """
    Math-aware compact view. Keeps mathematical symbols while removing layout padding.
    For PDF inputs, v2.7 prefers this view for both solver and retrieval because it
    preserves reconstructed superscripts/subscripts that plain layout text can lose.
    """
    text = _normalize_unicode(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Join ordinary paragraph wraps, but leave display-style short lines alone.
    lines = [x.strip() for x in text.splitlines()]
    out = []
    buf = []
    for line in lines:
        if not line:
            if buf:
                out.append(" ".join(buf))
                buf = []
            out.append("")
            continue
        mathish = (
            len(line) < 70
            and bool(re.search(r"[=≤≥∑∏√⌊⌋∈∣|^_]", line))
        )
        if mathish:
            if buf:
                out.append(" ".join(buf))
                buf = []
            out.append(line)
        else:
            buf.append(line)
    if buf:
        out.append(" ".join(buf))
    return "\n".join(out).strip()


class MathAwarePyMuPDF:
    """
    Secondary text view using span font size and vertical position to reconstruct
    superscripts/subscripts. This is especially useful for inline expressions:
        z2 -> z^{2}
        xA -> x_{A}
        10105 -> 10^{10^{5}}
    It is not intended to replace layout-preserved extraction for stacked fractions.
    """

    def __init__(self, pdf_path: str | Path):
        try:
            import pymupdf as fitz  # PyMuPDF
        except Exception as e:
            raise RuntimeError(
                "PyMuPDF is not installed. Install package `PyMuPDF` or use "
                "the Poppler `pdftotext` fallback."
            ) from e
        self.fitz = fitz
        self.path = str(pdf_path)
        self.doc = fitz.open(self.path)

    @staticmethod
    def _script_depth(base_size: float, size: float) -> int:
        if size <= 0 or base_size <= 0:
            return 1
        ratio = max(base_size / size, 1.0)
        # TeX commonly scales scripts by ~0.7 each level.
        try:
            d = int(round(math.log(ratio, 1 / 0.7)))
        except Exception:
            d = 1
        return max(1, min(3, d))

    def reconstruct_line(self, line: dict) -> str:
        spans = [s for s in line.get("spans", []) if s.get("text")]
        if not spans:
            return ""

        visible = [s for s in spans if s["text"].strip()]
        if not visible:
            return " "

        max_size = max(s.get("size", 10.0) for s in visible)
        base_candidates = [
            s for s in visible
            if s.get("size", 0) >= 0.85 * max_size
            and not (int(s.get("flags", 0)) & 1)
        ]
        if not base_candidates:
            base_candidates = visible

        base_size = statistics.median(s.get("size", max_size) for s in base_candidates)
        base_y0 = statistics.median(s.get("bbox", (0, 0, 0, 0))[1] for s in base_candidates)

        classified = []
        for s in spans:
            text = s["text"]
            size = float(s.get("size", base_size))
            y0 = float(s.get("bbox", (0, base_y0, 0, 0))[1])
            flags = int(s.get("flags", 0))

            if flags & 1:  # PyMuPDF TEXT_FONT_SUPERSCRIPT
                kind = "sup"
                depth = self._script_depth(base_size, size)
            elif size < 0.82 * base_size and y0 > base_y0 + 0.15 * base_size:
                kind = "sub"
                depth = self._script_depth(base_size, size)
            else:
                kind = "normal"
                depth = 0
            classified.append((text, kind, depth))

        out = []
        current_kind = "normal"
        current_depth = 0

        def close(n: int):
            out.extend(["}"] * n)

        for text, kind, depth in classified:
            if text.isspace():
                if current_depth == 0:
                    out.append(text)
                continue

            if kind == "normal":
                if current_depth:
                    close(current_depth)
                current_kind, current_depth = "normal", 0
                out.append(text)
                continue

            if current_depth and kind != current_kind:
                close(current_depth)
                current_depth = 0

            if depth > current_depth:
                for _ in range(depth - current_depth):
                    out.append("^{" if kind == "sup" else "_{")
            elif depth < current_depth:
                close(current_depth - depth)

            current_kind, current_depth = kind, depth
            out.append(text.strip())

        if current_depth:
            close(current_depth)

        return "".join(out)

    def page_text(self, page_index: int) -> str:
        page = self.doc[page_index]
        data = page.get_text("dict", sort=True)
        lines = []
        for block in data.get("blocks", []):
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                t = self.reconstruct_line(line).rstrip()
                if t:
                    lines.append(t)
        return "\n".join(lines)

    def document_text(self) -> str:
        pages = []
        for i in range(len(self.doc)):
            pages.append(self.page_text(i))
        return "\n\f\n".join(pages)

    def page_has_image_between(
        self,
        page_index: int,
        y_min: float,
        y_max: float
    ) -> bool:
        page = self.doc[page_index]
        data = page.get_text("dict", sort=True)
        for block in data.get("blocks", []):
            if block.get("type") == 1:
                bbox = block.get("bbox", (0, 0, 0, 0))
                cy = (bbox[1] + bbox[3]) / 2
                if y_min <= cy <= y_max:
                    return True
        return False

    def statement_image_flag(self, problem_number: int) -> bool:
        """
        Conservative detector for an image/figure occurring between the `Problem:`
        and `Answer:` markers on the page containing `Problem N`.
        """
        heading = f"Problem {problem_number}"
        for i in range(len(self.doc)):
            page = self.doc[i]
            heading_rects = page.search_for(heading)
            if not heading_rects:
                continue
            problem_rects = page.search_for("Problem:")
            answer_rects = page.search_for("Answer:")
            if not problem_rects:
                continue
            y_min = min(r.y0 for r in problem_rects)
            y_max = min((r.y0 for r in answer_rects), default=page.rect.height)
            return self.page_has_image_between(i, y_min, y_max)
        return False


class AIMOReferencePDFReader:
    """
    Leakage-safe reader for AIMO-style reference PDFs.

    Default behavior:
      - extracts only `Problem:` text
      - removes `Answer:` and `Solution:` from model input
      - expected answer is only retained when benchmark_mode=True
      - solutions are NEVER returned as problem context

    Extraction engines:
      1) Poppler `pdftotext -layout` when available. This best preserves stacked
         fractions/sums in text-native LaTeX PDFs.
      2) PyMuPDF text fallback.
      3) PyMuPDF math-aware span view is additionally used for semantic_text.
    """

    HEADING_RE = re.compile(r"(?m)^[ \t\f]*Problem\s+(\d+)\s*$")
    PROBLEM_RE = re.compile(r"(?m)^[ \t]*Problem:\s*")
    ANSWER_RE = re.compile(r"(?m)^[ \t]*Answer:\s*([0-9]+)")
    SOLUTION_RE = re.compile(r"(?m)^[ \t]*Solution:\s*")

    def __init__(
        self,
        pdf_path: str | Path,
        benchmark_mode: bool = False,
        prefer_layout: bool = True,
    ):
        self.path = Path(pdf_path)
        if not self.path.exists():
            raise FileNotFoundError(self.path)
        self.benchmark_mode = benchmark_mode
        self.prefer_layout = prefer_layout

    def _poppler_layout_text(self) -> Optional[str]:
        exe = shutil.which("pdftotext")
        if not exe:
            return None
        try:
            p = subprocess.run(
                [exe, "-layout", str(self.path), "-"],
                text=True,
                capture_output=True,
                check=True,
            )
            return p.stdout
        except Exception:
            return None

    def _pymupdf_plain_text(self) -> str:
        try:
            import pymupdf as fitz
        except Exception as e:
            raise RuntimeError(
                "PDF reader needs either system `pdftotext` or PyMuPDF."
            ) from e
        doc = fitz.open(str(self.path))
        return "\n\f\n".join(page.get_text("text", sort=True) for page in doc)

    @staticmethod
    def _heading_page_map(pdf_path: Path) -> dict[int, int]:
        result = {}
        try:
            import pymupdf as fitz
            doc = fitz.open(str(pdf_path))
            for pi, page in enumerate(doc):
                txt = page.get_text("text", sort=True)
                for m in re.finditer(r"(?m)^Problem\s+(\d+)\s*$", txt):
                    result[int(m.group(1))] = pi + 1
        except Exception:
            pass
        return result

    def _semantic_sections(self) -> dict[int, str]:
        try:
            math_view = MathAwarePyMuPDF(self.path).document_text()
        except Exception:
            return {}
        heads = list(self.HEADING_RE.finditer(math_view))
        out = {}
        for i, m in enumerate(heads):
            num = int(m.group(1))
            end = heads[i + 1].start() if i + 1 < len(heads) else len(math_view)
            out[num] = math_view[m.end():end]
        return out

    def read(self) -> list[PDFProblemRecord]:
        raw = self._poppler_layout_text() if self.prefer_layout else None
        engine = "poppler_layout" if raw is not None else "pymupdf_text"
        if raw is None:
            raw = self._pymupdf_plain_text()

        raw = _normalize_unicode(raw)
        heads = list(self.HEADING_RE.finditer(raw))
        if not heads:
            # Generic single-problem PDF: do not attempt answer/solution exposure.
            cleaned = _trim_outer_blank_lines(_remove_page_number_lines(raw))
            return [
                PDFProblemRecord(
                    problem_id=self.path.stem,
                    problem_number=None,
                    problem_text=cleaned,
                    semantic_text=_compact_for_retrieval(cleaned),
                    page_start=1,
                    page_end=None,
                    expected_answer=None,
                    source_pdf=str(self.path),
                    extraction_engine=engine,
                    warnings=[
                        "No numbered `Problem N` headings detected; treated the PDF as one problem."
                    ],
                )
            ]

        page_map = self._heading_page_map(self.path)
        semantic_sections = self._semantic_sections()
        image_reader = None
        try:
            image_reader = MathAwarePyMuPDF(self.path)
        except Exception:
            pass

        records = []
        for i, m in enumerate(heads):
            number = int(m.group(1))
            section_end = heads[i + 1].start() if i + 1 < len(heads) else len(raw)
            section = raw[m.end():section_end]

            pm = self.PROBLEM_RE.search(section)
            am = self.ANSWER_RE.search(section)
            sm = self.SOLUTION_RE.search(section)

            if not pm:
                continue

            stop_candidates = [x.start() for x in (am, sm) if x is not None]
            stop = min(stop_candidates) if stop_candidates else len(section)
            problem_layout = section[pm.end():stop]
            problem_layout = _trim_outer_blank_lines(
                _remove_page_number_lines(problem_layout)
            )

            # Secondary semantic text from font-aware PyMuPDF reconstruction.
            sem_section = semantic_sections.get(number, "")
            sem_pm = self.PROBLEM_RE.search(sem_section)
            sem_am = self.ANSWER_RE.search(sem_section)
            sem_sm = self.SOLUTION_RE.search(sem_section)
            if sem_pm:
                sem_stop_candidates = [x.start() for x in (sem_am, sem_sm) if x]
                sem_stop = min(sem_stop_candidates) if sem_stop_candidates else len(sem_section)
                semantic = sem_section[sem_pm.end():sem_stop]
                semantic = _compact_for_retrieval(semantic)
            else:
                semantic = _compact_for_retrieval(problem_layout)

            raw_semantic = semantic
            recovered = recover_statement_math(number, semantic, problem_layout)
            semantic = recovered.text

            expected = int(am.group(1)) if (self.benchmark_mode and am) else None

            page_start = page_map.get(number)
            next_nums = [n for n in page_map if n > number]
            page_end = (
                page_map[min(next_nums)] - 1
                if next_nums and page_start is not None
                else page_start
            )

            warnings = []
            has_images = False
            if image_reader is not None:
                try:
                    has_images = image_reader.statement_image_flag(number)
                    if has_images:
                        warnings.append(
                            "A figure/image appears inside the problem-statement region. "
                            "The current reasoning models are text-only; visual information may be lost."
                        )
                except Exception:
                    pass

            records.append(
                PDFProblemRecord(
                    problem_id=f"pdf_problem_{number:02d}",
                    problem_number=number,
                    problem_text=problem_layout,
                    semantic_text=semantic,
                    page_start=page_start,
                    page_end=page_end,
                    expected_answer=expected,
                    source_pdf=str(self.path),
                    extraction_engine=engine,
                    has_statement_images=has_images,
                    warnings=warnings + ([
                        "Math recovery left warnings: " + ", ".join(recovered.warnings)
                    ] if recovered.warnings else []),
                    raw_semantic_text=raw_semantic,
                    math_recovery=recovered.to_dict(),
                )
            )

        return records
