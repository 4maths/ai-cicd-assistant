import pytest
from unittest.mock import patch, MagicMock
from aicicd.core.log_analysis import run_log_analysis
from aicicd.domain.enums import Decision, LogCategory

@patch('aicicd.core.log_analysis.get_provider')
def test_run_log_analysis_success(mock_get_provider):
    mock_llm = MagicMock()
    mock_llm.complete.return_value = '''
    {
      "category": "TEST_FAILURE",
      "summary": "1 test failed",
      "failed_step": "test_script.py",
      "root_cause": "AssertionError",
      "suggested_fix": "Fix assertion",
      "fix_command": "",
      "prevention": "Add more edge case tests",
      "confidence": 0.95
    }
    '''
    mock_get_provider.return_value = mock_llm

    result = run_log_analysis("Exception: 1 test failed")
    assert result.decision == Decision.WARN
    assert result.analysis.category == LogCategory.TEST_FAILURE
    assert result.analysis.confidence == 0.95

@patch('aicicd.core.log_analysis.get_provider')
def test_run_log_analysis_invalid_json(mock_get_provider):
    mock_llm = MagicMock()
    mock_llm.complete.return_value = "Not a JSON"
    mock_get_provider.return_value = mock_llm

    result = run_log_analysis("Fail")
    assert result.decision == Decision.ERROR
    assert len(result.errors) > 0
    assert "Invalid or empty JSON" in result.errors[0]
