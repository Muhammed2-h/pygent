import pytest
from memory.storage import MemoryStore
from memory.privacy import PrivacyFilter
from memory.service import MemoryService
from datetime import datetime, timezone, timedelta

def test_get_relevant_skills(tmp_path):
    db_path = str(tmp_path / "test_relevant_skills.db")
    store = MemoryStore(db_path)
    privacy = PrivacyFilter()
    svc = MemoryService(store, privacy)
    
    now_str = datetime.now(timezone.utc).isoformat()
    old_str = (datetime.now(timezone.utc) - timedelta(days=15)).isoformat()
    
    store.add_skill("skill_1", "desc1", "proc1", confidence=0.9)
    # Give skill 1 some history
    store.conn.execute("UPDATE skills SET success_count=10, failure_count=0, last_used=? WHERE name='skill_1'", (now_str,))
    
    store.add_skill("skill_2", "desc2", "proc2", confidence=0.2)
    store.conn.execute("UPDATE skills SET success_count=0, failure_count=10, last_used=? WHERE name='skill_2'", (old_str,))

    # Skill 1 is highly relevant and successful.
    skills = svc.get_relevant_skills("skill_1")
    assert len(skills) > 0
    assert skills[0]['name'] == 'skill_1'
    assert skills[0]['score'] > 0.0
    
    # Content is procedure
    assert skills[0]['content'] == 'proc1'

def test_get_relevant_skills_no_match(tmp_path):
    db_path = str(tmp_path / "test_relevant_skills2.db")
    store = MemoryStore(db_path)
    privacy = PrivacyFilter()
    svc = MemoryService(store, privacy)
    
    assert len(svc.get_relevant_skills("no match at all")) == 0
