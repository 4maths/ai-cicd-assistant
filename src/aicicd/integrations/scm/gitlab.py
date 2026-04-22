import logging
import subprocess
import os
from typing import Dict, Any

logger = logging.getLogger(__name__)

MAX_DIFF_CHARS = 10000

def get_mr_diff(repo_name: str, mr_number: int, token: str = "", url: str = "https://gitlab.com") -> Dict[str, Any]:
    """Gets the unified diff using local git diff and metadata from GitLab environment."""
    try:
        # Determine base and head for GitLab MR
        # Default to main if not in a MR context
        base_branch = os.environ.get("CI_MERGE_REQUEST_TARGET_BRANCH_NAME", "main")
        
        logger.info(f"Fetching MR diff using git diff origin/{base_branch}...HEAD")
        
        # Try git diff
        cmd = ["git", "diff", f"origin/{base_branch}...HEAD"]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", check=True)
        full_diff = result.stdout

        if not full_diff:
            logger.info("Empty diff with origin, trying local branch diff")
            cmd = ["git", "diff", base_branch]
            result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", check=True)
            full_diff = result.stdout

        if len(full_diff) > MAX_DIFF_CHARS:
            logger.info(f"Diff too large, truncating to {MAX_DIFF_CHARS} chars.")
            full_diff = full_diff[:MAX_DIFF_CHARS]

        # Get metadata from GitLab CI variables
        author = os.environ.get("GITLAB_USER_LOGIN", "unknown")
        title = os.environ.get("CI_MERGE_REQUEST_TITLE", f"MR !{mr_number}" if mr_number else "Local Changes")

        return {
            "diff": full_diff,
            "metadata": {
                "author": author,
                "title": title
            }
        }

    except Exception as exc:
        logger.error(f"Error fetching MR diff using git: {exc}")
        return {"diff": "", "metadata": {}}


