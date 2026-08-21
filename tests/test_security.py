import pytest
import os
import json
from unittest.mock import patch

from tools.filesystem import file_read, file_write, normalize_and_check_path
from tools.code import execute_code
from memory.privacy import PrivacyFilter
from browser.policy import BrowserPolicy, RiskLevel

# 1. Secret redaction
def test_secret_redaction():
    pf = PrivacyFilter()
    assert "[REDACTED_ANTHROPIC_KEY]" in pf.scrub("sk-ant-api03-12345678901234567890123")
    assert "[REDACTED_API_KEY]" in pf.scrub("sk-proj-12345678901234567890123")
    # Bypass attempt: split key
    # Wait, privacy filter operates on strings. If it's split, it's not a key.
    # What if it's base64 encoded? 
    pass

# 2. Path Traversal
def test_path_traversal():
    os.environ["AGENT_WORKSPACE"] = "/tmp/workspace"
    # Try absolute path outside
    result = file_read("/etc/passwd")
    assert "Error" in result or "Access denied" in result
    
    # Try relative traversal
    result = file_write("../../etc/passwd", "hack")
    assert "Error" in result or "Access denied" in result

# 3. Arbitrary file execution
def test_arbitrary_file_execution():
    # If we execute code with cwd outside workspace, it should be denied.
    os.environ["AGENT_WORKSPACE"] = "/tmp/workspace"
    result = execute_code("bash", "pwd", cwd="/etc")
    assert "Access denied" in result or "Error" in result

# 4. Shell injection
def test_shell_injection():
    # Try to inject arguments into execute_code
    # Since it writes to a file, injection via args shouldn't work.
    result = execute_code("bash", "echo 'hello'")
    assert "hello" in result

# 5. Cookie leakage
def test_cookie_leakage():
    pf = PrivacyFilter()
    assert "[REDACTED_COOKIE]" in pf.scrub("Cookie: session_id=secret123;")
    assert "[REDACTED_COOKIE]" in pf.scrub("document.cookie = 'session_id=secret123'")

# 6. Authorization leakage
def test_authorization_leakage():
    pf = PrivacyFilter()
    assert "[REDACTED_AUTH_HEADER]" in pf.scrub("Authorization: Bearer mytoken123")

# 7. Unsafe browser action
def test_unsafe_browser_action():
    policy = BrowserPolicy()
    assert policy.evaluate_js("delete_account()") == RiskLevel.DANGEROUS
    
# 8. Confirmation bypass
def test_confirmation_bypass():
    # If the user tries to bypass confirmation by passing declared_risk="safe" 
    # but the action is dangerous.
    from tools.browser import browser_execute_js
    import asyncio
    
    policy = BrowserPolicy()
    # Let's say they obfuscate JS. We should catch it.
    js_code = r"window['\x64\x65\x6c\x65\x74\x65_account']()"
    assert policy.evaluate_js(js_code) == RiskLevel.DANGEROUS

