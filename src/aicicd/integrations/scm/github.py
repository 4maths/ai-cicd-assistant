import logging
import subprocess
import os
from typing import Dict, Any

logger = logging.getLogger(__name__)

MAX_DIFF_CHARS = 32000

def get_pr_diff(repo_name: str, pr_number: int, token: str = "") -> Dict[str, Any]:
    """Gets the unified diff using local git diff with robust fallback for CI."""
    try:
        base_ref = os.environ.get("GITHUB_BASE_REF", "main")
        head_ref = os.environ.get("GITHUB_HEAD_REF", "HEAD")
        
        logger.info(f"--- Git Diff Diagnostics ---")
        logger.info(f"GITHUB_BASE_REF: {base_ref}")
        logger.info(f"GITHUB_HEAD_REF: {head_ref}")
        
        # 1. Ensure base branch is fetched
        logger.info(f"Fetching origin/{base_ref}...")
        subprocess.run(["git", "fetch", "origin", base_ref], capture_output=True)
        
        # 2. Try various diff methods
        diff_cmds = [
            ["git", "diff", f"origin/{base_ref}...{head_ref}"],
            ["git", "diff", f"origin/{base_ref}...HEAD"],
            ["git", "diff", "HEAD^..HEAD"], # Last commit fallback
        ]
        
        full_diff = ""
        for cmd in diff_cmds:
            logger.info(f"Running: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
            if result.returncode == 0 and result.stdout.strip():
                full_diff = result.stdout
                logger.info(f"Success! Found diff using {' '.join(cmd)} ({len(full_diff)} chars)")
                break
        
        if not full_diff:
            logger.warning("All git diff attempts failed or returned empty. Is the repo fully fetched?")
            # Very aggressive fallback: show the last commit
            logger.info("Aggressive fallback: git show HEAD")
            result = subprocess.run(["git", "show", "HEAD"], capture_output=True, text=True, encoding="utf-8")
            full_diff = result.stdout if result.returncode == 0 else ""

        if len(full_diff) > MAX_DIFF_CHARS:
            logger.info(f"Diff too large, truncating to {MAX_DIFF_CHARS} chars.")
            full_diff = full_diff[:MAX_DIFF_CHARS]

        author = os.environ.get("GITHUB_ACTOR", "unknown")
        title = f"PR #{pr_number}" if pr_number else "Local Changes"

        return {
            "diff": full_diff,
            "metadata": {
                "author": author,
                "title": title
            }
        }

    except Exception as exc:
        logger.error(f"Error fetching diff: {exc}")
        return {"diff": "", "metadata": {}}
