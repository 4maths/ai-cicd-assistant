import json
import logging
from typing import Any, Dict, Optional
from aicicd.domain.enums import ToolName, Decision, RiskLevel
from aicicd.domain.results import PRReviewResult
from aicicd.providers.llm.factory import get_provider
from aicicd.utils.diff_utils import load_path_config, filter_diff_by_paths, truncate_text
from aicicd.utils.json_tools import parse_json_safely

logger = logging.getLogger(__name__)


def build_review_prompt(diff: str) -> str:
    return f"""Senior Developer Review. Analyze diff and return ONLY JSON.
Minimize length. Only report critical issues.

Diff:
{diff}

JSON Format:
{{
  "summary": "Short summary",
  "risk_level": "LOW|MEDIUM|HIGH",
  "risk_score": 0-100,
  "bugs": [],
  "security_issues": [],
  "code_quality": [],
  "suggestions": [],
  "decision": "BLOCK|WARN|APPROVE",
  "approved": bool
}}
"""


# Removed local parse_json_safely - now using shared version from json_tools


def normalize_analysis(data: Dict[str, Any]) -> Dict[str, Any]:
    normalized = {
        "summary": str(data.get("summary", "Không có tóm tắt.")),
        "risk_level": str(data.get("risk_level", "MEDIUM")).upper(),
        "risk_score": data.get("risk_score", 0),
        "bugs": data.get("bugs", []),
        "security_issues": data.get("security_issues", []),
        "code_quality": data.get("code_quality", []),
        "suggestions": data.get("suggestions", []),
        "decision": str(data.get("decision", "WARN")).upper(),
        "approved": data.get("approved", False),
    }

    try:
        normalized["risk_score"] = int(normalized["risk_score"])
    except (TypeError, ValueError):
        normalized["risk_score"] = 0

    if normalized["risk_level"] not in {"LOW", "MEDIUM", "HIGH"}:
        normalized["risk_level"] = "MEDIUM"

    if normalized["decision"] not in {"BLOCK", "WARN", "APPROVE"}:
        normalized["decision"] = "WARN"

    for field in ["bugs", "security_issues", "code_quality", "suggestions"]:
        value = normalized[field]
        if isinstance(value, list):
            normalized[field] = [str(item).strip() for item in value if str(item).strip()]
        elif value:
            normalized[field] = [str(value).strip()]
        else:
            normalized[field] = []

    if isinstance(normalized["approved"], str):
        normalized["approved"] = normalized["approved"].strip().lower() == "true"
    else:
        normalized["approved"] = bool(normalized["approved"])

    if normalized["decision"] == "BLOCK":
        normalized["approved"] = False

    if normalized["decision"] == "APPROVE" and normalized["risk_level"] == "HIGH":
        normalized["decision"] = "WARN"

    return normalized


def run_pr_review(diff_text: str, provider: str = "groq", paths_config_path: str = "config/security_paths.yml") -> PRReviewResult:
    result = PRReviewResult(
        tool=ToolName.PR_REVIEW,
        decision=Decision.APPROVE,
        summary="Phân tích Pull Request (AI-based)",
    )

    if not diff_text or not diff_text.strip():
        result.summary = "Bản diff rỗng, bỏ qua phân tích."
        return result

    # 1. Filter Diff - Crucial for stability and token limits
    path_config = load_path_config(paths_config_path)
    filtered_diff = filter_diff_by_paths(diff_text, path_config)
    
    if not filtered_diff.strip():
        result.summary = "Không có file nào cần review sau khi lọc (chỉ lọc bỏ các file rác/tự sinh)."
        return result

    try:
        llm = get_provider(provider)
        # Use strict truncation and low max_tokens to stay within 6k TPM
        safe_diff = truncate_text(filtered_diff, max_chars=5000)
        prompt = build_review_prompt(safe_diff)
        raw_response = llm.complete(prompt, max_tokens=500)
    except Exception as e:
        logger.error(f"Lỗi gọi AI trong PR Review: {e}")
        result.errors.append(f"AI Provider Error: {str(e)}")
        result.decision = Decision.ERROR
        result.summary = f"Lỗi kỹ thuật khi gọi AI: {str(e)}"
        return result

    data = parse_json_safely(raw_response)
    if not data:
        # Debug: Đưa nội dung thô vào summary nếu parse lỗi để user thấy được AI đang nói gì
        truncated_raw = (raw_response[:500] + "...") if len(raw_response) > 500 else raw_response
        result.errors.append(f"Invalid JSON. Raw head: {truncated_raw}")
        result.summary = f"LỖI PHÂN TÍCH JSON. AI ĐÃ TRẢ VỀ: {truncated_raw}"
        return result

    analysis = normalize_analysis(data)

    # Ensure decision is valid and NEVER stays as ERROR if data is present
    decision_val = analysis.get("decision", "WARN").upper()
    if decision_val not in Decision.__members__:
        decision_enum = Decision.WARN
    else:
        decision_enum = Decision[decision_val]
        
    if decision_enum == Decision.ERROR:
        decision_enum = Decision.WARN

    result.summary = analysis["summary"]
    try:
        result.risk_level = RiskLevel(analysis["risk_level"])
    except ValueError:
        result.risk_level = RiskLevel.MEDIUM
        
    result.risk_score = analysis["risk_score"]
    result.bugs = analysis["bugs"]
    result.security_issues = analysis["security_issues"]
    result.code_quality = analysis["code_quality"]
    result.suggestions = analysis["suggestions"]
    result.decision = decision_enum
    result.approved = analysis["approved"]

    result.metadata["provider"] = provider

    return result
