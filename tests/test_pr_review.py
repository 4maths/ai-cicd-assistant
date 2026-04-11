import pytest
from unittest.mock import patch, MagicMock
from aicicd.core.pr_review import run_pr_review
from aicicd.domain.enums import Decision, RiskLevel

@patch('aicicd.core.pr_review.get_provider')
def test_run_pr_review_approve(mock_get_provider):
    mock_llm = MagicMock()
    mock_llm.complete.return_value = '''
    {
      "summary": "LGTM",
      "risk_level": "LOW",
      "risk_score": 10,
      "bugs": [],
      "security_issues": [],
      "code_quality": ["Good naming"],
      "suggestions": [],
      "decision": "APPROVE",
      "approved": true
    }
    '''
    mock_get_provider.return_value = mock_llm

    result = run_pr_review("diff text")
    assert result.decision == Decision.APPROVE
    assert result.approved is True
    assert result.risk_level == RiskLevel.LOW

@patch('aicicd.core.pr_review.get_provider')
def test_run_pr_review_block(mock_get_provider):
    mock_llm = MagicMock()
    mock_llm.complete.return_value = '''
    {
      "summary": "Bad code",
      "risk_level": "HIGH",
      "risk_score": 90,
      "bugs": ["Null pointer"],
      "security_issues": ["SQL Injection"],
      "code_quality": [],
      "suggestions": [],
      "decision": "BLOCK",
      "approved": false
    }
    '''
    mock_get_provider.return_value = mock_llm

    result = run_pr_review("bad diff")
    assert result.decision == Decision.BLOCK
    assert result.approved is False
    assert result.risk_level == RiskLevel.HIGH
