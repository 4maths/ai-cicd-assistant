import logging
import sys

logger = logging.getLogger(__name__)

def publish_to_stdout(body: str) -> bool:
    """Prints the formatted result to standard output."""
    print(body)
    return True
