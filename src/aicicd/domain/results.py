from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional

from .enums import Decision, ExitCode, ToolName, Severity, RiskLevel
from .models import Finding, LogAnalysis


# =========================
# Base Result
# =========================
@dataclass
class BaseResult:
    tool: ToolName
    decision: Decision
    summary: str

    findings: List[Finding] = field(default_factory=list)

    metadata: dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)

    def get_exit_code(self) -> ExitCode:
        if self.decision == Decision.APPROVE:
            return ExitCode.SUCCESS
        elif self.decision == Decision.WARN:
            return ExitCode.WARNING
        elif self.decision == Decision.BLOCK:
            return ExitCode.BLOCKED
        else:
            return ExitCode.EXECUTION_ERROR


# =========================
# PR Review Result
# =========================
@dataclass
class PRReviewResult(BaseResult):
    risk_level: RiskLevel = RiskLevel.MEDIUM
    risk_score: int = 0

    bugs: List[str] = field(default_factory=list)
    security_issues: List[str] = field(default_factory=list)
    code_quality: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)

    approved: bool = False


# =========================
# Security Scan Result
# =========================
@dataclass
class SecurityScanResult(BaseResult):
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0

    has_blocking_issues: bool = False
    is_bypassed: bool = False
    bypass_label: Optional[str] = None

    def get_exit_code(self) -> ExitCode:
        if self.is_bypassed:
            # Nếu được Bypass, coi như thành công (thoát mã 0) để Pipeline xanh
            return ExitCode.SUCCESS
        return super().get_exit_code()


# =========================
# Log Analysis Result
# =========================
@dataclass
class LogAnalysisResult(BaseResult):
    analysis: Optional[LogAnalysis] = None

    root_cause: Optional[str] = None
    suggested_fix: Optional[str] = None
    fix_command: Optional[str] = None
    prevention: Optional[str] = None

    confidence: float = 0.0


# =========================
# Deploy Guard Result
# =========================
@dataclass
class DeployGuardResult(BaseResult):
    status_code: Optional[int] = None
    latency_ms: Optional[float] = None

    expected_text_found: bool = False

    status: Optional[str] = None  # HEALTHY / DEGRADED / UNHEALTHY

    message: Optional[str] = None


# =========================
# Helper Functions
# =========================
def compute_decision_from_severity(findings: List[Finding]) -> Decision:
    """Utility to determine decision based on severity."""
    has_critical = any(f.severity == Severity.CRITICAL for f in findings)
    has_high = any(f.severity == Severity.HIGH for f in findings)
    has_medium = any(f.severity == Severity.MEDIUM for f in findings)

    if has_critical or has_high:
        return Decision.BLOCK
    elif has_medium:
        return Decision.WARN
    return Decision.APPROVE