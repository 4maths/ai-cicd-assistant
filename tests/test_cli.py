import pytest
from unittest.mock import patch, MagicMock
import argparse
from aicicd.cli import build_parser

def test_cli_parser_pr_review():
    parser = build_parser()
    args = parser.parse_args(["pr-review", "--input", "diff.txt", "--format", "markdown"])
    assert args.command == "pr-review"
    assert args.input == "diff.txt"
    assert args.format == "markdown"

def test_cli_parser_fetch():
    parser = build_parser()
    args = parser.parse_args(["fetch", "--source", "github", "--pr", "123"])
    assert args.command == "fetch"
    assert args.source == "github"
    assert args.pr == 123

def test_cli_parser_publish():
    parser = build_parser()
    with pytest.raises(SystemExit):
        args = parser.parse_args(["publish", "--platform", "slack"])
    
def test_cli_parser_publish_valid():
    parser = build_parser()
    args = parser.parse_args(["publish", "--platform", "github", "--file", "result.md"])
    assert args.command == "publish"
    assert args.platform == "github"
    assert args.file == "result.md"
