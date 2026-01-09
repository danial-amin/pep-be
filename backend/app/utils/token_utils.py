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
    chunks = []
    
    # Estimate characters per token (conservative: 4 chars = 1 token)
    max_chars = max_tokens * 4
    overlap_chars = overlap_tokens * 4
    
    start = 0
    text_length = len(text)
    
    while start < text_length:
        # Calculate end position
        end = min(start + max_chars, text_length)
        
        # Try to break at sentence boundaries near the end
        chunk = text[start:end]
        
        # If not at the end of text, try to break at a sentence boundary
        if end < text_length:
            # Look for sentence endings in the last 20% of the chunk
            search_start = max(0, len(chunk) - (max_chars // 5))
            for i in range(len(chunk) - 1, search_start, -1):
                if chunk[i] in '.!?\n' and i > search_start:
                    chunk = chunk[:i+1]
                    end = start + i + 1
                    break
        
        chunks.append(chunk)
        
        # Move start position with overlap
        start = max(start + 1, end - overlap_chars)
        
        # Safety check to avoid infinite loop
        if start >= end:
            start = end
    
    return chunks

