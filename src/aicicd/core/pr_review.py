import json
import logging
from typing import Any, Dict

from aicicd.domain.enums import ToolName, Decision, RiskLevel
from aicicd.domain.results import PRReviewResult
from aicicd.providers.llm.factory import get_provider

logger = logging.getLogger(__name__)


def build_review_prompt(diff: str) -> str:
    return f"""Bạn là một senior DevOps engineer và security-minded code reviewer với nhiều năm kinh nghiệm review code trong môi trường production.

Nhiệm vụ:
Hãy phân tích code diff dưới đây như một reviewer thực tế và khó tính.
Chỉ đưa ra nhận xét dựa trên bằng chứng xuất hiện trong diff.
Không tự đoán mò.
Trả về kết quả chính xác theo định dạng JSON.
Không được khen xã giao.
Không được nói chung chung.

Code diff:
{diff}

Mục tiêu review:
1. Tìm bug hoặc logic error có khả năng gây sai chức năng
2. Tìm edge case chưa được xử lý
3. Tìm rủi ro bảo mật hoặc lỗ hổng liên quan đến secret, token, input validation, exception handling
4. Đánh giá chất lượng code: naming, readability, duplication, maintainability, structure
5. Tìm thay đổi có thể gây vỡ backward compatibility, gây tác dụng phụ hoặc làm sai hành vi mong đợi
6. Đưa ra đề xuất sửa cụ thể, ưu tiên đề xuất có thể áp dụng ngay

Các nguyên tắc bắt buộc:
- Chỉ đánh giá dựa trên diff được cung cấp
- Nếu không đủ bằng chứng, hãy giữ mức độ cẩn trọng
- Nếu thay đổi có dấu hiệu sai logic, hãy đưa vào trường "bugs"
- Nếu thay đổi có nguy cơ nhưng chưa chắc chắn, đưa vào "code_quality" hoặc "suggestions"
- Mỗi mục trong list phải là câu ngắn, rõ ràng, cụ thể
- Trường "approved" chỉ được đặt là true khi không có bug logic rõ ràng, không có security issue nghiêm trọng

Tiêu chí đánh giá mức độ rủi ro:
- LOW: ít khả năng gây lỗi, không có dấu hiệu bug/security issue
- MEDIUM: có một vài điểm đáng nghi, có thể gây lỗi
- HIGH: có dấu hiệu rõ ràng của bug logic, security risk

Trả về JSON theo schema sau:
{{
  "summary": "Tóm tắt ngắn gọn",
  "risk_level": "LOW | MEDIUM | HIGH",
  "risk_score": 0,
  "bugs": ["bug 1", "bug 2"],
  "security_issues": ["risk 1"],
  "code_quality": ["nhận xét 1"],
  "suggestions": ["gợi ý 1"],
  "decision": "BLOCK | WARN | APPROVE",
  "approved": true
}}

Chỉ trả về JSON, không Markdown, không giải thích thêm.
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
        raw_response = llm.complete(prompt, max_tokens=1000)
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
