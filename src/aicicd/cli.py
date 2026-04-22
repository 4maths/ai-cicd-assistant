from __future__ import annotations

import argparse
import sys
import json
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

from aicicd.domain.enums import ToolName, OutputFormat
from aicicd.domain.results import BaseResult

from aicicd.core.pr_review import run_pr_review
from aicicd.core.security_scan import run_security_scan
from aicicd.core.log_analysis import run_log_analysis
from aicicd.core.deploy_guard import run_deploy_guard

from aicicd.formatters.json_formatter import format_json
from aicicd.formatters.markdown_formatter import format_markdown

# =========================
# Helpers
# =========================
def read_file(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")

def write_output(content: str, output_path: str | None):
    if output_path:
        Path(output_path).write_text(content, encoding="utf-8")
    else:
        print(content)

def format_result(result: BaseResult, fmt: OutputFormat) -> str:
    if fmt == OutputFormat.JSON:
        return format_json(result)
    elif fmt == OutputFormat.MARKDOWN:
        return format_markdown(result)
    else:
        return str(result)

# =========================
# Command Handlers
# =========================
def handle_fetch(args) -> int:
    data = {"diff": "", "metadata": {}}
    if args.source == "github":
        from aicicd.integrations.scm import github
        token = os.environ.get("GITHUB_TOKEN", "")
        data = github.get_pr_diff(args.repo, args.pr, token)
    elif args.source == "gitlab":
        from aicicd.integrations.scm import gitlab
        token = os.environ.get("GITLAB_TOKEN", "")
        data = gitlab.get_mr_diff(args.repo, args.pr, token, url=os.environ.get("GITLAB_URL", "https://gitlab.com"))
    elif args.source == "local":
        from aicicd.integrations.scm import local_git
        data = local_git.get_local_diff()
    
    # Save diff.txt and metadata.json
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    
    diff_path = out_dir / "diff.txt"
    meta_path = out_dir / "metadata.json"
    
    diff_path.write_text(data.get("diff") or "", encoding="utf-8")
    meta_path.write_text(json.dumps(data.get("metadata", {}), indent=2, ensure_ascii=False), encoding="utf-8")
    
    print(f"Fetched diff to {diff_path} and metadata to {meta_path}")
    return 0

def handle_publish(args) -> int:
    content = read_file(args.file)
    success = False
    
    if args.platform == "github":
        from aicicd.integrations.publisher import github
        token = os.environ.get("GITHUB_TOKEN", "")
        success = github.post_pr_comment(args.repo, args.pr, token, content)
    elif args.platform == "gitlab":
        from aicicd.integrations.publisher import gitlab
        token = os.environ.get("GITLAB_TOKEN", "")
        success = gitlab.post_mr_comment(args.repo, args.pr, token, content, url=os.environ.get("GITLAB_URL", "https://gitlab.com"))
    elif args.platform == "jenkins":
        from aicicd.integrations.publisher import jenkins
        success = jenkins.post_comment(content)
    else:
        from aicicd.integrations.publisher import stdout
        success = stdout.publish_to_stdout(content)
        
    return 0 if success else 1


def handle_pr_review(args) -> BaseResult:
    diff_text = read_file(args.input)
    return run_pr_review(
        diff_text=diff_text, 
        provider=args.provider,
        paths_config_path=args.paths
    )


def handle_security_scan(args) -> BaseResult:
    from aicicd.domain.enums import Decision
    diff_text = read_file(args.input)
    result = run_security_scan(
        diff_text=diff_text,
        provider=args.provider,
        prompt_path=args.prompt,
        paths_path=args.paths,
    )
    
    # Logic Bypass bằng Labels đã bị gỡ bỏ theo yêu cầu tối ưu hóa
    return result



def handle_log_analysis(args) -> BaseResult:
    log_text = read_file(args.log_file)
    return run_log_analysis(log_text=log_text, provider=args.provider)


def handle_deploy_guard(args) -> BaseResult:
    return run_deploy_guard(
        url=args.url,
        provider=args.provider,
        prompt_path=args.prompt,
        timeout=args.timeout,
    )

# =========================
# CLI Definition
# =========================
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="aicicd")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # -------- FETCH --------
    fetch_parser = subparsers.add_parser("fetch")
    fetch_parser.add_argument("--source", choices=["github", "gitlab", "local"], required=True)
    fetch_parser.add_argument("--repo", help="Repository format owner/repo")
    fetch_parser.add_argument("--pr", type=int, help="PR or MR number")
    fetch_parser.add_argument("--out-dir", default=".", help="Directory to save diff.txt and metadata.json")

    # -------- PUBLISH --------
    pub_parser = subparsers.add_parser("publish")
    pub_parser.add_argument("--platform", choices=["github", "gitlab", "jenkins", "stdout"], required=True)
    pub_parser.add_argument("--repo", help="Repository format owner/repo")
    pub_parser.add_argument("--pr", type=int, help="PR or MR number")
    pub_parser.add_argument("--file", required=True, help="Markdown file to publish")

    # -------- PR REVIEW --------
    pr_parser = subparsers.add_parser(ToolName.PR_REVIEW.value)
    pr_parser.add_argument("--input", required=True, help="Path to diff file")
    pr_parser.add_argument("--provider", default="groq")
    pr_parser.add_argument("--paths", default="config/security_paths.yml", help="Path to filtering config")
    pr_parser.add_argument("--format", default="json")
    pr_parser.add_argument("--output", help="Output file path")

    # -------- SECURITY SCAN --------
    sec_parser = subparsers.add_parser(ToolName.SECURITY_SCAN.value)
    sec_parser.add_argument("--input", required=True)
    sec_parser.add_argument("--provider", default="groq")
    sec_parser.add_argument("--prompt", default="config/prompts/security_scan_prompt.md")
    sec_parser.add_argument("--paths", default="config/security_paths.yml")
    sec_parser.add_argument("--metadata", help="Path to metadata.json for label checking")
    sec_parser.add_argument("--format", default="json")
    sec_parser.add_argument("--output")

    # -------- LOG ANALYSIS --------
    log_parser = subparsers.add_parser(ToolName.LOG_ANALYSIS.value)
    log_parser.add_argument("--log-file", required=True)
    log_parser.add_argument("--provider", default="groq")
    log_parser.add_argument("--format", default="json")
    log_parser.add_argument("--output")

    # -------- DEPLOY GUARD --------
    dg_parser = subparsers.add_parser(ToolName.DEPLOY_GUARD.value)
    dg_parser.add_argument("--url", required=True)
    dg_parser.add_argument("--provider", default="groq")
    dg_parser.add_argument("--prompt", default="config/prompts/deploy_guard_prompt.md")
    dg_parser.add_argument("--timeout", type=int, default=10)
    dg_parser.add_argument("--format", default="json")
    dg_parser.add_argument("--output")

    return parser


# =========================
# Main
# =========================
def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "fetch":
        sys.exit(handle_fetch(args))
    elif args.command == "publish":
        sys.exit(handle_publish(args))

    fmt = OutputFormat(args.format)

    if args.command == ToolName.PR_REVIEW.value:
        result = handle_pr_review(args)
    elif args.command == ToolName.SECURITY_SCAN.value:
        result = handle_security_scan(args)
    elif args.command == ToolName.LOG_ANALYSIS.value:
        result = handle_log_analysis(args)
    elif args.command == ToolName.DEPLOY_GUARD.value:
        result = handle_deploy_guard(args)
    else:
        raise ValueError(f"Unknown command: {args.command}")

    output = format_result(result, fmt)
    write_output(output, args.output)

    exit_code = result.get_exit_code()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()