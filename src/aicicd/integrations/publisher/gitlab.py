import logging
import gitlab
from gitlab.exceptions import GitlabError

logger = logging.getLogger(__name__)

def post_mr_comment(repo_name: str, mr_number: int, token: str, body: str, url: str = "https://gitlab.com") -> bool:
    """Posts a Markdown comment to a Gitlab Merge Request."""
    try:
        gl = gitlab.Gitlab(url, private_token=token)
        project = gl.projects.get(repo_name)
        mr = project.mergerequests.get(mr_number)
        mr.notes.create({'body': body})
        logger.info(f"Successfully posted comment to MR #{mr_number}.")
        return True
    except GitlabError as exc:
        logger.error(f"Error posting comment to Gitlab MR: {exc}")
        return False
