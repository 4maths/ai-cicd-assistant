import logging
import subprocess
from typing import Dict, Any

logger = logging.getLogger(__name__)

def get_local_diff(base_branch: str = "main") -> Dict[str, Any]:
    """Gets the unified diff using a local git subprocess and empty metadata."""
    try:
        result = subprocess.run(
            ["git", "diff", base_branch],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True
        )
        return {
            "diff": result.stdout or "",
            "metadata": {
                "author": "local",
                "title": "Local Changes"
            }
        }

    except subprocess.CalledProcessError as exc:
        logger.error(f"Error executing git diff: {exc}")
        return {"diff": "", "metadata": {}}
    except FileNotFoundError:
        logger.error("Git executable not found.")
        return {"diff": "", "metadata": {}}

