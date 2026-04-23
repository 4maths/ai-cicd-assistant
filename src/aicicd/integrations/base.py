from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class SCMInterface(ABC):
    """Interface for Source Control Management (GitHub, GitLab, etc)."""
    @abstractmethod
    def get_pull_request_diff(self, repo: str, pr_id: int) -> Dict[str, Any]:
        pass

class PublisherInterface(ABC):
    """Interface for publishing results (comments, status, etc)."""
    @abstractmethod
    def publish_comment(self, repo: str, pr_id: int, body: str) -> bool:
        pass
