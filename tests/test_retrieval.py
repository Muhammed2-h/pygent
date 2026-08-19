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

