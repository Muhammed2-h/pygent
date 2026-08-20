import pytest
from memory.types import MemoryType, MemoryLayer
from memory.retrieval import LayeredRetriever
from memory.storage import MemoryStore

def test_layered_retrieval(tmp_path):
    db_path = str(tmp_path / "test_retrieval.db")
    store = MemoryStore(db_path)
    
    store.add_memory("Agent name is Bob", mem_type=MemoryType.FACT)
    store.add_memory("OS is Linux", mem_type=MemoryType.ENVIRONMENT)
    store.add_memory("User likes fast responses", mem_type=MemoryType.PREFERENCE)
    store.add_memory("Always verify before acting", mem_type=MemoryType.LESSON)
    store.add_memory("Past session discussed AI", mem_type=MemoryType.SESSION)
    
    retriever = LayeredRetriever(store)
    
    # Layer 2 should only retrieve Environment Facts (fact, environment)
    l2_results = retriever.retrieve(layer=MemoryLayer.L2, query="Linux Agent")
    types = {r['mem_type'] for r in l2_results}
    assert MemoryType.ENVIRONMENT in types
    assert MemoryType.FACT in types
    assert MemoryType.PREFERENCE not in types
    
    # Layer 3 should retrieve Skills and SOPs (lesson, skill)
    l3_results = retriever.retrieve(layer=MemoryLayer.L3, query="verify")
    types = {r['mem_type'] for r in l3_results}
    assert MemoryType.LESSON in types
    
    # Layer 4 should retrieve Session archives (session, preference)
    l4_results = retriever.retrieve(layer=MemoryLayer.L4, query="discussed fast")
    types = {r['mem_type'] for r in l4_results}
    assert MemoryType.SESSION in types
    assert MemoryType.PREFERENCE in types
    
    # Test empty query should return all for layer
    empty_results = retriever.retrieve(layer=MemoryLayer.L2, query="")
    assert len(empty_results) == 2
    
    # Test L0 and L1
    store.add_memory("System rule 1", mem_type=MemoryType.SYSTEM)
    l0_results = retriever.retrieve(layer=MemoryLayer.L0, query="")
    assert len(l0_results) == 1
    assert l0_results[0]['mem_type'] == MemoryType.SYSTEM


def test_advanced_retrieval(tmp_path):
    import datetime
    db_path = str(tmp_path / "test_adv_retrieval.db")
    store = MemoryStore(db_path)
    
    # Add skills manually
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    old = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=10)).isoformat()
    store.add_skill("skill1", "A fast python skill", "def fast(): pass")
    for _ in range(10):
        store.record_skill_success("skill1")
    store.conn.execute("UPDATE skills SET updated_at = ?, created_at = ? WHERE name = 'skill1'", (now, now))
    
    store.add_skill("skill2", "A slow python skill", "def slow(): pass")
    for _ in range(2):
        store.record_skill_success("skill2")
    for _ in range(8):
        store.record_skill_failure("skill2")
    store.conn.execute("UPDATE skills SET updated_at = ?, created_at = ? WHERE name = 'skill2'", (old, old))
    
    # Add memories
    store.add_memory("System is running ubuntu linux", mem_type=MemoryType.ENVIRONMENT)
    store.add_memory("Agent name is test bot", mem_type=MemoryType.FACT)
    store.add_memory("Always write tests before code", mem_type=MemoryType.LESSON)
    store.add_memory("User likes dark mode", mem_type=MemoryType.PREFERENCE)
    
    retriever = LayeredRetriever(store)
    
    # Test get_relevant_skills
    skills = retriever.get_relevant_skills("python")
    assert len(skills) == 2
    # skill1 should rank higher due to success rate and recency
    assert skills[0]['name'] == 'skill1'
    assert skills[1]['name'] == 'skill2'
    
    # Test get_environment_facts
    env_facts = retriever.get_environment_facts()
    types = {f['mem_type'] for f in env_facts}
    assert MemoryType.ENVIRONMENT in types
    assert MemoryType.FACT in types
    assert len(env_facts) == 2
    
    # Test get_environment_facts with query
    env_facts_query = retriever.get_environment_facts("ubuntu")
    assert len(env_facts_query) == 1
    assert "ubuntu" in env_facts_query[0]['content']
    
    # Test get_recent_lessons
    lessons = retriever.get_recent_lessons()
    assert len(lessons) == 1
    assert "tests before code" in lessons[0]['content']
    
    # Test global search
    results = retriever.search("dark mode")
    assert len(results) == 1
    assert results[0]['mem_type'] == MemoryType.PREFERENCE
