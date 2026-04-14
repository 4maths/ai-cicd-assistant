import json
import logging
from typing import Any, Dict

from aicicd.domain.enums import ToolName, Decision, RiskLevel
from aicicd.domain.results import PRReviewResult
from aicicd.providers.llm.factory import get_provider

logger = logging.getLogger(__name__)


def build_review_prompt(diff: str) -> str:
    return f"""Bạn là Senior Code Reviewer. Hãy phân tích code diff sau và trả về kết quả dưới dạng JSON.
Chỉ nhận xét những lỗi thực sự (bug, security, code quality). 

Code diff:
{diff}

Yêu cầu định dạng JSON (không được có văn bản thừa bên ngoài):
{{
  "summary": "Tóm tắt ngắn gọn",
  "risk_level": "LOW | MEDIUM | HIGH",
  "risk_score": 0,
  "bugs": ["danh sách bug nếu có"],
  "security_issues": ["danh sách lỗi bảo mật nếu có"],
  "code_quality": ["nhận xét chất lượng code"],
  "suggestions": ["đề xuất sửa"],
  "decision": "BLOCK | WARN | APPROVE",
  "approved": true
}}
"""


def parse_json_safely(raw: str) -> Dict[str, Any]:
    import re
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
        logger.error(f"Cannot parse JSON from LLM: {str(e)}\nRaw output: {raw}")
        return {}


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


def run_pr_review(diff_text: str, provider: str = "groq") -> PRReviewResult:
    result = PRReviewResult(
        tool=ToolName.PR_REVIEW,
        decision=Decision.ERROR,
        summary="Phân tích Pull Request",
    )

    if not diff_text or not diff_text.strip():
        result.errors.append("Diff input is empty.")
        result.decision = Decision.APPROVE
        result.summary = "Diff rỗng, bỏ qua phân tích."
        return result

    try:
        llm = get_provider(provider)
    except Exception as e:
        result.errors.append(f"Provider error: {str(e)}")
        return result

    prompt = build_review_prompt(diff_text)

    try:
        raw_response = llm.complete(prompt, max_tokens=2000)
    except Exception as e:
        result.errors.append(f"LLM API error: {str(e)}")
        return result

    data = parse_json_safely(raw_response)
    if not data:
        result.errors.append("Invalid or empty JSON returned from LLM")
        return result

    analysis = normalize_analysis(data)

    try:
        risk_enum = RiskLevel(analysis["risk_level"])
    except ValueError:
        risk_enum = RiskLevel.MEDIUM

    try:
        decision_enum = Decision(analysis["decision"])
    except ValueError:
        decision_enum = Decision.WARN

    result.summary = analysis["summary"]
    result.risk_level = risk_enum
    result.risk_score = analysis["risk_score"]
    result.bugs = analysis["bugs"]
    result.security_issues = analysis["security_issues"]
    result.code_quality = analysis["code_quality"]
    result.suggestions = analysis["suggestions"]
    result.decision = decision_enum
    result.approved = analysis["approved"]

    result.metadata["provider"] = provider

    return result
