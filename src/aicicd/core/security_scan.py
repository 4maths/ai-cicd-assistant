import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from aicicd.domain.enums import ToolName, Decision, Severity, FindingType
from aicicd.domain.models import Finding
from aicicd.domain.results import SecurityScanResult
from aicicd.providers.llm.factory import get_provider

logger = logging.getLogger(__name__)

DEFAULT_PATH_CONFIG = {
    "include_paths": [],
    "exclude_paths": ["tests/", "config/", ".github/", ".venv/", "docs/", "examples/"],
    "exclude_extensions": [".md", ".txt", ".json", ".lock"],
    "exclude_file_patterns": [r".*\.min\.js$"],
}


def load_path_config(config_path: str) -> Dict[str, Any]:
    path = Path(config_path)
    if not path.exists():
        return DEFAULT_PATH_CONFIG

    try:
        import yaml
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


def filter_diff_by_paths(diff_text: str, path_config: Dict[str, Any]) -> str:
    """Lọc diff_text chỉ giữ lại các file cần scan để tiết kiệm token."""
    filtered_lines = []
    include_current = True
    
    for line in diff_text.splitlines():
        if line.startswith("diff --git "):
            parts = line.split(" ")
            if len(parts) >= 4:
                path = parts[3]
                if path.startswith("b/"):
                    path = path[2:]
                include_current = should_scan_file(path, path_config)
            else:
                include_current = True
                
        if include_current:
            filtered_lines.append(line)
            
    return "\n".join(filtered_lines)


def parse_json_safely(raw: str) -> Dict[str, Any]:
    raw = raw.strip()
    if "```json" in raw:
        raw = raw.split("```json")[-1].split("```")[0]
    elif "```" in raw:
        raw = raw.split("```")[-1].split("```")[0]

    try:
        return json.loads(raw.strip())
    except json.JSONDecodeError as e:
        logger.error(f"Cannot parse Security JSON: {str(e)}\nRaw: {raw}")
        return {}


def build_security_prompt(diff: str, prompt_template_path: Optional[str] = None) -> str:
    template = ""
    if prompt_template_path:
        path = Path(prompt_template_path)
        if path.exists():
            template = path.read_text(encoding="utf-8")
            
    if not template:
        # Fallback template if file missing
        template = """Phân tích Code Diff sau theo chuẩn OWASP Top 10.
Trả về JSON format:
{
  "summary": "...",
  "findings": [{"id": "..", "title": "..", "description": "..", "severity": "HIGH|MEDIUM|LOW", "file": "..", "suggestion": "..", "owasp_category": "..", "why_it_matters": "..", "snippet": ".."}],
  "decision": "BLOCK|WARN|APPROVE"
}
Code Diff:
{{diff}}
"""
    return template.replace("{{diff}}", diff)


def run_security_scan(diff_text: str, provider: str = "groq", prompt_path: Optional[str] = None, paths_path: str = "config/security_paths.yml") -> SecurityScanResult:
    result = SecurityScanResult(
        tool=ToolName.SECURITY_SCAN,
        decision=Decision.APPROVE,
        summary="Phân tích bảo mật mã nguồn (AI-based - OWASP Top 10)",
    )
    
    if not diff_text or not diff_text.strip():
        result.summary = "Bản diff rỗng, không có gì để quét."
        return result

    # 1. Load config & Filter diff
    path_config = load_path_config(paths_path)
    filtered_diff = filter_diff_by_paths(diff_text, path_config)
    
    if not filtered_diff.strip():
        result.summary = "Không có file nào thỏa mãn điều kiện quét sau khi lọc path."
        return result

    # 2. Call AI
    try:
        llm = get_provider(provider)
        prompt = build_security_prompt(filtered_diff, prompt_path)
        raw_response = llm.complete(prompt, max_tokens=2000)
        data = parse_json_safely(raw_response)
    except Exception as e:
        logger.error(f"Lỗi gọi AI trong Security Scan: {e}")
        result.errors.append(f"AI Provider Error: {str(e)}")
        result.decision = Decision.ERROR
        return result

    if not data:
        result.errors.append("Không parse được kết quả JSON từ AI.")
        result.decision = Decision.ERROR
        return result

    # 3. Process findings
    result.summary = data.get("summary", "Đã hoàn thành quét bảo mật.")
    raw_findings = data.get("findings", [])
    
    findings_list = []
    for item in raw_findings:
        sev_str = str(item.get("severity", "LOW")).upper()
        try:
            severity_enum = Severity(sev_str)
        except ValueError:
            severity_enum = Severity.LOW
            
        finding = Finding(
            type=FindingType.SECURITY,
            severity=severity_enum,
            title=str(item.get("title", "Lỗ hổng bảo mật")),
            description=str(item.get("description", "")),
            file=str(item.get("file", "unknown")),
            suggestion=str(item.get("suggestion", "")),
            metadata={
                "owasp_category": str(item.get("owasp_category", "N/A")),
                "why_it_matters": str(item.get("why_it_matters", "")),
                "snippet": str(item.get("snippet", ""))
            }
        )
        findings_list.append(finding)

    result.findings = findings_list
    result.high_count = sum(1 for f in findings_list if f.severity == Severity.HIGH)
    result.medium_count = sum(1 for f in findings_list if f.severity == Severity.MEDIUM)
    result.low_count = sum(1 for f in findings_list if f.severity == Severity.LOW)

    # 4. Final Decision
    decision_str = str(data.get("decision", "APPROVE")).upper()
    if decision_str == "BLOCK" or result.high_count > 0:
        result.decision = Decision.BLOCK
        result.has_blocking_issues = True
    elif decision_str == "WARN" or result.medium_count > 0:
        result.decision = Decision.WARN
    else:
        result.decision = Decision.APPROVE

    return result
