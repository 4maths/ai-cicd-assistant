import logging
from github import Github, GithubException

logger = logging.getLogger(__name__)

def post_pr_comment(repo_name: str, pr_number: int, token: str, body: str) -> bool:
    """Posts a Markdown comment to a Github Pull Request."""
    try:
        gh = Github(token)
        repo = gh.get_repo(repo_name)
        pr = repo.get_pull(pr_number)
        pr.create_issue_comment(body)
        logger.info(f"Successfully posted comment to PR #{pr_number}.")
        return True
    except GithubException as exc:
        logger.error(f"Error posting comment to Github PR: {exc}")
        return False
