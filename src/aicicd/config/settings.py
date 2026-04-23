import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class Settings:
    """Centralized application settings."""
    # Base paths
    WORKSPACE_DIR: Path = Path(os.getcwd())
    CONFIG_DIR: Path = WORKSPACE_DIR / "config"
    PROMPTS_DIR: Path = CONFIG_DIR / "prompts"
    
    # LLM Defaults
    DEFAULT_LLM_PROVIDER: str = os.environ.get("AICICD_PROVIDER", "groq")
    DEFAULT_MAX_TOKENS: int = 1000
    
    # Security Config
    SECURITY_RULES_PATH: str = "config/security_rules.yml"
    SECURITY_PATHS_PATH: str = "config/security_paths.yml"
    
    # API Tokens
    GITHUB_TOKEN: Optional[str] = os.environ.get("GITHUB_TOKEN")
    GITLAB_TOKEN: Optional[str] = os.environ.get("GITLAB_TOKEN")
    GITLAB_URL: str = os.environ.get("GITLAB_URL", "https://gitlab.com")
    
    # Operational Limits
    MAX_DIFF_CHARS: int = 32000
    CHUNK_SIZE: int = 1500

settings = Settings()
