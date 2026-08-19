import re
import sqlite3
import logging
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
