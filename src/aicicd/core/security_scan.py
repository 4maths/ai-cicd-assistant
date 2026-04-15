import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from aicicd.domain.enums import ToolName, Decision, Severity, FindingType
from aicicd.domain.models import Finding
from aicicd.domain.results import SecurityScanResult
from aicicd.providers.llm.factory import get_provider

from aicicd.utils.diff_utils import load_path_config, filter_diff_by_paths, truncate_text


# Removed Load Config & Filter logic - now in diff_utils.py


def parse_json_safely(raw: str) -> Dict[str, Any]:
    raw = raw.strip()
    # Try to find JSON block in markdown
    match = re.search(r"```json\s*(.*?)\s*```", raw, re.DOTALL)
    if match:
        raw = match.group(1)
    else:
        # Try to find anything that looks like a JSON object
        match = re.search(r"({.*})", raw, re.DOTALL)
        if match:
            raw = match.group(1)

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
        prompt = build_security_prompt(truncate_text(filtered_diff), prompt_path)
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
