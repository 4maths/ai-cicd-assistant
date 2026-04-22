import logging
import subprocess
import os
from typing import Dict, Any

logger = logging.getLogger(__name__)

MAX_DIFF_CHARS = 10000

def get_pr_diff(repo_name: str, pr_number: int, token: str = "") -> Dict[str, Any]:
    """Gets the unified diff using local git diff and metadata from environment."""
    try:
        # Determine base branch for diff
        base_ref = os.environ.get("GITHUB_BASE_REF", "main")
        head_ref = os.environ.get("GITHUB_HEAD_REF", "HEAD")
        
        logger.info(f"Fetching diff using git diff origin/{base_ref}...{head_ref}")
        
        # Try to get diff using git command
        cmd = ["git", "diff", f"origin/{base_ref}...{head_ref}"]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", check=True)
        full_diff = result.stdout
        
        if not full_diff:
            # Fallback for local testing if origin doesn't exist
            logger.info("Empty diff with origin, trying local branch diff")
            cmd = ["git", "diff", base_ref]
            result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", check=True)
            full_diff = result.stdout

        if len(full_diff) > MAX_DIFF_CHARS:
            logger.info(f"Diff too large, truncating to {MAX_DIFF_CHARS} chars.")
            full_diff = full_diff[:MAX_DIFF_CHARS]

        # Get metadata from environment variables (provided by GitHub Actions)
        author = os.environ.get("GITHUB_ACTOR", "unknown")
        # PR Title is not directly in env, but can be passed or left as generic if no API
        title = f"PR #{pr_number}" if pr_number else "Local Changes"

        return {
            "diff": full_diff,
            "metadata": {
                "author": author,
                "title": title
            }
        }

    except Exception as exc:
        logger.error(f"Error fetching diff using git: {exc}")
        return {"diff": "", "metadata": {}}


