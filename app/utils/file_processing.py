"""
Utility functions for processing different file types.
"""
import aiofiles
import io
from pathlib import Path
from typing import Optional


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
            return text
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

