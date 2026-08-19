from typing import List, Dict
from memory.types import MemoryType, MemoryLayer
from memory.storage import MemoryStore

class LayeredRetriever:
    LAYER_MAPPING = {
        MemoryLayer.L0: [],
        MemoryLayer.L1: [],
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
            
        # Search using store and filter by allowed types
        import re
        words = [w for w in re.findall(r"\w+", query) if len(w) > 3]
        if not words:
            return []
        fts_query = " OR ".join(f'"{w}"' for w in words[:5])
        
        try:
            results = self.store.search(fts_query)
        except Exception:
            return []
            
        return [r for r in results if r.get("mem_type") in allowed_types]
