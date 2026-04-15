import logging
import time
import requests
from pathlib import Path
from typing import Any, Dict, Optional

from aicicd.domain.enums import ToolName, Decision, DeployStatus
from aicicd.domain.results import DeployGuardResult
from aicicd.providers.llm.factory import get_provider

logger = logging.getLogger(__name__)


def parse_json_safely(raw: str) -> Dict[str, Any]:
    raw = raw.strip()
    if "```json" in raw:
        raw = raw.split("```json")[-1].split("```")[0]
    elif "```" in raw:
        raw = raw.split("```")[-1].split("```")[0]
    try:
        import json
        return json.loads(raw.strip())
    except Exception:
        return {}


def build_deploy_prompt(url: str, status_code: int, headers: str, body: str, prompt_template_path: Optional[str] = None) -> str:
    template = ""
    if prompt_template_path:
        path = Path(prompt_template_path)
        if path.exists():
            template = path.read_text(encoding="utf-8")
            
    if not template:
        template = """Phân tích kết quả deploy:
URL: {{url}}
Status: {{status_code}}
Headers: {{headers}}
Body: {{body}}

Trả về JSON: {"summary": "..", "status": "HEALTHY|DEGRADED|UNHEALTHY", "decision": "APPROVE|WARN|BLOCK", "message": "..", "checks": []}
"""
    return template.replace("{{url}}", url)\
                   .replace("{{status_code}}", str(status_code))\
                   .replace("{{headers}}", headers)\
                   .replace("{{body}}", body)


def run_deploy_guard(url: str, provider: str = "groq", prompt_path: Optional[str] = None, timeout: int = 10) -> DeployGuardResult:
    result = DeployGuardResult(
        tool=ToolName.DEPLOY_GUARD,
        decision=Decision.ERROR,
        summary="Kiểm tra trạng thái triển khai (AI-based)",
    )
    
    if not url:
        result.errors.append("Deploy URL is missing")
        return result

    logger.info("Bắt đầu gọi HTTP check cho: %s", url)
    
    # 1. Thực hiện gọi HTTP lấy dữ liệu
    try:
        start = time.perf_counter()
        response = requests.get(url, timeout=timeout)
        elapsed_ms = (time.perf_counter() - start) * 1000
        
        status_code = response.status_code
        headers_str = str(response.headers)
        body_text = response.text[:2000] # Giới hạn 2000 ký tự đầu để tránh tràn token
        
        result.status_code = status_code
        result.latency_ms = elapsed_ms
    except Exception as exc:
        result.status = DeployStatus.UNREACHABLE
        result.decision = Decision.BLOCK
        result.summary = f"Không thể kết nối tới URL: {url}"
        result.message = str(exc)
        return result

    # 2. Gọi AI để phân tích Response
    try:
        llm = get_provider(provider)
        prompt = build_deploy_prompt(url, status_code, headers_str, body_text, prompt_path)
        raw_response = llm.complete(prompt, max_tokens=1000)
        data = parse_json_safely(raw_response)
    except Exception as e:
        logger.error(f"Lỗi gọi AI trong Deploy Guard: {e}")
        result.errors.append(f"AI Provider Error: {str(e)}")
        # Dự phòng nếu AI lỗi thì dùng logic status code cơ bản
        if status_code == 200:
            result.status = DeployStatus.HEALTHY
            result.decision = Decision.APPROVE
        else:
            result.status = DeployStatus.UNHEALTHY
            result.decision = Decision.BLOCK
        return result

    if not data:
        result.errors.append("Không parse được kết quả JSON từ AI.")
        result.decision = Decision.ERROR
        result.summary = "LỖI: AI không trả về dữ liệu phân tích hợp lệ (kết quả JSON trống)."
        return result

    # 3. Cập nhật kết quả dựa trên AI
    result.summary = data.get("summary", "Đã phân tích phản hồi từ server.")
    result.message = data.get("message", "")
    result.metadata["checks"] = data.get("checks", [])
    result.metadata["suggestion"] = data.get("suggestion", "")
    
    status_str = str(data.get("status", "UNHEALTHY")).upper()
    try:
        result.status = DeployStatus(status_str)
    except ValueError:
        result.status = DeployStatus.UNHEALTHY

    decision_str = str(data.get("decision", "BLOCK")).upper()
    try:
        result.decision = Decision(decision_str)
    except ValueError:
        result.decision = Decision.BLOCK

    return result
