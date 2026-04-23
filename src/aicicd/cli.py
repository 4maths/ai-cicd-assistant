import argparse
import sys
import os
import json
import logging
from pathlib import Path

from aicicd.config.settings import settings
from aicicd.domain.enums import ToolName, OutputFormat
from aicicd.core.reviewer import ReviewService
from aicicd.core.security import SecurityService
from aicicd.core.analyzer import LogAnalysisService
from aicicd.core.guard import DeployGuardService

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("aicicd.cli")

class CLI:
    """Refactored CLI with clean routing and centralized logic."""
    
    def __init__(self):
        self.parser = self._build_parser()

    def _build_parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(prog="aicicd", description="AI CI/CD Assistant")
        subparsers = parser.add_subparsers(dest="command", required=True)

        # FETCH: Get diff/data
        fetch = subparsers.add_parser("fetch")
        fetch.add_argument("--source", choices=["github", "gitlab", "local"], required=True)
        fetch.add_argument("--repo", help="owner/repo")
        fetch.add_argument("--pr", type=int, help="PR number")

        # REVIEW: AI Code Review
        review = subparsers.add_parser("review")
        review.add_argument("--input", required=True)
        review.add_argument("--provider")

        # SEC: Security Scan
        sec = subparsers.add_parser("security")
        sec.add_argument("--input", required=True)
        sec.add_argument("--provider")

        # LOG: Log Analysis
        log = subparsers.add_parser("log")
        log.add_argument("--file", required=True)
        log.add_argument("--provider")

        # DEPLOY: Deploy Guard
        dg = subparsers.add_parser("guard")
        dg.add_argument("--url", required=True)
        dg.add_argument("--provider")

        # PUBLISH: Post results
        pub = subparsers.add_parser("publish")
        pub.add_argument("--platform", choices=["github", "gitlab", "stdout"], required=True)
        pub.add_argument("--repo")
        pub.add_argument("--pr", type=int)
        pub.add_argument("--file", required=True)

        return parser

    def run(self):
        args = self.parser.parse_args()
        try:
            if args.command == "fetch":
                self.handle_fetch(args)
            elif args.command == "publish":
                self.handle_publish(args)
            elif args.command == "review":
                result = ReviewService(args.provider).review(self._read(args.input))
                self._output(result)
            elif args.command == "security":
                result = SecurityService(args.provider).scan(self._read(args.input))
                self._output(result)
            elif args.command == "log":
                result = LogAnalysisService(args.provider).analyze(self._read(args.file))
                self._output(result)
            elif args.command == "guard":
                result = DeployGuardService(args.provider).check(args.url)
                self._output(result)
        except Exception as e:
            logger.error(f"Execution failed: {e}")
            sys.exit(1)

    def handle_fetch(self, args):
        """Unified fetch routing."""
        scm = self._get_scm(args.source)
        data = scm.get_pull_request_diff(args.repo, args.pr)
        Path("diff.txt").write_text(data["diff"], encoding="utf-8")
        Path("metadata.json").write_text(json.dumps(data["metadata"]), encoding="utf-8")
        logger.info(f"Data fetched successfully to diff.txt")

    def handle_publish(self, args):
        """Unified publish routing."""
        content = self._read(args.file)
        pub = self._get_publisher(args.platform)
        if pub.publish_comment(args.repo, args.pr, content):
            logger.info("Content published successfully.")
        else:
            sys.exit(1)

    def _get_scm(self, source):
        if source == "github":
            from aicicd.integrations.scm.github import GitHubSCM
            return GitHubSCM()
        if source == "gitlab":
            from aicicd.integrations.scm.gitlab import GitLabSCM
            return GitLabSCM()
        raise NotImplementedError(f"SCM {source} not supported yet.")

    def _get_publisher(self, platform):
        if platform == "github":
            from aicicd.integrations.publisher.github import GitHubPublisher
            return GitHubPublisher()
        if platform == "gitlab":
            from aicicd.integrations.publisher.gitlab import GitLabPublisher
            return GitLabPublisher()
        
        from aicicd.integrations.publisher.stdout import StdoutPublisher
        return StdoutPublisher()

    def _read(self, path) -> str:
        return Path(path).read_text(encoding="utf-8")

    def _output(self, result):
        from aicicd.formatters.markdown_formatter import format_markdown
        print(format_markdown(result))
        sys.exit(result.get_exit_code())

def main():
    CLI().run()

if __name__ == "__main__":
    main()