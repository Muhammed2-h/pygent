import json
import logging

from core.logger import JSONLFormatter, redact


def test_redact_sensitive_keys():
    data = {
        "api_key": "secret123",
        "APIKEY": "secret123",
        "password": "my_password",
        "normal_field": "safe_value",
        "nested": {
            "token": "nested_secret",
            "safe": "nested_safe"
        },
        "list": [
            {"cookie": "choc"},
            "plain_string"
        ]
    }
    
    redacted = redact(data)
    assert redacted["api_key"] == "***REDACTED***"
    assert redacted["APIKEY"] == "***REDACTED***"
    assert redacted["password"] == "***REDACTED***"
    assert redacted["normal_field"] == "safe_value"
    assert redacted["nested"]["token"] == "***REDACTED***"
    assert redacted["nested"]["safe"] == "nested_safe"
    assert redacted["list"][0]["cookie"] == "***REDACTED***"
    assert redacted["list"][1] == "plain_string"

def test_redact_regex():
    data = {
        "auth": "Bearer abcd-1234",
        "key": "sk-1234567890abcdef1234567890abcdef"
    }
    
    redacted = redact(data)
    # The key "auth" gets redacted by SENSITIVE_KEYS anyway,
    # but "key" doesn't strictly match SENSITIVE_KEYS unless "key" is in it (it isn't).
    assert "sk-" not in redacted["key"]
    assert redacted["key"] == "***REDACTED***"
    
    # Test just string
    assert redact("Bearer token-abc") == "***REDACTED***"
    assert redact("sk-1234567890abcdef1234567890abcdef") == "***REDACTED***"

def test_jsonl_formatter():
    formatter = JSONLFormatter()
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname="test.py", lineno=1,
        msg="Test message", args=(), exc_info=None
    )
    record.task_id = "task-123"
    record.turn = 2
    record.tool = "search"
    record.status = "success"
    record.duration = 1.5
    record.error = None
    
    formatted = formatter.format(record)
    data = json.loads(formatted)
    
    assert data["task_id"] == "task-123"
    assert data["turn"] == 2
    assert data["tool"] == "search"
    assert data["status"] == "success"
    assert data["duration"] == 1.5
    assert data["error"] is None
    assert "timestamp" in data

def test_jsonl_formatter_redacts():
    formatter = JSONLFormatter()
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname="test.py", lineno=1,
        msg="Test message", args=(), exc_info=None
    )
    record.error = {"api_key": "secret"}
    
    formatted = formatter.format(record)
    data = json.loads(formatted)
    
    assert data["error"]["api_key"] == "***REDACTED***"
