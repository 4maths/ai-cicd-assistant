import logging
from typing import Optional
from github import Github, GithubException
from aicicd.integrations.base import PublisherInterface
from aicicd.config.settings import settings

logger = logging.getLogger(__name__)

class GitHubPublisher(PublisherInterface):
    """GitHub implementation of PublisherInterface."""
    
    def __init__(self, token: Optional[str] = None):
        self.token = token or settings.GITHUB_TOKEN

    def publish_comment(self, repo: str, pr_id: int, body: str) -> bool:
        if not self.token:
            logger.error("GitHub token missing.")
            return False
        try:
            gh = Github(self.token)
            gh_repo = gh.get_repo(repo)
            pr = gh_repo.get_pull(pr_id)
            pr.create_issue_comment(body)
            return True
        except GithubException as e:
            logger.error(f"Failed to post GitHub comment: {e}")
            return False
