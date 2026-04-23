from typing import Optional
from aicicd.core.base import BaseService
from aicicd.domain.enums import ToolName, Decision, LogCategory
from aicicd.domain.models import LogAnalysis
from aicicd.domain.results import LogAnalysisResult
from aicicd.utils.prompt_loader import load_prompt
from aicicd.utils.json_tools import parse_json_safely

class LogAnalysisService(BaseService):
    """Failure Log Analyzer using LLM to identify root causes."""
    
    def analyze(self, log_content: str) -> LogAnalysisResult:
        result = LogAnalysisResult(tool=ToolName.LOG_ANALYSIS)
        
        if not log_content.strip():
            result.errors.append("Log content is empty.")
            return result

        categories = " | ".join([e.value for e in LogCategory])
        prompt = load_prompt("log_analysis_prompt", {
            "log_content": log_content,
            "categories_str": categories
        })
        
        if not prompt:
            result.errors.append("Failed to load log analysis prompt template.")
            return result

        try:
            raw_response = self.llm.complete(prompt)
            data = parse_json_safely(raw_response)
            if data:
                result.analysis = self._map_to_model(data)
                result.summary = result.analysis.summary
                result.decision = Decision.WARN
            else:
                result.errors.append("LLM returned invalid JSON.")
        except Exception as e:
            self.logger.error(f"Log analysis failed: {e}")
            result.errors.append(str(e))

        return result

    def _map_to_model(self, data: dict) -> LogAnalysis:
        try:
            category = LogCategory(str(data.get("category", "")).upper())
        except ValueError:
            category = LogCategory.UNKNOWN
            
        return LogAnalysis(
            category=category,
            summary=str(data.get("summary", "N/A")),
            root_cause=str(data.get("root_cause", "")),
            failed_step=str(data.get("failed_step", "")),
            suggested_fix=str(data.get("suggested_fix", "")),
            fix_command=str(data.get("fix_command", "")),
            prevention=str(data.get("prevention", "")),
            confidence=float(data.get("confidence", 0.0))
        )
