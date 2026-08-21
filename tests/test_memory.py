import os
import pytest
from memory.storage import MemoryStore


def test_memory_storage(tmp_path):
    db_path = str(tmp_path / "test_memory.db")
    store = MemoryStore(db_path)
    store.add_memory("FastAPI is used", "semantic")
    store.add_memory("Django is used", "semantic")

    res = store.search("FastAPI")
    assert len(res) == 1
    assert res[0]["content"] == "FastAPI is used"
    assert res[0]["mem_type"] == "semantic"
    assert res[0]["superseded"] == 0

    store.mark_superseded(res[0]["id"])
    assert len(store.search("FastAPI")) == 0


def test_memory_storage_standalone():
    db_path = "test_memory_standalone.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    try:
        store = MemoryStore(db_path)
        id1 = store.add_memory("FastAPI is used", "semantic")
        store.add_memory("Django is used", "semantic")

        res = store.search("FastAPI")
        assert len(res) == 1
        assert res[0]["id"] == id1
        assert res[0]["content"] == "FastAPI is used"

        store.mark_superseded(res[0]["id"])
        assert len(store.search("FastAPI")) == 0
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)


def test_memory_search_multiple_and_no_match(tmp_path):
    db_path = str(tmp_path / "test_search.db")
    store = MemoryStore(db_path)
    store.add_memory("Python is great for AI", "observation")
    store.add_memory("Python has async support", "observation")
    store.add_memory("Rust is fast", "observation")

    res = store.search("Python")
    assert len(res) == 2
    contents = {r["content"] for r in res}
    assert "Python is great for AI" in contents
    assert "Python has async support" in contents

    no_match = store.search("Golang")
    assert len(no_match) == 0


def test_privacy_filter():
    from memory.privacy import PrivacyFilter

    privacy = PrivacyFilter()
    text = "Here is my openai key: sk-abcdefghijklmnopqrstuvwxyz12345 and gemini key: AIzaSyD12345678901234567890123456789012 and normal text."
    scrubbed = privacy.scrub(text)
    assert "sk-" not in scrubbed
    assert "[REDACTED_API_KEY]" in scrubbed
    assert "AIzaSy" not in scrubbed
    assert "[REDACTED_GEMINI_KEY]" in scrubbed
    assert "normal text" in scrubbed

def test_privacy_filter_expanded():
    from memory.privacy import PrivacyFilter

    privacy = PrivacyFilter()
    text = """anthropic: sk-ant-api03-abcdef1234567890abcdef
bearer: Bearer token123
cookie: Set-Cookie: sessionid=123
session: session_token=abc
auth: Authorization: Basic abc
url: https://user:pass@example.com
pwd: password=secret"""
    scrubbed = privacy.scrub(text)
    assert "sk-ant" not in scrubbed
    assert "[REDACTED_ANTHROPIC_KEY]" in scrubbed
    assert "token123" not in scrubbed
    assert "[REDACTED_BEARER_TOKEN]" in scrubbed
    assert "sessionid=123" not in scrubbed
    assert "[REDACTED_COOKIE]" in scrubbed
    assert "session_token=abc" not in scrubbed
    assert "[REDACTED_SESSION_TOKEN]" in scrubbed
    assert "Basic abc" not in scrubbed
    assert "[REDACTED_AUTH_HEADER]" in scrubbed
    assert "user:pass" not in scrubbed
    assert "[REDACTED_CREDENTIALS]" in scrubbed
    assert "secret" not in scrubbed
    assert "[REDACTED_PASSWORD]" in scrubbed



def test_privacy_filter_structured_formats():
    from memory.privacy import PrivacyFilter

    privacy = PrivacyFilter()
    
    # JSON-like
    json_text = '{"password": "supersecret", "safe": "data", "cookie": "sessionid=123", "Authorization": "Bearer abc"}'
    scrubbed_json = privacy.scrub(json_text)
    assert '"password": "[REDACTED_PASSWORD]"' in scrubbed_json
    assert '"safe": "data"' in scrubbed_json
    assert '"cookie": "[REDACTED_COOKIE]"' in scrubbed_json
    assert '"Authorization": "[REDACTED_AUTH_HEADER]"' in scrubbed_json

    # Dict-like
    dict_text = "{'pwd': 'supersecret', 'other': 'value', 'session_token': 'abc'}"
    scrubbed_dict = privacy.scrub(dict_text)
    assert "'pwd': '[REDACTED_PASSWORD]'" in scrubbed_dict
    assert "'other': 'value'" in scrubbed_dict
    assert "'session_token': '[REDACTED_SESSION_TOKEN]'" in scrubbed_dict

    # Single-line headers (previously problematic)
    headers = "Cookie: sessionid=123, other_header=xyz"
    scrubbed_headers = privacy.scrub(headers)
    assert "Cookie: [REDACTED_COOKIE]" in scrubbed_headers
    assert ", other_header=xyz" in scrubbed_headers

def test_memory_service(tmp_path):
    from memory.privacy import PrivacyFilter
    from memory.service import MemoryService

    db_path = str(tmp_path / "test_memory_svc.db")
    store = MemoryStore(db_path)
    privacy = PrivacyFilter()
    svc = MemoryService(store, privacy)

    svc.add("My key is sk-12345678901234567890 and I like python.")
    context = svc.get_context_for("python")

    assert "[REDACTED_API_KEY]" in context
    assert "sk-" not in context
    assert "Relevant Context:" in context
    assert "- My key is [REDACTED_API_KEY] and I like python." in context


def test_memory_service_standalone_and_edge_cases():
    import os
    from memory.privacy import PrivacyFilter
    from memory.service import MemoryService

    db_path = "test_memory_svc_standalone.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    try:
        store = MemoryStore(db_path)
        privacy = PrivacyFilter()
        svc = MemoryService(store, privacy)

        svc.add("User prefers dark mode and vim keybindings", "preference")
        svc.add("User is working on a machine learning project with Python", "semantic")

        # Test short words query
        assert svc.get_context_for("a is on") == ""

        # Test no match
        assert svc.get_context_for("javascript typescript") == ""

        # Test context formatting
        ctx = svc.get_context_for("machine learning")
        assert "Relevant Context:" in ctx
        assert "machine learning" in ctx

        # Test special characters/invalid FTS query resilience
        assert svc.get_context_for('*** """ :::') == ""
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)


def test_new_tables_created(tmp_path):
    db_path = str(tmp_path / "test_tables.db")
    store = MemoryStore(db_path)
    
    with store.conn:
        tables = store.conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        table_names = [t["name"] for t in tables]
        assert "memories" in table_names
        assert "skills" in table_names
        assert "memory_fts" in table_names
        assert "skills_fts" in table_names

def test_skill_lifecycle(tmp_path):
    db_path = str(tmp_path / "test_skills.db")
    store = MemoryStore(db_path)
    store.add_skill("test_skill", "desc", "proc", confidence=0.50)
    
    # Test initial state
    with store.conn:
        row = store.conn.execute("SELECT state FROM skills WHERE name='test_skill'").fetchone()
        assert row["state"] == 'candidate'

    # Test success 1 (0.50 + 0.15 = 0.65)
    store.record_skill_success("test_skill")
    with store.conn:
        row = store.conn.execute("SELECT confidence, success_count, state FROM skills WHERE name='test_skill'").fetchone()
        assert row["confidence"] == 0.65
        assert row["success_count"] == 1
        assert row["state"] == 'candidate'
        
    # Test success 2 (0.65 + 0.10 = 0.75) -> verified
    store.record_skill_success("test_skill")
    with store.conn:
        row = store.conn.execute("SELECT confidence, success_count, state FROM skills WHERE name='test_skill'").fetchone()
        assert row["confidence"] == 0.75
        assert row["success_count"] == 2
        assert row["state"] == 'verified'
        
    # Test successes up to 5 -> trusted
    store.record_skill_success("test_skill")
    store.record_skill_success("test_skill")
    store.record_skill_success("test_skill")
    with store.conn:
        row = store.conn.execute("SELECT success_count, state FROM skills WHERE name='test_skill'").fetchone()
        assert row["success_count"] == 5
        assert row["state"] == 'trusted'

    # Test failure 1 -> still trusted
    store.record_skill_failure("test_skill")
    with store.conn:
        row = store.conn.execute("SELECT failure_count, state FROM skills WHERE name='test_skill'").fetchone()
        assert row["failure_count"] == 1
        assert row["state"] == 'trusted'

    # Test failure 2 -> degraded
    store.record_skill_failure("test_skill")
    with store.conn:
        row = store.conn.execute("SELECT failure_count, state FROM skills WHERE name='test_skill'").fetchone()
        assert row["failure_count"] == 2
        assert row["state"] == 'degraded'

    # Test state update
    store.update_skill_state("test_skill", "reused")
    with store.conn:
        row = store.conn.execute("SELECT state FROM skills WHERE name='test_skill'").fetchone()
        assert row["state"] == 'reused'

    # Test clamp upper
    for _ in range(50):
        store.record_skill_success("test_skill")
    with store.conn:
        row = store.conn.execute("SELECT confidence FROM skills WHERE name='test_skill'").fetchone()
        assert row["confidence"] == 1.0
        
    # Test clamp lower
    for _ in range(20):
        store.record_skill_failure("test_skill")
    with store.conn:
        row = store.conn.execute("SELECT confidence FROM skills WHERE name='test_skill'").fetchone()
        assert row["confidence"] == 0.0

