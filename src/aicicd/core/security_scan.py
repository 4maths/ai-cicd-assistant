import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple
import yaml

from aicicd.domain.enums import ToolName, Decision, Severity, FindingType
from aicicd.domain.models import Finding
from aicicd.domain.results import SecurityScanResult

logger = logging.getLogger(__name__)

DEFAULT_RULES = [
    {
        "id": "hardcoded_secret",
        "description": "Phát hiện secret/token/password hardcode",
        "pattern": r'(?i)(api_key|apikey|token|secret|password|access_token|refresh_token|github_token)\s*[:=]\s*["\'][^"\']+["\']',
        "severity": "HIGH",
        "why_it_matters": "Secret hardcode có thể bị lộ qua git history, log hoặc người có quyền truy cập repo.",
        "suggested_fix": "Chuyển secret sang biến môi trường hoặc secret manager.",
        "allow_override": False,
    },
    {
        "id": "debug_mode_enabled",
        "description": "Phát hiện debug mode bật trong code",
        "pattern": r'(?i)(debug\s*=\s*True|app\.run\(.*debug\s*=\s*True)',
        "severity": "MEDIUM",
        "why_it_matters": "Debug mode có thể làm lộ stack trace hoặc thông tin nội bộ trong production.",
        "suggested_fix": "Tắt debug mode ở production và điều khiển bằng biến môi trường.",
        "allow_override": True,
    },
    {
        "id": "subprocess_shell_true",
        "description": "Phát hiện subprocess shell=True có thể gây command injection",
        "pattern": r'(?s)subprocess\.(run|Popen)\(.*?shell\s*=\s*True',
        "severity": "HIGH",
        "why_it_matters": "shell=True có thể dẫn tới command injection nếu input không được kiểm soát.",
        "suggested_fix": "Tránh dùng shell=True, truyền command dưới dạng list thay vì string.",
        "allow_override": False,
    },
]

DEFAULT_PATH_CONFIG = {
    "include_paths": [],
    "exclude_paths": ["tests/", "config/", ".github/", ".venv/", "docs/", "examples/"],
    "exclude_extensions": [".md", ".txt", ".json", ".lock"],
    "exclude_file_patterns": [r".*\.min\.js$"],
}


def load_rules(config_path: str) -> List[Dict[str, Any]]:
    path = Path(config_path)
    if not path.exists():
        logger.warning(f"Không tìm thấy config tại: {config_path}. Dùng default rules.")
        return DEFAULT_RULES

    try:
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            
        rules = data.get("rules", [])
        if not isinstance(rules, list) or not rules:
            return DEFAULT_RULES
        return rules
    except Exception as exc:
        logger.error(f"Lỗi load security rules tại {config_path}: {exc}")
        return DEFAULT_RULES


def load_path_config(config_path: str) -> Dict[str, Any]:
    path = Path(config_path)
    if not path.exists():
        return DEFAULT_PATH_CONFIG

    try:
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        return {
            "include_paths": data.get("include_paths", DEFAULT_PATH_CONFIG["include_paths"]),
            "exclude_paths": data.get("exclude_paths", DEFAULT_PATH_CONFIG["exclude_paths"]),
            "exclude_extensions": data.get("exclude_extensions", DEFAULT_PATH_CONFIG["exclude_extensions"]),
            "exclude_file_patterns": data.get("exclude_file_patterns", DEFAULT_PATH_CONFIG["exclude_file_patterns"]),
        }
    except Exception as exc:
        logger.error(f"Lỗi load security path config tại {config_path}: {exc}")
        return DEFAULT_PATH_CONFIG


def should_scan_file(filename: str, path_config: Dict[str, Any]) -> bool:
    include_paths = path_config.get("include_paths", [])
    exclude_paths = path_config.get("exclude_paths", [])
    exclude_extensions = path_config.get("exclude_extensions", [])
    exclude_file_patterns = path_config.get("exclude_file_patterns", [])

    if include_paths:
        if not any(filename == item or filename.startswith(item) for item in include_paths):
            return False

    if any(filename.startswith(prefix) for prefix in exclude_paths):
        return False

    if any(filename.endswith(ext) for ext in exclude_extensions):
        return False

    if any(re.match(pat, filename) for pat in exclude_file_patterns):
        return False

    return True


def extract_files_from_diff(diff_text: str) -> List[Tuple[str, str]]:
    files = []
    current_file = None
    current_patch = []

    for line in diff_text.splitlines():
        if line.startswith("diff --git "):
            if current_file and current_patch:
                files.append((current_file, "\n".join(current_patch)))
            parts = line.split(" ")
            if len(parts) >= 4:
                path = parts[3]
                if path.startswith("b/"):
                    path = path[2:]
                current_file = path
            current_patch = []
        elif current_file:
            current_patch.append(line)

    if current_file and current_patch:
        files.append((current_file, "\n".join(current_patch)))

    return files


def extract_snippet(text: str, pattern: str) -> str:
    try:
        match = re.search(pattern, text)
        if not match:
            return ""
        start = max(match.start() - 40, 0)
        end = min(match.end() + 80, len(text))
        snippet = text[start:end].strip().replace("\n", " ")
        if len(snippet) > 160:
            snippet = snippet[:160] + "..."
        return snippet
    except re.error:
        return ""


def run_security_scan(diff_text: str, rules_path: str, paths_path: str) -> SecurityScanResult:
    result = SecurityScanResult(
        tool=ToolName.SECURITY_SCAN,
        decision=Decision.APPROVE,
        summary="Scanning codebase for security vulnerabilities.",
    )
    
    if not diff_text or not diff_text.strip():
        result.errors.append("Diff input is empty.")
        return result
        
    rules = load_rules(rules_path)
    path_config = load_path_config(paths_path)
    
    files_data = extract_files_from_diff(diff_text)
    
    findings_list = []
    
    for filename, patch_text in files_data:
        if not should_scan_file(filename, path_config):
            continue
            
        for rule in rules:
            pattern = str(rule.get("pattern", "")); 
            if not pattern: continue
            
            try:
                if re.search(pattern, patch_text):
                    # Validate Severity
                    sev_str = str(rule.get("severity", "LOW")).upper()
                    try: severity_enum = Severity(sev_str)
                    except ValueError: severity_enum = Severity.LOW
                    
                    snippet = extract_snippet(patch_text, pattern)
                    
                    finding = Finding(
                        type=FindingType.SECURITY,
                        severity=severity_enum,
                        title=str(rule.get("id", "Unknown Rule")),
                        description=str(rule.get("description", "Vulnerability found")),
                        file=filename,
                        suggestion=str(rule.get("suggested_fix", "")),
                        metadata={
                            "allow_override": bool(rule.get("allow_override", False)),
                            "why_it_matters": str(rule.get("why_it_matters", "")),
                            "snippet": snippet
                        }
                    )
                    findings_list.append(finding)
            except re.error as exc:
                logger.error(f"Vulnerability Regex failed: {exc}")
                
    # Update result
    result.findings = findings_list
    result.high_count = sum(1 for f in findings_list if f.severity == Severity.HIGH)
    result.medium_count = sum(1 for f in findings_list if f.severity == Severity.MEDIUM)
    result.low_count = sum(1 for f in findings_list if f.severity == Severity.LOW)
    
    if result.high_count > 0:
        result.decision = Decision.BLOCK
        result.has_blocking_issues = True
        result.summary = f"Blocked: found {result.high_count} HIGH severity issues."
    elif result.medium_count > 0:
        result.decision = Decision.WARN
        result.summary = f"Warning: found {result.medium_count} MEDIUM severity issues."
    else:
        result.decision = Decision.APPROVE
        if len(findings_list) > 0:
            result.summary = f"Approved with {result.low_count} LOW severity issues."
        else:
            result.summary = "No security issues detected in diff."
            
    return result
