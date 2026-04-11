import logging
from github import Github, GithubException
from typing import Dict, Any

logger = logging.getLogger(__name__)

MAX_DIFF_CHARS = 10000

def get_pr_diff(repo_name: str, pr_number: int, token: str) -> Dict[str, Any]:
    """Gets the unified diff string and metadata for a Github PR."""
    try:
        gh = Github(token)
        repo = gh.get_repo(repo_name)
        pr = repo.get_pull(pr_number)

        diff_parts = []
        for changed_file in pr.get_files():
            if changed_file.patch:
                diff_parts.append(f"### {changed_file.filename}\n{changed_file.patch}")

        full_diff = "\n\n".join(diff_parts)
        if len(full_diff) > MAX_DIFF_CHARS:
            logger.info(f"Diff too large, truncating to {MAX_DIFF_CHARS} chars.")
            full_diff = full_diff[:MAX_DIFF_CHARS]

        labels = [label.name for label in pr.get_labels()]

        return {
            "diff": full_diff,
            "metadata": {
                "labels": labels,
                "author": pr.user.login,
                "title": pr.title
            }
        }

    except GithubException as exc:
        logger.error(f"Error fetching PR diff from GitHub: {exc}")
        return {"diff": "", "metadata": {}}

