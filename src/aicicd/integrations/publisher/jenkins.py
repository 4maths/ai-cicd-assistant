import logging
import sys

logger = logging.getLogger(__name__)

def post_comment(body: str) -> bool:
    """Publish the result for a Jenkins build.
    Jenkins usually captures standard output as its build log.
    Advanced integrations might write to an XML/JSON file for Jenkins warnings plugin.
    For now, we output to STDOUT with clear boundaries.
    """
    try:
        print("\n" + "="*50)
        print("🤖 AI CI/CD ASSISTANT REPORT 🤖")
        print("="*50 + "\n")
        print(body)
        print("\n" + "="*50 + "\n")
        return True
    except Exception as exc:
        logger.error(f"Error publishing to Jenkins console: {exc}")
        return False
