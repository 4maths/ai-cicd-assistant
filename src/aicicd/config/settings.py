import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class Settings:
    """Centralized application settings."""
    # Base paths
    WORKSPACE_DIR: Path = Path(os.getcwd())
    
    # Package internal config path
    PACKAGE_ROOT: Path = Path(__file__).parent.parent.parent.parent
    INTERNAL_CONFIG_DIR: Path = PACKAGE_ROOT / "config"
    
    # Priority: Workspace config > Package config
    @property
    def CONFIG_DIR(self) -> Path:
        ws_config = self.WORKSPACE_DIR / "config"
        return ws_config if ws_config.exists() else self.INTERNAL_CONFIG_DIR
    
    @property
    def PROMPTS_DIR(self) -> Path:
        return self.CONFIG_DIR / "prompts"
    
    # LLM Defaults
    DEFAULT_LLM_PROVIDER: str = os.environ.get("AICICD_PROVIDER", "groq")
    DEFAULT_MAX_TOKENS: int = 1000
    
    # Security Config (calculated based on CONFIG_DIR)
    @property
    def SECURITY_RULES_PATH(self) -> str:
        path = self.CONFIG_DIR / "security_rules.yml"
        return str(path)
        
    @property
    def SECURITY_PATHS_PATH(self) -> str:
        path = self.CONFIG_DIR / "security_paths.yml"
        return str(path)
    
    # API Tokens
    GITHUB_TOKEN: Optional[str] = os.environ.get("GITHUB_TOKEN")
    GITLAB_TOKEN: Optional[str] = os.environ.get("GITLAB_TOKEN")
    GITLAB_URL: str = os.environ.get("GITLAB_URL", "https://gitlab.com")
    
    # Operational Limits
    MAX_DIFF_CHARS: int = 32000
    CHUNK_SIZE: int = 1500

settings = Settings()
