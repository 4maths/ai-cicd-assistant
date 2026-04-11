import logging
from github import Github, GithubException

logger = logging.getLogger(__name__)

MAX_LOG_CHARS = 3000

def get_workflow_logs(repo_name: str, run_id: int, token: str) -> str:
    """Gets failure logs for a given GitHub Actions workflow run."""
    try:
        gh = Github(token)
        repo = gh.get_repo(repo_name)
        run = repo.get_workflow_run(run_id)

        log_parts = []
        for job in run.jobs():
            if str(job.conclusion).lower() == "failure":
                job_header = f"FAILED JOB: {job.name}"
                step_logs = []
                for step in job.steps:
                    if str(step.conclusion).lower() == "failure":
                        step_logs.append(f"[Failed Step: {step.name}]")
                log_parts.append(job_header + "\n" + "\n".join(step_logs))

        combined = "\n\n".join(log_parts)

        if len(combined) > MAX_LOG_CHARS:
            logger.info(f"Log too large, truncating to {MAX_LOG_CHARS} chars.")
            return "...\n" + combined[-MAX_LOG_CHARS:]

        return combined

    except GithubException as exc:
        logger.error(f"Error fetching workflow logs from GitHub: {exc}")
        return ""
