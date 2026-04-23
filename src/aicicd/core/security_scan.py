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
from aicicd.utils.json_tools import parse_json_safely

logger = logging.getLogger(__name__)


# Removed Load Config & Filter logic - now in diff_utils.py


# Removed local parse_json_safely - now using shared version from json_tools


from aicicd.utils.prompt_loader import load_prompt

def build_security_prompt(diff: str, prompt_template_path: Optional[str] = None) -> str:
    # If a specific path is provided, we use it for backward compatibility or special cases
    if prompt_template_path:
        path = Path(prompt_template_path)
        if path.exists():
            template = path.read_text(encoding="utf-8")
            return template.replace("{{diff}}", diff)
            
    # Default behavior: load from config/prompts/security_scan_prompt.md
    prompt = load_prompt("security_scan_prompt", {"diff": diff})
    
    if not prompt:
        # Fallback template if file missing
        prompt = f"""Analyze Code Diff for security vulnerabilities (OWASP Top 10).
Return ONLY JSON:
{{
  "summary": "...",
  "findings": [{{"id": "..", "title": "..", "description": "..", "severity": "HIGH|MEDIUM|LOW", "file": "..", "suggestion": ".."}}],
  "decision": "BLOCK|WARN|APPROVE"
}}
Code Diff:
{diff}
"""
    return prompt


from aicicd.utils.chunking import chunk_diff
from aicicd.utils.regex_scanner import RegexScanner

def run_security_scan(diff_text: str, provider: str = "groq", prompt_path: Optional[str] = None, paths_path: str = "config/security_paths.yml") -> SecurityScanResult:
    result = SecurityScanResult(
        tool=ToolName.SECURITY_SCAN,
        decision=Decision.APPROVE,
        summary="Phân tích bảo mật mã nguồn (Groq Intelligence + Regex Scanner)",
    )
    
    if not diff_text or not diff_text.strip():
        result.summary = "Bản diff rỗng, không có gì để quét."
        return result

    # 1. Load config & Filter diff
    path_config = load_path_config(paths_path)
    filtered_diff = filter_diff_by_paths(diff_text, path_config)
    
    if not filtered_diff.strip():
        result.summary = "Không có file nguồn nào cần quét sau khi lọc."
        return result

    # 2. Split into chunks for processing
    chunks = chunk_diff(filtered_diff, chunk_size=1500)
    
    all_findings = []
    llm = get_provider(provider)
    scanner = RegexScanner()

    # 3. Process each chunk
    for i, chunk in enumerate(chunks):
        logger.info(f"Processing security chunk {i+1}/{len(chunks)}")
        
        # 3a. Primary Regex Scan
        regex_findings = scanner.scan(chunk)
        all_findings.extend(regex_findings)

        # 3b. LLM Scan for context and subtle issues
        prompt = build_security_prompt(chunk, prompt_path)
        try:
            raw_response = llm.complete(prompt, max_tokens=1000)
            data = parse_json_safely(raw_response)
            
            if data:
                raw_findings = data.get("findings", [])
                for item in raw_findings:
                    findings_list = []
                    sev_str = str(item.get("severity", "LOW")).upper()
                    try:
                        severity_enum = Severity(sev_str)
                    except ValueError:
                        severity_enum = Severity.LOW
                        
                    finding = Finding(
                        type=FindingType.SECURITY,
                        severity=severity_enum,
                        title=str(item.get("title", "AI Detection")),
                        description=str(item.get("description", "")),
                        file=str(item.get("file", "unknown")),
                        suggestion=str(item.get("suggestion", "")),
                        metadata={
                            "owasp_category": str(item.get("owasp_category", "N/A")),
                            "source": "AI"
                        }
                    )
                    all_findings.append(finding)
        except Exception as e:
            logger.error(f"LLM Scan failed for chunk {i+1}: {e}")
            result.errors.append(f"Chunk {i+1} LLM Error: {str(e)}")

    # 4. Aggregate findings
    result.findings = all_findings
    result.high_count = sum(1 for f in all_findings if f.severity in [Severity.HIGH, Severity.CRITICAL])
    result.medium_count = sum(1 for f in all_findings if f.severity == Severity.MEDIUM)
    result.low_count = sum(1 for f in all_findings if f.severity == Severity.LOW)

    # 5. Final Decision
    if result.high_count > 0:
        result.decision = Decision.WARN
        result.has_blocking_issues = True
    elif result.medium_count > 0:
        result.decision = Decision.WARN
    else:
        result.decision = Decision.APPROVE

    result.summary = f"Đã hoàn thành quét {len(chunks)} đoạn mã. Phát hiện {len(all_findings)} lỗi bảo mật tiềm ẩn."
    return result

