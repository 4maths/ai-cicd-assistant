import logging
import subprocess
import os
from typing import Dict, Any

logger = logging.getLogger(__name__)

MAX_DIFF_CHARS = 32000

import requests

MAX_DIFF_CHARS = 32000

def get_pr_diff(repo_name: str, pr_number: int, token: str = "") -> Dict[str, Any]:
    """Gets the unified diff using GitHub API (primary) or local git (fallback)."""
    full_diff = ""
    author = os.environ.get("GITHUB_ACTOR", "unknown")
    title = f"PR #{pr_number}" if pr_number else "Local Changes"

    # 1. Try GitHub API (Reliable in CI)
    if token and pr_number and repo_name:
        try:
            logger.info(f"Attempting to fetch diff via GitHub API for {repo_name} PR #{pr_number}")
            url = f"https://api.github.com/repos/{repo_name}/pulls/{pr_number}"
            # Standard GitHub Diff header
            headers = {
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.diff"
            }
            response = requests.get(url, headers=headers, timeout=20)
            logger.info(f"GitHub API Response Status: {response.status_code}")
            
            if response.status_code == 200:
                full_diff = response.text
                if full_diff.strip():
                    logger.info(f"Successfully fetched diff via API ({len(full_diff)} chars)")
                    logger.info(f"Diff preview: {full_diff[:100]}...")
                else:
                    logger.warning("API returned 200 OK but the diff content is empty!")
            else:
                logger.warning(f"API Diff failed: {response.status_code} - {response.text[:200]}")

        except Exception as e:
            logger.warning(f"Error calling GitHub API: {e}")

    # 2. Fallback to Local Git if API failed or not applicable
    if not full_diff:
        try:
            base_ref = os.environ.get("GITHUB_BASE_REF", "main")
            head_ref = os.environ.get("GITHUB_HEAD_REF", "HEAD")
            
            logger.info(f"--- Git Diff Fallback Diagnostics ---")
            # Ensure base branch is fetched
            subprocess.run(["git", "fetch", "origin", base_ref], capture_output=True)
            
            diff_cmds = [
                ["git", "diff", f"origin/{base_ref}...{head_ref}"],
                ["git", "diff", f"origin/{base_ref}...HEAD"],
                ["git", "diff", "HEAD^..HEAD"],
            ]
            
            for cmd in diff_cmds:
                result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
                if result.returncode == 0 and result.stdout.strip():
                    full_diff = result.stdout
                    logger.info(f"Success! Found diff using {' '.join(cmd)}")
                    break
        except Exception as exc:
            logger.error(f"Git fallback failed: {exc}")

    if not full_diff:
        logger.error("Failed to acquire diff through all methods.")
        return {"diff": "", "metadata": {}}

    if len(full_diff) > MAX_DIFF_CHARS:
        full_diff = full_diff[:MAX_DIFF_CHARS]

    return {
        "diff": full_diff,
        "metadata": {
            "author": author,
            "title": title
        }
    }

