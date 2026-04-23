import json
import logging
from typing import Any, Dict, Optional
from aicicd.domain.enums import ToolName, Decision, RiskLevel
from aicicd.domain.results import PRReviewResult
from aicicd.providers.llm.factory import get_provider
from aicicd.utils.diff_utils import load_path_config, filter_diff_by_paths, truncate_text
from aicicd.utils.json_tools import parse_json_safely

logger = logging.getLogger(__name__)


from aicicd.utils.prompt_loader import load_prompt

def build_review_prompt(diff: str) -> str:
    prompt = load_prompt("pr_review_prompt", {"diff": diff})
    if prompt:
        return prompt
        
    # Fallback
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
            # Keep dictionary/object structure if it exists, don't force to string
            normalized[field] = [item for item in value if item]
        elif value:
            normalized[field] = [value]
        else:
            normalized[field] = []


    if isinstance(normalized["approved"], str):
        normalized["approved"] = normalized["approved"].strip().lower() == "true"
    else:
        normalized["approved"] = bool(normalized["approved"])

    if normalized["decision"] == "BLOCK":
        normalized["decision"] = "WARN" # Downgrade to WARN
        normalized["approved"] = False


    if normalized["decision"] == "APPROVE" and normalized["risk_level"] == "HIGH":
        normalized["decision"] = "WARN"

    return normalized


from aicicd.utils.chunking import chunk_diff

def run_pr_review(diff_text: str, provider: str = "groq", paths_config_path: str = "config/security_paths.yml") -> PRReviewResult:
    result = PRReviewResult(
        tool=ToolName.PR_REVIEW,
        decision=Decision.APPROVE,
        summary="Phân tích Pull Request (Groq Intelligence)",
    )

    if not diff_text or not diff_text.strip():
        result.summary = "Bản diff rỗng, bỏ qua phân tích."
        return result

    # 1. Filter Diff
    path_config = load_path_config(paths_config_path)
    filtered_diff = filter_diff_by_paths(diff_text, path_config)
    
    if not filtered_diff.strip():
        result.summary = "Không có file nguồn nào cần review sau khi lọc (src/, app/)."
        return result

    # 2. Split into chunks
    chunks = chunk_diff(filtered_diff, chunk_size=1500)
    
    summaries = []
    all_bugs = []
    all_sec = []
    all_quality = []
    all_suggestions = []
    
    llm = get_provider(provider)

    # 3. Process each chunk
    for i, chunk in enumerate(chunks):
        logger.info(f"Reviewing chunk {i+1}/{len(chunks)}")
        prompt = build_review_prompt(chunk)
        
        try:
            raw_response = llm.complete(prompt, max_tokens=1000)
            data = parse_json_safely(raw_response)
            
            if data:
                analysis = normalize_analysis(data)
                if analysis.get("summary"):
                    summaries.append(f"[Chunk {i+1}] {analysis['summary']}")
                all_bugs.extend(analysis.get("bugs", []))
                all_sec.extend(analysis.get("security_issues", []))
                all_quality.extend(analysis.get("code_quality", []))
                all_suggestions.extend(analysis.get("suggestions", []))
                
                # Decision aggregation: if any chunk is BLOCK (or WARN), downgrade overall
                if analysis.get("decision") == "BLOCK" or analysis.get("decision") == "WARN":
                    result.decision = Decision.WARN
        except Exception as e:
            logger.error(f"Review failed for chunk {i+1}: {e}")
            result.errors.append(f"Chunk {i+1} Review Error: {str(e)}")

    # 4. Final aggregation
    result.summary = "\n".join(summaries) if summaries else "Hoàn thành review các thành phần code."
    result.bugs = list(set(all_bugs)) # Unique bugs
    result.security_issues = list(set(all_sec))
    result.code_quality = list(set(all_quality))
    result.suggestions = list(set(all_suggestions))
    
    result.approved = result.decision == Decision.APPROVE
    result.metadata["provider"] = provider
    result.metadata["chunks_processed"] = len(chunks)

    return result

