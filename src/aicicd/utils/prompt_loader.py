import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

def load_prompt(prompt_name: str, variables: Optional[Dict[str, Any]] = None, config_dir: str = "config/prompts") -> str:
    """
    Loads a prompt from a markdown file and replaces placeholders with variables.
    
    Args:
        prompt_name: Name of the prompt file (without .md extension)
        variables: Dictionary of variables to replace in the prompt (e.g. {{diff}})
        config_dir: Directory where prompt files are stored
        
    Returns:
        The processed prompt string.
    """
    prompt_path = Path(config_dir) / f"{prompt_name}.md"
    
    if not prompt_path.exists():
        logger.warning(f"Prompt file not found: {prompt_path}")
        return ""
        
    try:
        content = prompt_path.read_text(encoding="utf-8")
        
        if variables:
            for key, value in variables.items():
                placeholder = "{{" + key + "}}"
                content = content.replace(placeholder, str(value))
                
        return content
    except Exception as e:
        logger.error(f"Error loading prompt {prompt_name}: {e}")
        return ""
