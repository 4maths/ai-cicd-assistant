import json
import logging
from typing import Any, Dict

from aicicd.domain.enums import ToolName, Decision, LogCategory
from aicicd.domain.models import LogAnalysis
from aicicd.domain.results import LogAnalysisResult
from aicicd.providers.llm.factory import get_provider

logger = logging.getLogger(__name__)


def build_log_prompt(log_content: str) -> str:
    categories = [e.value for e in LogCategory]
    categories_str = " | ".join(categories)
    return f"""Bạn là một DevOps engineer giàu kinh nghiệm trong việc debug CI/CD pipeline, build failure, test failure và workflow automation.

Nhiệm vụ:
Phân tích log CI thất bại dưới đây và xác định nguyên nhân gốc rễ một cách chính xác, ngắn gọn, có căn cứ.
Chỉ được dựa trên thông tin xuất hiện trong log.
Không suy đoán quá mức.
Không viết chung chung.
Không thêm lời mở đầu hay giải thích ngoài JSON.

Log CI:
{log_content}

Mục tiêu phân tích:
1. Xác định chính xác step hoặc job thất bại
2. Phân loại lỗi theo đúng bản chất
3. Tóm tắt lỗi ngắn gọn
4. Giải thích nguyên nhân gốc rễ rõ ràng, ngắn gọn, dễ hiểu
5. Đề xuất cách sửa lỗi cụ thể, có thể thực hiện ngay
6. Đề xuất cách phòng tránh lỗi này tái diễn trong tương lai

Nguyên tắc bắt buộc:
- Chỉ phân tích dựa trên log được cung cấp
- Nếu log không đủ thông tin, phải thể hiện sự thận trọng trong phần root_cause
- Không bịa thêm bối cảnh không có trong log
- "suggested_fix" phải mang tính hành động, không được quá chung chung
- "prevention" phải là biện pháp thực tế để tránh lỗi lặp lại
- "fix_command" chỉ nên điền khi có lệnh cụ thể hợp lý để áp dụng (ví dụ: npm install <package> hoặc pip install <package>)
- Nếu không có command phù hợp rõ ràng, trả về chuỗi rỗng cho "fix_command"

Yêu cầu chất lượng output:
- "failed_step": phải ghi rõ tên step hoặc job thất bại nếu suy ra được từ log
- "root_cause": 2-3 câu, nêu đúng nguyên nhân gốc rễ, không lan man
- "suggested_fix": nêu từng hành động cụ thể để sửa
- "confidence": giá trị float từ 0.0 đến 1.0. Chọn 0.9-1.0 khi log thể hiện nguyên nhân rất rõ ràng. Chọn 0.6-0.8 nếu có dấu hiệu mạnh nhưng chưa hoàn toàn chắc chắn. Chọn < 0.5 nếu log quá ít thông tin
- "prevention": đưa ra biện pháp phòng tránh thực tế như thêm validation, cải thiện test, khóa version dependency, tăng logging, hoặc retry/backoff

Trả về đúng định dạng JSON theo schema sau:
{{
  "category": "{categories_str}",
  "summary": "Tóm tắt loại lỗi ngắn gọn",
  "failed_step": "Tên step hoặc job thất bại cụ thể",
  "root_cause": "Mô tả ngắn gọn nguyên nhân gốc rễ, tối đa 2-3 câu",
  "suggested_fix": "Hướng dẫn sửa lỗi cụ thể, rõ ràng, có thể làm ngay",
  "fix_command": "Lệnh sửa lỗi cụ thể (nếu có, nếu không thì trả về chuỗi rỗng)",
  "prevention": "Cách ngăn lỗi này tái diễn trong tương lai",
  "confidence": 0.9
}}

Chỉ trả về JSON hợp lệ, không Markdown, không giải thích thêm.
"""


def parse_json_safely(raw: str) -> Dict[str, Any]:
    raw = raw.strip()
    if raw.startswith("```json"):
        raw = raw[7:]
    elif raw.startswith("```"):
        raw = raw[3:]
    
    if raw.endswith("```"):
        raw = raw[:-3]
        
    try:
        return json.loads(raw.strip())
    except json.JSONDecodeError as e:
        logger.error(f"Cannot parse JSON from LLM: {str(e)}\nRaw output: {raw}")
        return {}


def run_log_analysis(log_text: str, provider: str = "groq") -> LogAnalysisResult:
    result = LogAnalysisResult(
        tool=ToolName.LOG_ANALYSIS,
        decision=Decision.ERROR,
        summary="Phân tích log thất bại",
    )

    if not log_text or not log_text.strip():
        result.errors.append("Input log_text is empty")
        return result

    try:
        llm = get_provider(provider)
    except Exception as e:
        result.errors.append(f"Provider error: {str(e)}")
        return result

    prompt = build_log_prompt(log_text)
    
    try:
        raw_response = llm.complete(prompt, max_tokens=1000)
    except Exception as e:
        result.errors.append(f"LLM API error: {str(e)}")
        return result

    data = parse_json_safely(raw_response)
    if not data:
        result.errors.append("Invalid or empty JSON returned from LLM")
        return result

    # Map category safely
    category_str = str(data.get("category", "")).upper()
    try:
        category = LogCategory(category_str)
    except ValueError:
        category = LogCategory.UNKNOWN

    analysis_model = LogAnalysis(
        category=category,
        summary=str(data.get("summary", "Không có tóm tắt")),
        root_cause=str(data.get("root_cause", "Không rõ nguyên nhân")),
        failed_step=str(data.get("failed_step", "Không xác định")),
        suggested_fix=str(data.get("suggested_fix", "")),
        fix_command=str(data.get("fix_command", "")),
        prevention=str(data.get("prevention", "")),
        confidence=float(data.get("confidence", 0.0)),
    )

    result.analysis = analysis_model
    result.summary = analysis_model.summary
    result.root_cause = analysis_model.root_cause
    result.suggested_fix = analysis_model.suggested_fix
    result.fix_command = analysis_model.fix_command
    result.prevention = analysis_model.prevention
    result.confidence = analysis_model.confidence

    # Log analysis is observational. It points out what's wrong.
    result.decision = Decision.WARN
    result.metadata["provider"] = provider

    return result
