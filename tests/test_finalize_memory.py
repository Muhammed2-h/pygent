"""Tests for finalize_task_memory (Task 9) and MemoryStore.add_skill."""
import pytest

from memory.lifecycle import (
    _extract_facts,
    _extract_procedures,
    _is_failed_experiment,
    _is_generic_knowledge,
    _is_reasoning_chain,
    _is_temporary_variable,
    finalize_task_memory,
)
from memory.storage import MemoryStore


@pytest.fixture
def store(tmp_path):
    db_path = str(tmp_path / "test_finalize.db")
    s = MemoryStore(db_path)
    yield s
    s.close()


# ── Filter helpers ──────────────────────────────────────────────────────

class TestFilterHelpers:
    def test_is_temporary_variable(self):
        assert _is_temporary_variable("tmp_foo = 1")
        assert _is_temporary_variable("temp_bar")
        assert _is_temporary_variable("_tmp123")
        assert _is_temporary_variable("var42")
        assert _is_temporary_variable("i = 0")
        assert _is_temporary_variable("x=5")
        assert _is_temporary_variable("j = 99")
        assert not _is_temporary_variable("The server runs on port 8080")
        assert not _is_temporary_variable("important_setting = true")
        # Tightened: free-text starting with single letters should NOT be rejected
        assert not _is_temporary_variable("i = the index used in the main loop")
        assert not _is_temporary_variable("x marks the spot")

    def test_is_reasoning_chain(self):
        assert _is_reasoning_chain("Let me think about this")
        assert _is_reasoning_chain("I think the answer is 42")
        assert _is_reasoning_chain("Maybe we should try something else")
        assert _is_reasoning_chain("Hmm, that's interesting")
        assert _is_reasoning_chain("Step 1: do something")
        assert not _is_reasoning_chain("The API uses port 3000")
        assert not _is_reasoning_chain("PostgreSQL version 14 is installed")

    def test_is_generic_knowledge(self):
        assert _is_generic_knowledge("Python is a programming language")
        assert _is_generic_knowledge("python is a programming language.")
        assert _is_generic_knowledge("HTML is a markup language")
        assert not _is_generic_knowledge("Python 3.11 is installed at /usr/bin/python3")
        assert not _is_generic_knowledge("This project uses FastAPI")

    def test_is_failed_experiment(self):
        assert _is_failed_experiment({"success": False, "content": "tried X"})
        assert _is_failed_experiment({"ok": False, "content": "Y failed"})
        assert _is_failed_experiment({"error": "ConnectionError", "content": "Z"})
        assert not _is_failed_experiment({"success": True, "content": "worked"})
        assert not _is_failed_experiment({"type": "fact", "content": "ok"})
        # Empty string error should not be treated as failure
        assert not _is_failed_experiment({"error": "", "content": "ok"})


# ── Extraction ──────────────────────────────────────────────────────────

class TestExtraction:
    def test_extract_facts_basic(self):
        history = [
            {"type": "fact", "content": "Port 8080 is open", "verified": True},
            {"type": "observation", "content": "Disk usage is 42%"},
            {"type": "other", "content": "Some internal note"},
        ]
        facts = _extract_facts(history)
        assert len(facts) == 2
        assert facts[0].content == "Port 8080 is open"
        assert facts[1].content == "Disk usage is 42%"

    def test_extract_facts_rejects_temp_vars(self):
        history = [
            {"type": "fact", "content": "tmp_counter = 5"},
        ]
        assert _extract_facts(history) == []

    def test_extract_facts_rejects_reasoning(self):
        history = [
            {"type": "fact", "content": "Let me think about this problem"},
        ]
        assert _extract_facts(history) == []

    def test_extract_facts_rejects_generic(self):
        history = [
            {"type": "fact", "content": "Python is a programming language"},
        ]
        assert _extract_facts(history) == []

    def test_extract_facts_rejects_failed(self):
        history = [
            {"type": "fact", "content": "This is valid", "success": False},
        ]
        assert _extract_facts(history) == []

    def test_extract_facts_rejects_unverified_low_confidence(self):
        history = [
            {"type": "fact", "content": "Might be port 80", "confidence": 0.1, "verified": False},
        ]
        assert _extract_facts(history) == []

    def test_extract_procedures_basic(self):
        history = [
            {
                "type": "procedure",
                "name": "deploy_app",
                "description": "Deploy the application",
                "procedure": "Run docker compose up -d",
                "trigger": "deploy command",
                "confidence": 0.9,
            },
            {
                "type": "skill",
                "name": "run_tests",
                "procedure": "pytest -x tests/",
            },
        ]
        procs = _extract_procedures(history)
        assert len(procs) == 2
        assert procs[0].name == "deploy_app"
        assert procs[1].name == "run_tests"

    def test_extract_procedures_rejects_failed(self):
        history = [
            {
                "type": "procedure",
                "name": "bad_deploy",
                "procedure": "Run bad command",
                "success": False,
            },
        ]
        assert _extract_procedures(history) == []

    def test_extract_procedures_rejects_reasoning_content(self):
        history = [
            {
                "type": "procedure",
                "name": "think_step",
                "procedure": "Let me think about this approach",
            },
        ]
        assert _extract_procedures(history) == []

    def test_extract_procedures_skips_missing_name(self):
        history = [
            {"type": "procedure", "procedure": "do something"},
        ]
        assert _extract_procedures(history) == []


# ── finalize_task_memory integration ────────────────────────────────────

class TestFinalizeTaskMemory:
    def test_empty_history(self, store):
        result = finalize_task_memory([], store)
        assert result.facts_persisted == 0
        assert result.procedures_persisted == 0
        assert "Empty execution history" in result.details[0]

    def test_persists_facts_to_l2(self, store):
        history = [
            {"type": "fact", "content": "Server runs on port 8080", "verified": True, "confidence": 0.9},
            {"type": "environment", "content": "Node.js v18 installed", "source": "environment scan"},
        ]
        result = finalize_task_memory(history, store)
        assert result.facts_persisted == 2
        assert result.procedures_persisted == 0

        # Verify persisted in DB
        found = store.search("port 8080")
        assert len(found) == 1
        assert found[0]["content"] == "Server runs on port 8080"

    def test_persists_procedures_to_l3(self, store):
        history = [
            {
                "type": "skill",
                "name": "restart_nginx",
                "description": "Restart nginx service",
                "procedure": "sudo systemctl restart nginx",
                "trigger": "nginx not responding",
                "confidence": 0.8,
            },
        ]
        result = finalize_task_memory(history, store)
        assert result.procedures_persisted == 1
        assert result.facts_persisted == 0

        # Verify persisted in DB
        skills = store.search_skills("nginx")
        assert len(skills) == 1
        assert skills[0]["name"] == "restart_nginx"

    def test_rejects_all_bad_entries(self, store):
        history = [
            {"type": "fact", "content": "tmp_var = 42"},  # temp var
            {"type": "fact", "content": "Let me think about it"},  # reasoning
            {"type": "fact", "content": "Python is a programming language"},  # generic
            {"type": "fact", "content": "This failed", "success": False},  # failed
            {"type": "fact", "content": "Uncertain claim", "confidence": 0.1, "verified": False},  # unverified
            {"type": "random", "content": "Not a fact type"},  # wrong type
        ]
        result = finalize_task_memory(history, store)
        assert result.facts_persisted == 0
        assert result.procedures_persisted == 0
        assert result.items_rejected == 6

    def test_deduplicates_within_batch(self, store):
        history = [
            {"type": "fact", "content": "Port 3000 is open", "verified": True},
            {"type": "fact", "content": "Port 3000 is open", "verified": True},
            {"type": "fact", "content": "port 3000 is open", "verified": True},  # case-insensitive dup
        ]
        result = finalize_task_memory(history, store)
        assert result.facts_persisted == 1

    def test_deduplicates_against_existing_store(self, store):
        # Pre-populate store
        store.add_memory("Port 5432 is open", "fact")

        history = [
            {"type": "fact", "content": "Port 5432 is open", "verified": True},
            {"type": "fact", "content": "Port 8080 is new", "verified": True},
        ]
        result = finalize_task_memory(history, store)
        assert result.facts_persisted == 1  # only the new one

    def test_skill_upsert(self, store):
        # Add a skill first
        store.add_skill(
            name="deploy_app",
            description="old description",
            procedure="old procedure",
        )

        history = [
            {
                "type": "skill",
                "name": "deploy_app",
                "description": "Updated deploy process",
                "procedure": "docker compose up --build -d",
                "confidence": 0.9,
            },
        ]
        result = finalize_task_memory(history, store)
        assert result.procedures_persisted == 1

        # Verify updated
        skills = store.search_skills("deploy")
        assert len(skills) == 1
        assert skills[0]["description"] == "Updated deploy process"

    def test_mixed_history(self, store):
        history = [
            {"type": "fact", "content": "Redis runs on port 6379", "verified": True},
            {"type": "observation", "content": "API latency is 50ms"},
            {"type": "procedure", "name": "cache_clear", "procedure": "redis-cli FLUSHALL", "confidence": 0.7},
            {"type": "fact", "content": "tmp_x = 10"},  # rejected
            {"type": "fact", "content": "Let me think about caching"},  # rejected
            {"type": "skill", "name": "bad_skill", "procedure": "fail", "success": False},  # rejected
        ]
        result = finalize_task_memory(history, store)
        assert result.facts_persisted == 2
        assert result.procedures_persisted == 1
        assert result.items_rejected >= 3

    def test_environment_source_sets_type(self, store):
        history = [
            {"type": "environment", "content": "Docker version 24.0.5", "source": "environment check"},
        ]
        result = finalize_task_memory(history, store)
        assert result.facts_persisted == 1

        # Check it was stored as environment type
        rows = store.conn.execute(
            "SELECT type FROM memories WHERE content = ?", ("Docker version 24.0.5",)
        ).fetchall()
        assert len(rows) == 1
        assert rows[0]["type"] == "environment"

    def test_environment_entry_type_routes_without_source(self, store):
        """Entry type='environment' should route to ENVIRONMENT even if source doesn't contain 'environment'."""
        history = [
            {"type": "environment", "content": "Node.js v20 installed", "source": "scan"},
        ]
        result = finalize_task_memory(history, store)
        assert result.facts_persisted == 1

        rows = store.conn.execute(
            "SELECT type FROM memories WHERE content = ?", ("Node.js v20 installed",)
        ).fetchall()
        assert len(rows) == 1
        assert rows[0]["type"] == "environment"

    def test_result_details_summary(self, store):
        history = [
            {"type": "fact", "content": "Valid fact here", "verified": True},
        ]
        result = finalize_task_memory(history, store)
        summary = result.details[-1]
        assert "1 facts" in summary
        assert "0 procedures" in summary


# ── MemoryStore.add_skill tests ─────────────────────────────────────────

class TestMemoryStoreAddSkill:
    def test_add_and_search_skill(self, store):
        skill_id = store.add_skill(
            name="test_skill",
            description="A test skill",
            procedure="do the thing",
        )
        assert skill_id > 0

        results = store.search_skills("test_skill")
        assert len(results) == 1
        assert results[0]["name"] == "test_skill"
        assert results[0]["procedure"] == "do the thing"

    def test_upsert_updates_existing(self, store):
        id1 = store.add_skill(name="my_skill", description="v1", procedure="step1")
        id2 = store.add_skill(name="my_skill", description="v2", procedure="step2")
        assert id1 == id2  # same row updated

        results = store.search_skills("my_skill")
        assert len(results) == 1
        assert results[0]["description"] == "v2"
        assert results[0]["procedure"] == "step2"

    def test_add_skill_with_all_fields(self, store):
        store.add_skill(
            name="full_skill",
            description="Complete skill",
            procedure="do X then Y",
            trigger="when Z happens",
            prerequisites="need A and B",
            verification="check C",
            confidence=0.95,
        )
        results = store.search_skills("full_skill")
        assert len(results) == 1
        r = results[0]
        assert r["trigger"] == "when Z happens"
        assert r["prerequisites"] == "need A and B"
        assert r["verification"] == "check C"
        assert r["confidence"] == 0.95
