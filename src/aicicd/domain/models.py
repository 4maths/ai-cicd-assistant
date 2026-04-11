from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from .enums import Severity, FindingType, LogCategory


# =========================
# Generic Finding
# =========================
@dataclass
class Finding:
    type: FindingType
    severity: Severity
    title: str
    description: str

    file: Optional[str] = None
    line: Optional[int] = None

    suggestion: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)


# =========================
# PR Review Specific
# =========================
@dataclass
class PRMetrics:
    files_changed: int = 0
    lines_added: int = 0
    lines_deleted: int = 0


@dataclass
class PRContext:
    diff: str
    metrics: PRMetrics = field(default_factory=PRMetrics)


# =========================
# Security Scan
# =========================
@dataclass
class SecurityRuleMatch:
    rule_id: str
    description: str
    severity: Severity
    file: Optional[str] = None
    line: Optional[int] = None
    match_text: Optional[str] = None


# =========================
# Log Analysis
# =========================
@dataclass
class LogContext:
    raw_log: str
    truncated: bool = False
    max_lines: int = 0


@dataclass
class LogAnalysis:
    category: LogCategory
    summary: str
    root_cause: str

    failed_step: Optional[str] = None
    error_message: Optional[str] = None

    suggested_fix: Optional[str] = None
    fix_command: Optional[str] = None
    prevention: Optional[str] = None

    confidence: float = 0.0


# =========================
# Deploy Guard
# =========================
@dataclass
class DeployCheckResult:
    status_code: Optional[int]
    latency_ms: Optional[float]

    response_body: Optional[str] = None

    is_healthy: bool = False
    error: Optional[str] = None