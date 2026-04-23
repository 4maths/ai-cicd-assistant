import logging
import requests
import os
import subprocess
from typing import Dict, Any, Optional
from aicicd.integrations.base import SCMInterface
from aicicd.config.settings import settings

logger = logging.getLogger(__name__)

class GitHubSCM(SCMInterface):
    """GitHub implementation of SCMInterface."""
    
    def __init__(self, token: Optional[str] = None):
        self.token = token or settings.GITHUB_TOKEN

    def get_pull_request_diff(self, repo: str, pr_id: int) -> Dict[str, Any]:
        diff = ""
        # 1. API Fetch
        if self.token:
            try:
                url = f"https://api.github.com/repos/{repo}/pulls/{pr_id}"
                headers = {
                    "Authorization": f"token {self.token}",
                    "Accept": "application/vnd.github.diff"
                }
                resp = requests.get(url, headers=headers, timeout=20)
                if resp.status_code == 200:
                    diff = resp.text
            except Exception as e:
                logger.warning(f"GitHub API error: {e}")

        # 2. Local Fallback
        if not diff:
            diff = self._get_local_git_diff()
            
        return {
            "diff": diff[:settings.MAX_DIFF_CHARS] if diff else "",
            "metadata": {"source": "GitHub", "repo": repo, "pr": pr_id}
        }

    def _get_local_git_diff(self) -> str:
        try:
            base = os.environ.get("GITHUB_BASE_REF", "main")
            subprocess.run(["git", "fetch", "origin", base], capture_output=True)
            res = subprocess.run(["git", "diff", f"origin/{base}...HEAD"], capture_output=True, text=True)
            return res.stdout if res.returncode == 0 else ""
        except:
            return ""
