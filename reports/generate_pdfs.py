"""Convert NeuroSense markdown reports to PDF."""

from __future__ import annotations

import re
import sys
from pathlib import Path

from fpdf import FPDF


def _sanitize(text: str) -> str:
    text = text.replace("\u2014", "-").replace("\u2013", "-")
    text = text.replace("\u2192", "->").replace("\u2019", "'")
    text = text.replace("**", "").replace("*", "")
    return text.encode("latin-1", "replace").decode("latin-1")


def md_to_pdf(md_path: Path, pdf_path: Path, title: str) -> None:
    pdf = FPDF()
    pdf.set_margins(15, 15, 15)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    w = pdf.epw

    pdf.set_font("Helvetica", "B", 14)
    pdf.multi_cell(w, 8, _sanitize(title))
    pdf.ln(4)

    for raw in md_path.read_text(encoding="utf-8").splitlines():
        line = _sanitize(raw.rstrip())
        if not line:
            pdf.ln(3)
            continue
        if line.startswith("# "):
            pdf.set_font("Helvetica", "B", 12)
            pdf.multi_cell(w, 6, line[2:].strip())
            pdf.set_font("Helvetica", "", 9)
        elif line.startswith("## "):
            pdf.set_font("Helvetica", "B", 10)
            pdf.multi_cell(w, 5, line[3:].strip())
            pdf.set_font("Helvetica", "", 9)
        elif line.startswith("### "):
            pdf.set_font("Helvetica", "B", 9)
            pdf.multi_cell(w, 5, line[4:].strip())
            pdf.set_font("Helvetica", "", 9)
        elif line.strip().startswith("|") and "---" not in line:
            pdf.set_font("Helvetica", "", 8)
            pdf.multi_cell(w, 4, re.sub(r"\s*\|\s*", "  |  ", line.strip()))
            pdf.set_font("Helvetica", "", 9)
        elif line.strip() == "---":
            pdf.ln(2)
        else:
            pdf.set_font("Helvetica", "", 9)
            pdf.multi_cell(w, 4, line)

    pdf.output(str(pdf_path))
    print(f"Wrote {pdf_path}")


def main() -> None:
    reports = Path(__file__).resolve().parent
    pairs = [
        (
            reports / "NeuroSense_Batch_Summary_20260702.md",
            reports / "NeuroSense_Batch_Summary_20260702.pdf",
            "NeuroSense AI - Batch Summary",
        ),
        (
            reports / "DW_5-18-26_Claude_Narrative.md",
            reports / "DW_5-18-26_Claude_Narrative.pdf",
            "DW 5-18-26 - Claude Analysis",
        ),
    ]
    for md, pdf, title in pairs:
        if not md.is_file():
            print(f"Missing {md}", file=sys.stderr)
            sys.exit(1)
        md_to_pdf(md, pdf, title)


if __name__ == "__main__":
    main()
