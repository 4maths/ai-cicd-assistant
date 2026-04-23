import logging
import gitlab
from gitlab.exceptions import GitlabError
from aicicd.integrations.base import PublisherInterface
from aicicd.config.settings import settings

logger = logging.getLogger(__name__)

class GitLabPublisher(PublisherInterface):
    """GitLab implementation of PublisherInterface."""

    def __init__(self, token: Optional[str] = None, url: Optional[str] = None):
        self.token = token or settings.GITLAB_TOKEN
        self.url = url or settings.GITLAB_URL

    def publish_comment(self, repo: str, pr_id: int, body: str) -> bool:
        if not self.token:
            logger.error("GitLab token missing.")
            return False
        try:
            gl = gitlab.Gitlab(self.url, private_token=self.token)
            project = gl.projects.get(repo)
            mr = project.mergerequests.get(pr_id)
            mr.notes.create({'body': body})
            return True
        except GitlabError as e:
            logger.error(f"Failed to post GitLab comment: {e}")
            return False
