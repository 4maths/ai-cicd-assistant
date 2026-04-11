import pytest
from unittest.mock import patch, MagicMock
from aicicd.core.deploy_guard import run_deploy_guard
from aicicd.domain.enums import Decision, DeployStatus
import requests

@patch('requests.get')
def test_deploy_guard_healthy(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = "OK, service is up"
    mock_get.return_value = mock_resp

    result = run_deploy_guard("http://example.com", expect_text="OK")
    assert result.decision == Decision.APPROVE
    assert result.status == DeployStatus.HEALTHY
    assert result.expected_text_found is True

@patch('requests.get')
def test_deploy_guard_missing_text(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = "Some other text"
    mock_get.return_value = mock_resp

    result = run_deploy_guard("http://example.com", expect_text="Expected")
    assert result.decision == Decision.WARN
    assert result.status == DeployStatus.DEGRADED
    assert result.expected_text_found is False

@patch('requests.get')
def test_deploy_guard_timeout(mock_get):
    mock_get.side_effect = requests.exceptions.Timeout("Timeout")

    result = run_deploy_guard("http://timeout.com")
    assert result.decision == Decision.BLOCK
    assert result.status == DeployStatus.UNREACHABLE
