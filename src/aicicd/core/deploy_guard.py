import logging
import time
import requests
from aicicd.domain.enums import ToolName, Decision, DeployStatus
from aicicd.domain.results import DeployGuardResult

logger = logging.getLogger(__name__)


def run_deploy_guard(url: str, timeout: int = 5, max_latency_ms: int = 1000, expect_text: str = "") -> DeployGuardResult:
    result = DeployGuardResult(
        tool=ToolName.DEPLOY_GUARD,
        decision=Decision.ERROR,
        summary="Service post-deploy check",
    )
    
    if not url:
        result.errors.append("Deploy URL is missing")
        return result

    logger.info("Bắt đầu kiểm tra deploy cho URL: %s", url)
    checks = []

    try:
        start = time.perf_counter()
        response = requests.get(url, timeout=timeout)
        elapsed_ms = (time.perf_counter() - start) * 1000

        result.status_code = response.status_code
        result.latency_ms = elapsed_ms
        body_text = response.text.strip()
        
        if response.status_code == 200:
            checks.append("Health endpoint trả về HTTP 200.")
        else:
            checks.append(f"Health endpoint trả về HTTP {response.status_code}.")
            
        checks.append(f"Latency đo được: {int(elapsed_ms)} ms.")

        if expect_text:
            if expect_text.lower() in body_text.lower():
                checks.append(f'Body chứa chuỗi mong đợi: "{expect_text}".')
                result.expected_text_found = True
            else:
                checks.append(f'Body không chứa chuỗi mong đợi: "{expect_text}".')
                result.expected_text_found = False
        else:
            result.expected_text_found = True
            
        result.metadata["checks"] = checks

        if response.status_code != 200:
            result.status = DeployStatus.UNHEALTHY
            result.decision = Decision.BLOCK
            result.summary = f"Service không khỏe, trả về status {response.status_code}."
            result.message = "Health check HTTP failed."
        elif expect_text and not result.expected_text_found:
            result.status = DeployStatus.DEGRADED
            result.decision = Decision.WARN
            result.summary = "Trả về 200 nhưng nội dung response không như mong đợi."
            result.message = "Expected text missing."
        elif elapsed_ms > max_latency_ms:
            result.status = DeployStatus.DEGRADED
            result.decision = Decision.WARN
            result.summary = "Service hoạt động nhưng latency vượt hạn mức."
            result.message = f"Latency {int(elapsed_ms)}ms > {max_latency_ms}ms"
        else:
            result.status = DeployStatus.HEALTHY
            result.decision = Decision.APPROVE
            result.summary = "Service hoạt động ổn định và đáp ứng tất cả các chỉ tiêu."
            result.message = "All checks passed."

    except requests.exceptions.Timeout:
        result.status = DeployStatus.UNREACHABLE
        result.decision = Decision.BLOCK
        result.summary = "Request bị timeout khi gọi kiểm tra health check."
        result.message = "Timeout"
    except requests.exceptions.RequestException as exc:
        result.status = DeployStatus.ERROR
        result.decision = Decision.BLOCK
        result.summary = "Gặp lỗi network nội tại trong lúc gọi HTTP request."
        result.message = "Network error"
        result.errors.append(str(exc))

    return result
