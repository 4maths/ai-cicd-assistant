# AI CI/CD Assistant

A production-grade, multi-platform AI-powered CI/CD Assistant built with Python. 

This tool works seamlessly across GitHub, GitLab, Jenkins, and Local Git repositories to provide AI-driven Pull Request Reviews, Log Validation, Security Scanning, and Deployment Health Checks.

## Architecture

The project strictly follows a **Clean Architecture (CLI-driven)** pattern. The `Core` modules perform business logic offline by reading files, ensuring there are naturally no strict tie-ins to any single CI platform. 
Platform-specific integrations are enclosed within the `integrations` modules and bound to the system via the `fetch` and `publish` commands.

## Installation

You can install this project directly via pip from within the root directory:

```bash
pip install -e .
```

This will register the `aicicd` CLI command globally.

## Features & Usage

### 1. Fetching Integration Data
Fetch diffs and logs from a supported platform (github, gitlab, local).

```bash
export GITHUB_TOKEN="ghp_xxx"
aicicd fetch --source github --repo my-org/my-project --pr 123 --out-dir ./payload
```
*Creates `./payload/diff.txt` and `./payload/metadata.json`*

### 2. Core AI Modules
Run core tools against the fetched files. Core logic is completely disconnected from external APIs aside from the LLM Provider.

#### PR Review
```bash
aicicd pr-review --input ./payload/diff.txt --format markdown --output review.md
```

#### Security Scan (Rule-based)
```bash
aicicd security-scan --input ./payload/diff.txt --rules config/security_rules.yml --format markdown --output review.md
```

#### Log Analysis
```bash
aicicd log-analysis --log-file failed_CI_Log.txt --format markdown --output review.md
```

#### Deploy Guard
```bash
aicicd deploy-guard --url "http://myapp.com/health" --format markdown --output review.md
```

### 3. Publishing Data
Publish validation results back to your provider. (github, gitlab, jenkins, stdout)

```bash
aicicd publish --platform github --repo my-org/my-project --pr 123 --file review.md
```

## Running Tests

To run the unit tests, install test dependencies and use pytest:

```bash
pip install ".[test]"
pytest -v tests/
```
