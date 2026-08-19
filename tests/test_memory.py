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
