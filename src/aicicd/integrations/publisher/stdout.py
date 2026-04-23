from aicicd.integrations.base import PublisherInterface

class StdoutPublisher(PublisherInterface):
    """Fallback publisher that prints to standard output."""
    
    def publish_comment(self, repo: str, pr_id: int, body: str) -> bool:
        print("-" * 40)
        print(f"COMMENT ON {repo} PR #{pr_id}:")
        print(body)
        print("-" * 40)
        return True
