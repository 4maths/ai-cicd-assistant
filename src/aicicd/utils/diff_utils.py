import re
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_PATH_CONFIG = {
    "include_paths": [],
    "exclude_paths": ["tests/", "config/", ".github/", ".venv/", "docs/", "examples/", "node_modules/", "vendor/"],
    "exclude_extensions": [".md", ".txt", ".json", ".lock", ".csv", ".pdf", ".svg", ".png", ".jpg", ".jpeg"],
    "exclude_file_patterns": [r".*\.min\.js$", r".*\.map$"],
}

def load_path_config(config_path: Optional[str]) -> Dict[str, Any]:
    if not config_path:
        return DEFAULT_PATH_CONFIG
        
    path = Path(config_path)
    if not path.exists():
        return DEFAULT_PATH_CONFIG

    try:
        import yaml
        # Import moved inside to avoid hard dependency if YAML not needed, though it's in requirements.txt
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        return {
            "include_paths": data.get("include_paths", DEFAULT_PATH_CONFIG["include_paths"]),
            "exclude_paths": data.get("exclude_paths", DEFAULT_PATH_CONFIG["exclude_paths"]),
            "exclude_extensions": data.get("exclude_extensions", DEFAULT_PATH_CONFIG["exclude_extensions"]),
            "exclude_file_patterns": data.get("exclude_file_patterns", DEFAULT_PATH_CONFIG["exclude_file_patterns"]),
        }
    except Exception as exc:
        logger.error(f"Error loading path config at {config_path}: {exc}")
        return DEFAULT_PATH_CONFIG

def should_process_file(filename: str, path_config: Dict[str, Any]) -> bool:
    include_paths = path_config.get("include_paths", [])
    exclude_paths = path_config.get("exclude_paths", [])
    exclude_extensions = path_config.get("exclude_extensions", [])
    exclude_file_patterns = path_config.get("exclude_file_patterns", [])

    if include_paths:
        if not any(filename == item or filename.startswith(item) for item in include_paths):
            return False

    if any(filename.startswith(prefix) for prefix in exclude_paths):
        return False

    if any(filename.endswith(ext) for ext in exclude_extensions):
        return False

    if any(re.match(pat, filename) for pat in exclude_file_patterns):
        return False

    return True

def filter_diff_by_paths(diff_text: str, path_config: Dict[str, Any]) -> str:
    """Filters diff_text to keep only relevant files to save tokens."""
    if not diff_text:
        return ""
        
    filtered_lines = []
    include_current = True
    
    for line in diff_text.splitlines():
        if line.startswith("diff --git "):
            parts = line.split(" ")
            if len(parts) >= 4:
                path = parts[3]
                if path.startswith("b/"):
                    path = path[2:]
                include_current = should_process_file(path, path_config)
            else:
                include_current = True
                
        if include_current:
            filtered_lines.append(line)
            
    return "\n".join(filtered_lines)

def truncate_text(text: str, max_chars: int = 15000) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n... [Diff truncated for token limits] ..."
