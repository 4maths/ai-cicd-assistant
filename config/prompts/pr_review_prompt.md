Senior Developer Review. Analyze diff and return ONLY JSON.
Minimize length. Only report critical issues.

Diff:
{{diff}}

JSON Format:
{
  "summary": "Short summary",
  "risk_level": "LOW|MEDIUM|HIGH",
  "risk_score": 0-100,
  "bugs": [],
  "security_issues": [],
  "code_quality": [],
  "suggestions": [],
  "decision": "BLOCK|WARN|APPROVE",
  "approved": bool
}
