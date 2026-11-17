"""
Utility functions for token estimation and text chunking.
"""
from typing import List


def estimate_tokens(text: str) -> int:
    """
    Estimate token count for text.
    Rough estimation: ~4 characters per token for English text.
    This is a conservative estimate.
    """
    return len(text) // 4


def chunk_text_by_tokens(
    text: str,
    max_tokens: int = 20000,
    overlap_tokens: int = 500
) -> List[str]:
    """
    Split text into chunks based on token limits.
    
    Args:
        text: Text to chunk
        max_tokens: Maximum tokens per chunk (default 20k, leaving room for prompt)
        overlap_tokens: Number of tokens to overlap between chunks
    
    Returns:
        List of text chunks
    """
    if not text:
        return []

    # Estimate characters per token (conservative: 4 chars = 1 token)
    max_chars = max(1, max_tokens * 4)
    overlap_chars = max(0, overlap_tokens * 4)
    # Never allow overlap to be >= max chunk size (would cause no progress)
    if overlap_chars >= max_chars:
        overlap_chars = max(0, max_chars // 4)

    chunks: List[str] = []
    text_length = len(text)
    start = 0

    while start < text_length:
        end = min(start + max_chars, text_length)
        chunk = text[start:end]

        # If not at the end of text, try to break at a boundary near the end
        if end < text_length and chunk:
            # Search last 20% of the chunk for a reasonable break point.
            search_floor = max(0, len(chunk) - (len(chunk) // 5))
            for i in range(len(chunk) - 1, search_floor, -1):
                if chunk[i] in ".!?\n":
                    chunk = chunk[: i + 1]
                    end = start + i + 1
                    break

        if chunk:
            chunks.append(chunk)

        # Advance start; guarantee forward progress even in pathological inputs
        next_start = end - overlap_chars
        if next_start <= start:
            next_start = end
        start = next_start

    return chunks

