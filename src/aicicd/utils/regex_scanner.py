from __future__ import annotations

import re
import yaml
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from aicicd.domain.enums import Severity, FindingType
from aicicd.domain.models import Finding

logger = logging.getLogger(__name__)

class RegexScanner:
    """
    Primary security scanner using regex patterns defined in YAML.
    """

    def __init__(self, rules_path: str = "config/security_rules.yml"):
        self.rules_path = rules_path
        self.rules = self._load_rules()

    def _load_rules(self) -> List[Dict[str, Any]]:
        path = Path(self.rules_path)
        if not path.exists():
            logger.warning(f"Security rules file not found: {self.rules_path}")
            return []
        
        try:
            with path.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                return data.get("rules", [])
        except Exception as e:
            logger.error(f"Error loading security rules: {e}")
            return []

    def scan(self, text: str, filename: Optional[str] = None) -> List[Finding]:
        findings = []
        if not text:
            return findings

        for rule in self.rules:
            pattern = rule.get("pattern")
            if not pattern:
                continue

            try:
                matches = re.finditer(pattern, text)
                for match in matches:
                    findings.append(Finding(
                        type=FindingType.SECURITY,
                        severity=Severity(rule.get("severity", "MEDIUM").upper()),
                        title=rule.get("id", "Regex Match"),
                        description=rule.get("description", "Potential security issue detected via regex."),
                        file=filename,
                        metadata={
                            "match_text": match.group(0),
                            "regex_pattern": pattern
                        }
                    ))
            except Exception as e:
                logger.error(f"Error executing regex pattern {pattern}: {e}")

        return findings
