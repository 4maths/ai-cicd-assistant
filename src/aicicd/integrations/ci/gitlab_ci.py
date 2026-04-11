import logging
import gitlab
from gitlab.exceptions import GitlabError

logger = logging.getLogger(__name__)

MAX_LOG_CHARS = 10000

def get_workflow_logs(repo_name: str, pipeline_id: int, token: str, url: str = "https://gitlab.com") -> str:
    """Gets failure logs for a given GitLab CI pipeline."""
    try:
        gl = gitlab.Gitlab(url, private_token=token)
        project = gl.projects.get(repo_name)
        pipeline = project.pipelines.get(pipeline_id)
        jobs = pipeline.jobs.list(all=True)

        log_parts = []
        for job in jobs:
            if job.status == "failed":
                job_header = f"FAILED JOB: {job.name} (Stage: {job.stage})"
                try:
                    # gitlab job.trace() returns bytes
                    full_trace = job.trace().decode("utf-8")
                    if len(full_trace) > MAX_LOG_CHARS:
                        full_trace = "...\n" + full_trace[-MAX_LOG_CHARS:]
                    log_parts.append(job_header + "\n" + full_trace)
                except Exception as trace_exc:
                    log_parts.append(job_header + f"\n[Could not fetch trace: {trace_exc}]")

        combined = "\n\n".join(log_parts)
        if len(combined) > MAX_LOG_CHARS:
            combined = "...\n" + combined[-MAX_LOG_CHARS:]

        return combined

    except GitlabError as exc:
        logger.error(f"Error fetching pipeline logs from GitLab: {exc}")
        return ""