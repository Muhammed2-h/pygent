import sqlite3


class MemoryStore:
    def __init__(self, db_path: str = "memory.db"):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS memory_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL,
                    mem_type TEXT NOT NULL,
                    superseded BOOLEAN DEFAULT 0
                )
            """)
            self.conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(
                    content,
                    content='memory_data',
                    content_rowid='id'
                )
            """)
            self.conn.execute("""
                CREATE TRIGGER IF NOT EXISTS memory_fts_insert AFTER INSERT ON memory_data BEGIN
                    INSERT INTO memory_fts(rowid, content) VALUES (new.id, new.content);
                END
            """)
            self.conn.execute("""
                CREATE TRIGGER IF NOT EXISTS memory_fts_update AFTER UPDATE ON memory_data BEGIN
                    INSERT INTO memory_fts(memory_fts, rowid, content) VALUES('delete', old.id, old.content);
                    INSERT INTO memory_fts(rowid, content) VALUES (new.id, new.content);
                END
            """)

    def add_memory(self, content: str, mem_type: str = "semantic") -> int:
        with self.conn:
            cursor = self.conn.execute(
                "INSERT INTO memory_data (content, mem_type) VALUES (?, ?)",
                (content, mem_type),
            )
            return cursor.lastrowid

    def search(self, query: str) -> list[dict]:
        cursor = self.conn.execute(
            """
            SELECT d.id, d.content, d.mem_type, d.superseded 
            FROM memory_fts f
            JOIN memory_data d ON f.rowid = d.id
            WHERE memory_fts MATCH ? AND d.superseded = 0
            """,
            (query,),
        )
        return [dict(row) for row in cursor.fetchall()]

    def mark_superseded(self, memory_id: int):
        with self.conn:
            self.conn.execute(
                "UPDATE memory_data SET superseded = 1 WHERE id = ?",
                (memory_id,),
            )
