from aicicd.domain.results import (
    BaseResult,
    PRReviewResult,
    SecurityScanResult,
    LogAnalysisResult,
    DeployGuardResult
)
from aicicd.domain.enums import ToolName, Severity


def render_list(items: list, fallback: str = "Không có.") -> str:
    if not items:
        return f"- {fallback}"
    return "\n".join(f"- {item}" for item in items)


def render_errors(errors: list) -> str:
    if not errors:
        return ""
    lines = "\n".join(f"- ❌ {err}" for err in errors)
    return f"\n> [!CAUTION]\n> **Lỗi hệ thống:**\n{lines}\n"


def _format_pr_review(result: PRReviewResult) -> str:
    risk_icon = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🔴", "CRITICAL": "🔥"}.get(str(result.risk_level), "⚪")
    decision_icon = {"APPROVE": "✅", "WARN": "⚠️", "BLOCK": "🚫", "ERROR": "❌"}.get(str(result.decision), "⚪")
    status_line = "APPROVED" if result.approved else "CHANGES REQUESTED"

    return f"""## AI PR Review

**Trạng thái:** {status_line}  
**Decision:** {decision_icon} {result.decision}  
**Mức độ rủi ro:** {risk_icon} {result.risk_level}  
**Risk score:** {result.risk_score}/100
{render_errors(result.errors)}

### Tóm tắt
{result.summary}

### Bug / Logic Error
{render_list(result.bugs)}

### Bảo mật
{render_list(result.security_issues)}

### Chất lượng code
{render_list(result.code_quality)}

### Gợi ý cải thiện
{render_list(result.suggestions)}
"""


def _format_security_scan(result: SecurityScanResult) -> str:
    decision = result.decision

    if not result.findings:
        return f"""## AI Security Scan

**Decision:** {decision}  
**Tóm tắt:** {result.summary}
{render_errors(result.errors)}

Không phát hiện vấn đề bảo mật.
"""

    lines = []
    for f in result.findings:
        sev_icon = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🔴"}.get(str(f.severity), "⚪")
        allow_override = f.metadata.get("allow_override", False)
        snippet = f.metadata.get("snippet", "")
        
        snippet_block = f"\n  - Snippet: `{snippet}`" if snippet else ""
        lines.append(
            f"- **{sev_icon} {f.severity}** | `{f.file}` | {f.description} (`{f.title}`)\n"
            f"  - Why it matters: {f.metadata.get('why_it_matters', '')}\n"
            f"  - Suggested fix: {f.suggestion}"
            f"{snippet_block}"
        )

    return f"""## AI Security Scan

**Decision:** {decision}  
**Tóm tắt:** Phát hiện {len(result.findings)} vấn đề (HIGH: {result.high_count}, MEDIUM: {result.medium_count}, LOW: {result.low_count})

### Findings
{chr(10).join(lines)}

---
*AI CI/CD Assistant — Security Scanner*
"""


def _format_log_analysis(result: LogAnalysisResult) -> str:
    analysis = result.analysis
    if not analysis:
        return f"""## AI CI Log Analysis
        
**Trạng thái:** Lỗi phân tích
Mô tả: {result.summary}
"""

    conf_icon = ""
    if analysis.confidence >= 0.8:
        conf_icon = "🟢"
    elif analysis.confidence >= 0.5:
        conf_icon = "🟡"
    else:
        conf_icon = "🔴"

    fix_cmd = ""
    if analysis.fix_command:
        fix_cmd = f"\n\n### Lệnh gợi ý sửa lỗi\n```bash\n{analysis.fix_command}\n```"

    return f"""## AI CI Log Analysis

**Loại lỗi:** {analysis.category}  
**Step/job thất bại:** {analysis.failed_step}  
**Độ chính xác (Confidence):** {conf_icon} {int(analysis.confidence * 100)}%

### Nguyên nhân gốc rễ (Root Cause)
{analysis.root_cause}

### Gợi ý sửa lỗi (Suggested Fix)
{analysis.suggested_fix}{fix_cmd}

### Cách phòng ngừa (Prevention)
{analysis.prevention}
"""


def _format_deploy_guard(result: DeployGuardResult) -> str:
    checks = result.metadata.get("checks", [])
    
    return f"""## AI Deploy Guard

**Decision:** {result.decision}  
**Status code:** {result.status_code if result.status_code else 'N/A'}  
**Latency:** {result.latency_ms if result.latency_ms is not None else 'N/A'} ms  
**Health status:** {result.status or 'UNKNOWN'}

**Tóm tắt**: {result.summary}
{render_errors(result.errors)}

### Checks executed
{render_list(checks)}

### Message
{result.message if result.message else 'Không có.'}
"""


def format_markdown(result: BaseResult) -> str:
    """Format kết quả thành Markdown phụ thuộc vào tool"""
    if isinstance(result, PRReviewResult):
        return _format_pr_review(result)
    elif isinstance(result, SecurityScanResult):
        return _format_security_scan(result)
    elif isinstance(result, LogAnalysisResult):
        return _format_log_analysis(result)
    elif isinstance(result, DeployGuardResult):
        return _format_deploy_guard(result)
    else:
        return f"## {result.tool}\n\n**Decision**: {result.decision}\n\n**Summary**: {result.summary}"
