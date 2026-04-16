Analyze Code Diff for security vulnerabilities (OWASP Top 10).
Return ONLY JSON:
{
  "summary": "...",
  "findings": [
    {
      "id": "Short ID (e.g. A03)",
      "title": "Short title",
      "description": "Short description",
      "severity": "HIGH | MEDIUM | LOW",
      "file": "filename",
      "suggestion": "How to fix"
    }
  ],
  "decision": "BLOCK | WARN | APPROVE"
}

Diff to analyze:
{{diff}}
