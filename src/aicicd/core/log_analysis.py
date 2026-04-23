import json
import logging
from typing import Any, Dict

from aicicd.domain.enums import ToolName, Decision, LogCategory
from aicicd.domain.models import LogAnalysis
from aicicd.domain.results import LogAnalysisResult
from aicicd.providers.llm.factory import get_provider

logger = logging.getLogger(__name__)


from aicicd.utils.prompt_loader import load_prompt
from aicicd.utils.json_tools import parse_json_safely

def build_log_prompt(log_content: str) -> str:
    categories = [e.value for e in LogCategory]
    categories_str = " | ".join(categories)
    
    prompt = load_prompt("log_analysis_prompt", {
        "log_content": log_content,
        "categories_str": categories_str
    })
    
    if prompt:
        return prompt
        
    # Fallback minimal template
    return f"""Analyze CI log fail. Log: {log_content}. Return JSON."""


# Use shared parse_json_safely from aicicd.utils.json_tools


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
