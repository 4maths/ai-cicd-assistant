from __future__ import annotations

import logging
from typing import List

logger = logging.getLogger(__name__)

def chunk_diff(diff_text: str, chunk_size: int = 1500) -> List[str]:
    """
    Splits diff text into chunks of approximately chunk_size.
    Tries to split at file boundaries if possible, but falls back to char-based splitting.
    """
    if not diff_text:
        return []

    if len(diff_text) <= chunk_size:
        return [diff_text]

    chunks = []
    current_chunk = []
    current_length = 0

    # Try to split by lines first to keep patches intact if possible
    lines = diff_text.splitlines()
    
    for line in lines:
        line_len = len(line) + 1 # +1 for newline
        
        if current_length + line_len > chunk_size and current_chunk:
            chunks.append("\n".join(current_chunk))
            current_chunk = []
            current_length = 0
            
        current_chunk.append(line)
        current_length += line_len
        
        # If a single line is larger than chunk_size, we have to hard split it
        if line_len > chunk_size:
            massive_line = current_chunk.pop()
            # Flush current chunk
            if current_chunk:
                chunks.append("\n".join(current_chunk))
                current_chunk = []
                current_length = 0
            
            # Split massive line
            for i in range(0, len(massive_line), chunk_size):
                chunks.append(massive_line[i:i+chunk_size])

    if current_chunk:
        chunks.append("\n".join(current_chunk))

    logger.info(f"Split diff into {len(chunks)} chunks.")
    return chunks
