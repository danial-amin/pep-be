"""
Utility functions for processing different file types.
"""
import aiofiles
import io
import re
import unicodedata
from pathlib import Path
from typing import Optional


def _clean_pdf_text(raw_text: str) -> str:
    """
    Normalize PDF-extracted text to remove common artifacts:
    - headers/footers, URLs, page counters
    - ligatures and odd unicode
    - excessive whitespace and duplicated lines
    """
    if not raw_text:
        return raw_text

    # Normalize unicode (fix ligatures like ﬁ/ﬀ and odd spacing)
    text = unicodedata.normalize("NFKC", raw_text)

    # Fix common ligatures explicitly (NFKC won't catch all)
    ligatures = {
        "ﬁ": "fi",
        "ﬂ": "fl",
        "ﬀ": "ff",
        "ﬃ": "ffi",
        "ﬄ": "ffl",
        "ﬅ": "ft",
        "ﬆ": "st",
    }
    for bad, good in ligatures.items():
        text = text.replace(bad, good)

    lines = [ln.strip() for ln in text.splitlines()]
    cleaned_lines = []
    url_re = re.compile(r"https?://\S+")
    page_re = re.compile(r"^\d+\s*/\s*\d+$")
    timestamp_re = re.compile(r"^\d{1,2}/\d{1,2}/\d{2,4},")
    for ln in lines:
        if not ln:
            continue
        # Drop obvious header/footer noise
        if url_re.search(ln):
            continue
        if page_re.match(ln):
            continue
        if timestamp_re.match(ln):
            continue
        cleaned_lines.append(ln)

    # Remove consecutive duplicate lines (common in PDF extraction)
    deduped_lines = []
    prev = None
    for ln in cleaned_lines:
        if ln == prev:
            continue
        deduped_lines.append(ln)
        prev = ln

    # Re-join and de-hyphenate line breaks
    text = "\n".join(deduped_lines)
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
    # Collapse extra whitespace
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


async def extract_text_from_file(file_path: str, file_extension: str) -> str:
    """
    Extract text content from various file types.

    - .txt, .md: Direct text reading (utf-8)
    - .pdf: pdfplumber (primary; better layout/tables), pypdf (fallback)
    - .docx: python-docx
    """
    file_ext = file_extension.lower()

    if file_ext in [".txt", ".md"]:
        async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
            return await f.read()

    elif file_ext == ".pdf":
        return await _extract_pdf(file_path)

    elif file_ext == ".docx":
        try:
            from docx import Document as DocxDocument
            doc = DocxDocument(file_path)
            text = "\n".join(p.text for p in doc.paragraphs if p.text)
            return text.strip()
        except ImportError:
            raise ValueError(
                "DOCX support requires 'python-docx'. Install with: pip install python-docx"
            )

    else:
        raise ValueError(f"Unsupported file type: {file_ext}")


def _table_to_text(table: list) -> str:
    """Turn a pdfplumber table (list of lists) into readable text lines."""
    if not table:
        return ""
    lines = []
    for row in table:
        line = " | ".join(str(cell) if cell is not None else "" for cell in row)
        if line.strip():
            lines.append(line)
    return "\n".join(lines) if lines else ""


async def _extract_pdf(file_path: str) -> str:
    """
    Extract text from PDF using pdfplumber (primary) with pypdf fallback.
    pdfplumber gives better layout and table handling; pypdf is used if pdfplumber fails.
    Includes table extraction so tables appear in the document content.
    """
    # Prefer pdfplumber (better for tables and layout)
    try:
        import pdfplumber
        text_parts = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text_parts.append(t)
                # Include tables as text (pdfplumber strength)
                tables = page.extract_tables()
                for table in tables:
                    table_text = _table_to_text(table)
                    if table_text:
                        text_parts.append(table_text)
        text = "\n\n".join(text_parts)
        if text.strip():
            return _clean_pdf_text(text)
    except ImportError:
        pass
    except Exception:
        # Fall through to pypdf on any pdfplumber error
        pass

    # Fallback: pypdf
    try:
        import pypdf
        text = ""
        async with aiofiles.open(file_path, "rb") as f:
            content = await f.read()
            pdf_reader = pypdf.PdfReader(io.BytesIO(content))
            for page in pdf_reader.pages:
                t = page.extract_text()
                if t:
                    text += t + "\n"
        return _clean_pdf_text(text)
    except ImportError:
        raise ValueError(
            "PDF support requires 'pdfplumber' or 'pypdf'. Install with: pip install pdfplumber pypdf"
        )

