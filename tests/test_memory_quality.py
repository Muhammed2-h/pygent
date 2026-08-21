from core.memory_service import MemoryService

from memory.lifecycle import (
    ExtractedFact,
    _deduplicate_facts,
    _is_generic_knowledge,
    _is_reasoning_chain,
)
from memory.privacy import PrivacyFilter
from memory.retrieval import LayeredRetriever
from memory.storage import MemoryStore
from memory.types import MemoryLayer, MemoryType


def test_duplicate_memories(tmp_path):
    store = MemoryStore(str(tmp_path / "test_dup.db"))
    # Add a memory
    store.add_memory("The server is running on port 8080", mem_type=MemoryType.FACT)
    
    # Try deduplicating an exact match
    fact = ExtractedFact(content="The server is running on port 8080", entry_type=MemoryType.FACT)
    unique_facts = _deduplicate_facts([fact], store)
    assert len(unique_facts) == 0, "Duplicate fact should be filtered out"
    
    # Different fact
    fact2 = ExtractedFact(content="The server is on port 9090", entry_type=MemoryType.FACT)
    unique_facts2 = _deduplicate_facts([fact2], store)
    assert len(unique_facts2) == 1, "New fact should be kept"

def test_irrelevant_memory_exclusion():
    assert _is_generic_knowledge("python is a programming language")
    assert _is_reasoning_chain("let me think about this")
    assert _is_reasoning_chain("hmm, maybe we should try")

def test_superseding_and_stale_memories(tmp_path):
    store = MemoryStore(str(tmp_path / "test_stale.db"))
    retriever = LayeredRetriever(store)
    
    id1 = store.add_memory("Config file is in /etc/old.conf", mem_type=MemoryType.FACT)
    id2 = store.add_memory("Config file is in /etc/new.conf", mem_type=MemoryType.FACT)
    
    # Supersede id1 with id2
    store.mark_superseded(id1, superseded_by=id2)
    
    # Search should only return id2
    results = retriever.search("Config file")
    assert len(results) == 1
    assert results[0]["id"] == id2
    
def test_skill_confidence_and_verification(tmp_path):
    store = MemoryStore(str(tmp_path / "test_skills.db"))
    
    store.add_skill("deploy_app", "Deploy to server", "echo deploy")
    
    # Record success -> Verified
    store.record_skill_success("deploy_app")
    store.record_skill_success("deploy_app")
    
    skill = store.get_skill("deploy_app")
    assert skill["state"] == "verified"
    assert skill["confidence"] > 0.5
    
    # Record failures -> Degraded
    store.record_skill_failure("deploy_app")
    store.record_skill_failure("deploy_app")
    
    skill = store.get_skill("deploy_app")
    assert skill["state"] == "degraded"
    assert skill["confidence"] < 0.7  # it should drop

def test_failed_skills_ranking(tmp_path):
    store = MemoryStore(str(tmp_path / "test_skill_rank.db"))
    retriever = LayeredRetriever(store)
    
    store.add_skill("good_skill", "Good", "echo good")
    store.add_skill("bad_skill", "Bad", "echo bad")
    
    for _ in range(3):
        store.record_skill_success("good_skill")
        
    for _ in range(3):
        store.record_skill_failure("bad_skill")
        
    results = retriever.get_relevant_skills("good bad")
    
    # good_skill should rank higher than bad_skill
    names = [r["name"] for r in results]
    assert names[0] == "good_skill"

def test_memory_retrieval(tmp_path):
    store = MemoryStore(str(tmp_path / "test_retrieval.db"))
    retriever = LayeredRetriever(store)
    
    store.add_memory("Environment is production", mem_type=MemoryType.ENVIRONMENT)
    store.add_memory("User prefers vim", mem_type=MemoryType.PREFERENCE)
    store.add_memory("System prompt configuration", mem_type=MemoryType.SYSTEM)
    
    l2_results = retriever.retrieve(MemoryLayer.L2)
    assert len(l2_results) == 1
    assert l2_results[0]["mem_type"] == MemoryType.ENVIRONMENT
    
    l4_results = retriever.retrieve(MemoryLayer.L4)
    assert len(l4_results) == 1
    assert l4_results[0]["mem_type"] == MemoryType.PREFERENCE

def test_privacy_filtering(tmp_path):
    store = MemoryStore(str(tmp_path / "test_privacy.db"))
    privacy = PrivacyFilter()
    svc = MemoryService(store, privacy)
    
    svc.add("Connecting with key sk-abcdefghijklmnopqrstuvwxyz1234567890", mem_type=MemoryType.FACT)
    
    retriever = LayeredRetriever(store)
    results = retriever.search("Connecting")
    assert len(results) == 1
    assert "sk-" not in results[0]["content"]
    assert "[REDACTED_API_KEY]" in results[0]["content"]

