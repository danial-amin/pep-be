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
    
    Currently supports:
    - .txt, .md: Direct text reading
    - .pdf: Requires pypdf (add to requirements if needed)
    - .docx: Requires python-docx (add to requirements if needed)
    """
    file_ext = file_extension.lower()
    
    if file_ext in ['.txt', '.md']:
        async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
            return await f.read()
    
    elif file_ext == '.pdf':
        # For PDF support, you would need: pip install pypdf
        try:
            import pypdf
            text = ""
            async with aiofiles.open(file_path, 'rb') as f:
                content = await f.read()
                pdf_reader = pypdf.PdfReader(io.BytesIO(content))
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
            return _clean_pdf_text(text)
        except ImportError:
            raise ValueError("PDF support requires 'pypdf' package. Install with: pip install pypdf")
    
    elif file_ext == '.docx':
        # For DOCX support, you would need: pip install python-docx
        try:
            from docx import Document
            doc = Document(file_path)
            text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
            return text
        except ImportError:
            raise ValueError("DOCX support requires 'python-docx' package. Install with: pip install python-docx")
    
    else:
        raise ValueError(f"Unsupported file type: {file_ext}")

