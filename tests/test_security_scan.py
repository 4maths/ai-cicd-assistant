import os
import tempfile
import pytest
from aicicd.core.security_scan import run_security_scan, load_rules
from aicicd.domain.enums import Decision, Severity

def test_load_rules_default():
    rules = load_rules("non_existent.yml")
    assert len(rules) > 0
    assert rules[0]["id"] == "hardcoded_secret"

def test_run_security_scan_clean():
    diff_text = '''diff --git a/app.py b/app.py
--- a/app.py
+++ b/app.py
@@ -1 +1 @@
-print('hello')
+print('world')'''
    
    with tempfile.NamedTemporaryFile('w', delete=False) as f_rules:
        f_rules.write("rules: []")
        rules_path = f_rules.name
        
    with tempfile.NamedTemporaryFile('w', delete=False) as f_paths:
        f_paths.write("include_paths: []")
        paths_path = f_paths.name
        
    try:
        result = run_security_scan(diff_text, rules_path, paths_path)
        assert result.decision == Decision.APPROVE
        assert len(result.findings) == 0
    finally:
        os.unlink(rules_path)
        os.unlink(paths_path)

def test_run_security_scan_violations():
    diff_text = '''diff --git a/secret.py b/secret.py
--- a/secret.py
+++ b/secret.py
@@ -1 +1 @@
-pass
+api_key = "123456"
'''
    result = run_security_scan(diff_text, "rules.yml", "paths.yml")
    assert result.decision == Decision.BLOCK
    assert result.high_count > 0
    assert len(result.findings) >= 1
    assert result.findings[0].severity == Severity.HIGH
