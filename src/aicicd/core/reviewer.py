from typing import Dict, Any, List
from aicicd.core.base import BaseService
from aicicd.domain.enums import ToolName, Decision
from aicicd.domain.results import PRReviewResult
from aicicd.utils.prompt_loader import load_prompt
from aicicd.utils.json_tools import parse_json_safely
from aicicd.utils.chunking import chunk_diff
from aicicd.utils.diff_utils import load_path_config, filter_diff_by_paths
from aicicd.config.settings import settings

class ReviewService(BaseService):
    """Automated PR Reviewer using LLM."""
    
    def review(self, diff_text: str, paths_config: str = settings.SECURITY_PATHS_PATH) -> PRReviewResult:
        result = PRReviewResult(tool=ToolName.PR_REVIEW)
        
        if not diff_text.strip():
            result.summary = "Bản diff rỗng."
            return result

        # Load filtering config
        path_config = load_path_config(paths_config)
        filtered_diff = filter_diff_by_paths(diff_text, path_config)
        
        if not filtered_diff.strip():
            result.summary = "Không có file thuộc danh mục review."
            return result

        chunks = chunk_diff(filtered_diff, chunk_size=settings.CHUNK_SIZE)
        
        summaries = []
        for i, chunk in enumerate(chunks):
            self.logger.info(f"Reviewing chunk {i+1}/{len(chunks)}")
            prompt = load_prompt("pr_review_prompt", {"diff": chunk})
            
            try:
                raw_response = self.llm.complete(prompt)
                data = parse_json_safely(raw_response)
                if data:
                    analysis = self._normalize_analysis(data)
                    summaries.append(f"[Phần {i+1}] {analysis['summary']}")
                    result.bugs.extend(analysis['bugs'])
                    result.security_issues.extend(analysis['security_issues'])
                    result.code_quality.extend(analysis['code_quality'])
                    # If any chunk is BLOCK/WARN, aggregate to WARN
                    if analysis['decision'] in ("BLOCK", "WARN"):
                        result.decision = Decision.WARN
            except Exception as e:
                self.logger.error(f"Review Error on chunk {i+1}: {e}")

        result.summary = "\n".join(summaries)
        result.approved = (result.decision == Decision.APPROVE)
        return result

    def _normalize_analysis(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Ensures the AI output matches expected internal formats."""
        return {
            "summary": data.get("summary", ""),
            "bugs": data.get("bugs", []),
            "security_issues": data.get("security_issues", []),
            "code_quality": data.get("code_quality", []),
            "decision": str(data.get("decision", "WARN")).upper()
        }
