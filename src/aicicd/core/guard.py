import time
import requests
from typing import Optional
from aicicd.core.base import BaseService
from aicicd.domain.enums import ToolName, Decision, DeployStatus
from aicicd.domain.results import DeployGuardResult
from aicicd.utils.prompt_loader import load_prompt
from aicicd.utils.json_tools import parse_json_safely

class DeployGuardService(BaseService):
    """Post-deployment Health Checker using LLM analysis of HTTP responses."""
    
    def check(self, url: str, timeout: int = 10) -> DeployGuardResult:
        result = DeployGuardResult(tool=ToolName.DEPLOY_GUARD)
        
        if not url:
            result.errors.append("URL target is missing.")
            return result

        # 1. Probe the endpoint
        try:
            start_time = time.perf_counter()
            response = requests.get(url, timeout=timeout)
            latency = (time.perf_counter() - start_time) * 1000
            
            result.status_code = response.status_code
            result.latency_ms = latency
            body = response.text[:2000] # Token limit safety
            headers = str(response.headers)
        except Exception as e:
            self.logger.error(f"Endpoint unreachable: {e}")
            result.status = DeployStatus.UNREACHABLE
            result.decision = Decision.BLOCK
            result.summary = f"Cannot reach {url}"
            return result

        # 2. AI Analysis of the response
        prompt = load_prompt("deploy_guard_prompt", {
            "url": url,
            "status_code": result.status_code,
            "headers": headers,
            "body": body
        })
        
        if prompt:
            try:
                raw_ai = self.llm.complete(prompt)
                data = parse_json_safely(raw_ai)
                if data:
                    self._update_result_from_ai(result, data)
                else:
                    self._fallback_check(result)
            except Exception as e:
                self.logger.error(f"AI Check failed: {e}")
                self._fallback_check(result)
        else:
            self._fallback_check(result)

        return result

    def _update_result_from_ai(self, result: DeployGuardResult, data: dict):
        result.summary = data.get("summary", "Health check completed.")
        result.message = data.get("message", "")
        result.metadata["checks"] = data.get("checks", [])
        result.metadata["suggestion"] = data.get("suggestion", "")
        
        try:
            result.status = DeployStatus(str(data.get("status", "UNHEALTHY")).upper())
            result.decision = Decision(str(data.get("decision", "BLOCK")).upper())
        except ValueError:
            result.status = DeployStatus.UNHEALTHY
            result.decision = Decision.BLOCK

    def _fallback_check(self, result: DeployGuardResult):
        """Basic status code based check if AI fails."""
        if result.status_code == 200:
            result.status = DeployStatus.HEALTHY
            result.decision = Decision.APPROVE
        else:
            result.status = DeployStatus.UNHEALTHY
            result.decision = Decision.BLOCK
