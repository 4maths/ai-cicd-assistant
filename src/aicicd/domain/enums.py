from __future__ import annotations

from enum import Enum


class StrEnum(str, Enum):
    """Base enum that behaves like both str and Enum."""

    def __str__(self) -> str:
        return self.value


class ToolName(StrEnum):
    PR_REVIEW = "pr-review"
    SECURITY_SCAN = "security-scan"
    LOG_ANALYSIS = "log-analysis"
    DEPLOY_GUARD = "deploy-guard"


class Decision(StrEnum):
    APPROVE = "APPROVE"
    WARN = "WARN"
    BLOCK = "BLOCK"
    ERROR = "ERROR"


class Severity(StrEnum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RiskLevel(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class FindingType(StrEnum):
    BUG = "BUG"
    SECURITY = "SECURITY"
    CODE_QUALITY = "CODE_QUALITY"
    PERFORMANCE = "PERFORMANCE"
    RELIABILITY = "RELIABILITY"
    TESTING = "TESTING"
    DEPLOYMENT = "DEPLOYMENT"
    CONFIGURATION = "CONFIGURATION"
    OBSERVABILITY = "OBSERVABILITY"
    GENERAL = "GENERAL"


class OutputFormat(StrEnum):
    JSON = "json"
    MARKDOWN = "markdown"
    TEXT = "text"


class ProviderName(StrEnum):
    GROQ = "groq"
    OPENAI = "openai"
    OLLAMA = "ollama"
    FPT = "fpt"
    MOCK = "mock"



class SCMPlatform(StrEnum):
    GITHUB = "github"
    GITLAB = "gitlab"
    LOCAL = "local"


class CIPlatform(StrEnum):
    GITHUB_ACTIONS = "github-actions"
    GITLAB_CI = "gitlab-ci"
    JENKINS = "jenkins"
    LOCAL = "local"


class PublisherType(StrEnum):
    GITHUB_PR_COMMENT = "github-pr-comment"
    GITLAB_MR_NOTE = "gitlab-mr-note"
    JENKINS_CONSOLE = "jenkins-console"
    STDOUT = "stdout"
    FILE = "file"


class LogCategory(StrEnum):
    TEST_FAILURE = "TEST_FAILURE"
    BUILD_FAILURE = "BUILD_FAILURE"
    DEPENDENCY_ERROR = "DEPENDENCY_ERROR"
    DOCKER_ERROR = "DOCKER_ERROR"
    KUBERNETES_ERROR = "KUBERNETES_ERROR"
    LINT_ERROR = "LINT_ERROR"
    TYPE_ERROR = "TYPE_ERROR"
    SYNTAX_ERROR = "SYNTAX_ERROR"
    RUNTIME_ERROR = "RUNTIME_ERROR"
    NETWORK_ERROR = "NETWORK_ERROR"
    AUTH_ERROR = "AUTH_ERROR"
    CONFIG_ERROR = "CONFIG_ERROR"
    UNKNOWN = "UNKNOWN"


class DeployStatus(StrEnum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"
    UNREACHABLE = "UNREACHABLE"
    ERROR = "ERROR"


class ExitCode(int, Enum):
    SUCCESS = 0
    WARNING = 1
    BLOCKED = 2
    EXECUTION_ERROR = 3
    VALIDATION_ERROR = 4