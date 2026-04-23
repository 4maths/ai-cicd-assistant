import logging
import subprocess
import os
from typing import Dict, Any, Optional
from aicicd.integrations.base import SCMInterface
from aicicd.config.settings import settings

logger = logging.getLogger(__name__)

class GitLabSCM(SCMInterface):
    """GitLab implementation of SCMInterface using environment variables and git."""

    def __init__(self, token: Optional[str] = None):
        self.token = token or settings.GITLAB_TOKEN

    def get_pull_request_diff(self, repo: str, pr_id: int) -> Dict[str, Any]:
        full_diff = ""
        try:
            base_branch = os.environ.get("CI_MERGE_REQUEST_TARGET_BRANCH_NAME", "main")
            # Try git diff against origin
            res = subprocess.run(["git", "diff", f"origin/{base_branch}...HEAD"], capture_output=True, text=True)
            if res.returncode == 0:
                full_diff = res.stdout
            
            if not full_diff:
                res = subprocess.run(["git", "diff", base_branch], capture_output=True, text=True)
                full_diff = res.stdout

            author = os.environ.get("GITLAB_USER_LOGIN", "unknown")
            title = os.environ.get("CI_MERGE_REQUEST_TITLE", f"MR !{pr_id}" if pr_id else "Local Changes")

            return {
                "diff": full_diff[:settings.MAX_DIFF_CHARS] if full_diff else "",
                "metadata": {"author": author, "title": title, "source": "GitLab"}
            }
        except Exception as e:
            logger.error(f"GitLab diff error: {e}")
            return {"diff": "", "metadata": {}}
        
