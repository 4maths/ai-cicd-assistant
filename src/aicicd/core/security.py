from typing import Optional, List
from aicicd.core.base import BaseService
from aicicd.domain.enums import ToolName, Decision, Severity, FindingType
from aicicd.domain.models import Finding
from aicicd.domain.results import SecurityScanResult
from aicicd.utils.prompt_loader import load_prompt
from aicicd.utils.json_tools import parse_json_safely
from aicicd.utils.regex_scanner import RegexScanner
from aicicd.utils.chunking import chunk_diff
from aicicd.utils.diff_utils import load_path_config, filter_diff_by_paths
from aicicd.config.settings import settings

class SecurityService(BaseService):
    """Hybrid Security Scanner: Regex Pattern Matching + AI Context Analysis."""
    
    def scan(self, diff_text: str, paths_config: str = settings.SECURITY_PATHS_PATH) -> SecurityScanResult:
        result = SecurityScanResult(
            tool=ToolName.SECURITY_SCAN,
            decision=Decision.APPROVE,
            summary="Khởi tạo quét bảo mật..."
        )
        
        if not diff_text.strip():
            result.summary = "Diff rỗng."
            return result

        # 1. Pipeline: Filter -> Chunk
        path_config = load_path_config(paths_config)
        filtered_diff = filter_diff_by_paths(diff_text, path_config)
        
        if not filtered_diff.strip():
            result.summary = "Không có mã nguồn cần quét sau lọc."
            return result

        chunks = chunk_diff(filtered_diff, chunk_size=settings.CHUNK_SIZE)
        scanner = RegexScanner(rules_path=settings.SECURITY_RULES_PATH)
        all_findings = []

        # 2. Hybrid Processing
        for i, chunk in enumerate(chunks):
            self.logger.info(f"Scanning chunk {i+1}/{len(chunks)}")
            
            # Phase A: Regex (Fast & Deterministic)
            all_findings.extend(scanner.scan(chunk))

            # Phase B: LLM (Contextual)
            prompt = load_prompt("security_scan_prompt", {"diff": chunk})
            if prompt:
                try:
                    response = self.llm.complete(prompt)
                    data = parse_json_safely(response)
                    if data and "findings" in data:
                        all_findings.extend(self._map_ai_findings(data["findings"]))
                except Exception as e:
                    self.logger.error(f"LLM Error on chunk {i+1}: {e}")

        # 3. Aggregation
        result.findings = all_findings
        self._set_final_decision(result)
        result.summary = f"Hoàn thành quét {len(chunks)} đoạn mã. Phát hiện {len(all_findings)} vấn đề."
        return result

    def _map_ai_findings(self, raw_findings: List[dict]) -> List[Finding]:
        findings = []
        for item in raw_findings:
            try:
                severity = Severity(str(item.get("severity", "LOW")).upper())
            except ValueError:
                severity = Severity.LOW
                
            findings.append(Finding(
                type=FindingType.SECURITY,
                severity=severity,
                title=str(item.get("title", "AI Detection")),
                description=str(item.get("description", "")),
                file=str(item.get("file", "unknown")),
                suggestion=str(item.get("suggestion", "")),
                metadata={"source": "AI"}
            ))
        return findings

    def _set_final_decision(self, result: SecurityScanResult):
        high_critical = [f for f in result.findings if f.severity in (Severity.HIGH, Severity.CRITICAL)]
        if high_critical:
            result.decision = Decision.WARN  # Maintain warn for human review
            result.has_blocking_issues = True
        elif any(f.severity == Severity.MEDIUM for f in result.findings):
            result.decision = Decision.WARN
