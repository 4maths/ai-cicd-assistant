import json
import re
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

def parse_json_safely(raw: str) -> Dict[str, Any]:
    """
    Robustly extracts and parses a JSON object from a potentially messy string.
    Handles Markdown code blocks and leading/trailing text.
    """
    if not raw:
        return {}
        
    raw = raw.strip()
    # 1. Try to find JSON block in markdown
    match = re.search(r"```json\s*(.*?)\s*```", raw, re.DOTALL)
    if match:
        raw = match.group(1)
    else:
        # 2. Try to find anything that looks like a JSON object { ... }
        match = re.search(r"({.*})", raw, re.DOTALL)
        if match:
            raw = match.group(1)

    try:
        return json.loads(raw.strip())
    except Exception as e:
        logger.error(f"Cannot parse JSON from LLM: {str(e)}\nRaw was: {raw}")
        return {}
