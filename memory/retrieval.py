import re
import sqlite3
import logging
import datetime
from typing import List, Dict
from memory.types import MemoryType, MemoryLayer
from memory.storage import MemoryStore

logger = logging.getLogger(__name__)

class LayeredRetriever:
    LAYER_MAPPING = {
        MemoryLayer.L0: [MemoryType.SYSTEM],
        MemoryLayer.L1: [MemoryType.INDEX],
        MemoryLayer.L2: [MemoryType.ENVIRONMENT, MemoryType.FACT],
        MemoryLayer.L3: [MemoryType.SKILL, MemoryType.LESSON],
        MemoryLayer.L4: [MemoryType.SESSION, MemoryType.PREFERENCE]
    }

    def __init__(self, store: MemoryStore):
        self.store = store

    def retrieve(self, layer: MemoryLayer, query: str = "") -> List[dict]:
        allowed_types = self.LAYER_MAPPING.get(layer, [])
        if not allowed_types:
            return []
            
        type_placeholders = ",".join("?" for _ in allowed_types)
        params = list(allowed_types)
        
        try:
            if not query.strip():
                # Fetch all for the given layers if query is empty
                sql = f"""
                    SELECT id, content, type as mem_type, (CASE WHEN superseded_by IS NULL THEN 0 ELSE 1 END) as superseded 
                    FROM memories 
                    WHERE type IN ({type_placeholders}) AND superseded_by IS NULL
                """
                cursor = self.store.conn.execute(sql, params)
                return [dict(row) for row in cursor.fetchall()]
                
            # Otherwise use FTS
            words = [w for w in re.findall(r"\w+", query)]
            if not words:
                # If no valid words in query, just fetch all for the given layers
                sql = f"""
                    SELECT id, content, type as mem_type, (CASE WHEN superseded_by IS NULL THEN 0 ELSE 1 END) as superseded 
                    FROM memories 
                    WHERE type IN ({type_placeholders}) AND superseded_by IS NULL
                """
                cursor = self.store.conn.execute(sql, params)
                return [dict(row) for row in cursor.fetchall()]

            fts_query = " OR ".join(f'"{w}"' for w in words)
            
            sql = f"""
                SELECT d.id, d.content, d.type as mem_type, (CASE WHEN d.superseded_by IS NULL THEN 0 ELSE 1 END) as superseded 
                FROM memory_fts f
                JOIN memories d ON f.rowid = d.id
                WHERE memory_fts MATCH ? AND d.type IN ({type_placeholders}) AND d.superseded_by IS NULL
            """
            cursor = self.store.conn.execute(sql, [fts_query] + params)
            return [dict(row) for row in cursor.fetchall()]
            
        except sqlite3.Error as e:
            logger.error(f"Database error during layered retrieval: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during layered retrieval: {e}")
            raise

    def rank(self, results: List[Dict]) -> List[Dict]:
        """Rank results based on FTS relevance + confidence + verification + success rate + recency."""
        now = datetime.datetime.now(datetime.timezone.utc)
        
        def score(item):
            # FTS relevance (SQLite FTS5 rank is usually negative, so we negate it to make it positive)
            fts_score = -item.get('rank', 0.0)
            
            # confidence
            confidence = item.get('confidence', 0.5)
            
            # verification
            verification = 1.0 if (item.get('verified') or item.get('verification')) else 0.0
            
            # success rate
            success = item.get('success_count') or 0
            failure = item.get('failure_count') or 0
            total = success + failure
            success_rate = (success / total) if total > 0 else 0.0
            
            # recency
            updated_at = item.get('updated_at') or item.get('last_used') or item.get('created_at')
            recency = 0.0
            if updated_at:
                try:
                    dt = datetime.datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=datetime.timezone.utc)
                    age_days = (now - dt).total_seconds() / 86400.0
                    recency = min(1.0, max(0.0, 1.0 - (age_days / 30.0)))
                except Exception:
                    pass
            
            item['_score'] = fts_score + confidence + verification + success_rate + recency
            return item['_score']
            
        return sorted(results, key=score, reverse=True)

    def search(self, query: str, types: List[str] = None) -> List[Dict]:
        """Search memories and rank results."""
        if not query.strip():
            return []
            
        words = [w for w in re.findall(r"\w+", query)]
        if not words:
            return []
            
        fts_query = " OR ".join(f'"{w}"' for w in words)
        
        sql = """
            SELECT d.*, f.rank, d.type as mem_type
            FROM memory_fts f
            JOIN memories d ON f.rowid = d.id
            WHERE memory_fts MATCH ? AND d.superseded_by IS NULL
        """
        params = [fts_query]
        
        if types:
            placeholders = ",".join("?" for _ in types)
            sql += f" AND d.type IN ({placeholders})"
            params.extend(types)
            
        cursor = self.store.conn.execute(sql, params)
        results = [dict(row) for row in cursor.fetchall()]
        return self.rank(results)

    def get_relevant_skills(self, query: str) -> List[Dict]:
        """Search and rank skills based on query."""
        if not query.strip():
            sql = "SELECT *, 0.0 as rank FROM skills ORDER BY updated_at DESC LIMIT 50"
            cursor = self.store.conn.execute(sql)
            results = [dict(row) for row in cursor.fetchall()]
            return self.rank(results)
            
        words = [w for w in re.findall(r"\w+", query)]
        if not words:
            return []
            
        fts_query = " OR ".join(f'"{w}"' for w in words)
        
        sql = """
            SELECT s.*, f.rank 
            FROM skills_fts f
            JOIN skills s ON f.rowid = s.id
            WHERE skills_fts MATCH ?
        """
        cursor = self.store.conn.execute(sql, [fts_query])
        results = [dict(row) for row in cursor.fetchall()]
        return self.rank(results)

    def get_environment_facts(self, query: str = "") -> List[Dict]:
        """Get and rank environment facts."""
        if query.strip():
            return self.search(query, types=[MemoryType.ENVIRONMENT, MemoryType.FACT])
            
        sql = """
            SELECT *, 0.0 as rank, type as mem_type
            FROM memories
            WHERE type IN (?, ?) AND superseded_by IS NULL
            ORDER BY updated_at DESC LIMIT 50
        """
        cursor = self.store.conn.execute(sql, [MemoryType.ENVIRONMENT, MemoryType.FACT])
        results = [dict(row) for row in cursor.fetchall()]
        return self.rank(results)

    def get_recent_lessons(self, query: str = "", limit: int = 5) -> List[Dict]:
        """Get and rank recent lessons."""
        if query.strip():
            results = self.search(query, types=[MemoryType.LESSON])
        else:
            sql = """
                SELECT *, 0.0 as rank, type as mem_type
                FROM memories
                WHERE type = ? AND superseded_by IS NULL
                ORDER BY updated_at DESC LIMIT ?
            """
            cursor = self.store.conn.execute(sql, [MemoryType.LESSON, limit])
            results = [dict(row) for row in cursor.fetchall()]
            results = self.rank(results)
            
        return results[:limit]
