import logging
import requests

logger = logging.getLogger(__name__)

MAX_LOG_CHARS = 10000

def get_workflow_logs(job_url: str, username: str, token: str) -> str:
    """Gets failure logs for a Jenkins build via REST API.
    job_url should be the full job url, e.g. http://jenkins/job/MyJob/12/
    """
    try:
        console_url = f"{job_url.rstrip('/')}/consoleText"
        auth = (username, token) if username and token else None
        
        response = requests.get(console_url, auth=auth, timeout=10)
        response.raise_for_status()

        full_log = response.text
        if len(full_log) > MAX_LOG_CHARS:
            logger.info(f"Log too large, truncating to {MAX_LOG_CHARS} chars.")
            return "...\n" + full_log[-MAX_LOG_CHARS:]
            
        return full_log

    except requests.exceptions.RequestException as exc:
        logger.error(f"Error fetching workflow logs from Jenkins: {exc}")
        return ""
