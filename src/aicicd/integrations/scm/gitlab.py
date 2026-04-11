import logging
import gitlab
from gitlab.exceptions import GitlabError
from typing import Dict, Any

logger = logging.getLogger(__name__)

MAX_DIFF_CHARS = 10000

def get_mr_diff(repo_name: str, mr_number: int, token: str, url: str = "https://gitlab.com") -> Dict[str, Any]:
    """Gets the unified diff string and metadata for a Gitlab MR."""
    try:
        gl = gitlab.Gitlab(url, private_token=token)
        project = gl.projects.get(repo_name)
        mr = project.mergerequests.get(mr_number)
        changes = mr.changes()
        
        diff_parts = []
        for change in changes.get("changes", []):
            new_path = change.get('new_path', 'unknown')
            patch = change.get('diff', '')
            if patch:
                diff_parts.append(f"### {new_path}\n{patch}")

        full_diff = "\n\n".join(diff_parts)
        if len(full_diff) > MAX_DIFF_CHARS:
            logger.info(f"Diff too large, truncating to {MAX_DIFF_CHARS} chars.")
            full_diff = full_diff[:MAX_DIFF_CHARS]

        labels = mr.labels

        return {
            "diff": full_diff,
            "metadata": {
                "labels": labels,
                "author": mr.author.get('username') if getattr(mr, 'author', None) else "",
                "title": getattr(mr, 'title', "")
            }
        }

    except GitlabError as exc:
        logger.error(f"Error fetching MR diff from GitLab: {exc}")
        return {"diff": "", "metadata": {}}

