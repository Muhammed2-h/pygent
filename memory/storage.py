import sqlite3
import datetime

class MemoryStore:
    def __init__(self, db_path: str = "memory.db"):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    source TEXT,
                    confidence REAL DEFAULT 0.5,
                    verified INTEGER DEFAULT 0,
                    superseded_by INTEGER,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS skills (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT NOT NULL,
                    trigger TEXT,
                    procedure TEXT NOT NULL,
                    prerequisites TEXT,
                    verification TEXT,
                    confidence REAL DEFAULT 0.5,
                    success_count INTEGER DEFAULT 0,
                    failure_count INTEGER DEFAULT 0,
                    last_used TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            # FTS for memories
            self.conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(
                    content,
                    title,
                    content='memories',
                    content_rowid='id'
                )
            """)
            self.conn.execute("""
                CREATE TRIGGER IF NOT EXISTS memory_fts_insert AFTER INSERT ON memories BEGIN
                    INSERT INTO memory_fts(rowid, content, title) VALUES (new.id, new.content, new.title);
                END
            """)
            self.conn.execute("""
                CREATE TRIGGER IF NOT EXISTS memory_fts_update AFTER UPDATE ON memories BEGIN
                    INSERT INTO memory_fts(memory_fts, rowid, content, title) VALUES('delete', old.id, old.content, old.title);
                    INSERT INTO memory_fts(rowid, content, title) VALUES (new.id, new.content, new.title);
                END
            """)
            self.conn.execute("""
                CREATE TRIGGER IF NOT EXISTS memory_fts_delete AFTER DELETE ON memories BEGIN
                    INSERT INTO memory_fts(memory_fts, rowid, content, title) VALUES('delete', old.id, old.content, old.title);
                END
            """)
            
            # FTS for skills
            self.conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS skills_fts USING fts5(
                    name,
                    description,
                    procedure,
                    content='skills',
                    content_rowid='id'
                )
            """)
            self.conn.execute("""
                CREATE TRIGGER IF NOT EXISTS skills_fts_insert AFTER INSERT ON skills BEGIN
                    INSERT INTO skills_fts(rowid, name, description, procedure) VALUES (new.id, new.name, new.description, new.procedure);
                END
            """)
            self.conn.execute("""
                CREATE TRIGGER IF NOT EXISTS skills_fts_update AFTER UPDATE ON skills BEGIN
                    INSERT INTO skills_fts(skills_fts, rowid, name, description, procedure) VALUES('delete', old.id, old.name, old.description, old.procedure);
                    INSERT INTO skills_fts(rowid, name, description, procedure) VALUES (new.id, new.name, new.description, new.procedure);
                END
            """)
            self.conn.execute("""
                CREATE TRIGGER IF NOT EXISTS skills_fts_delete AFTER DELETE ON skills BEGIN
                    INSERT INTO skills_fts(skills_fts, rowid, name, description, procedure) VALUES('delete', old.id, old.name, old.description, old.procedure);
                END
            """)

    def add_memory(self, content: str, mem_type: str = "semantic", title: str = "") -> int:
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        if not title:
            words = content.split()
            title = " ".join(words[:5]) + ("..." if len(words) > 5 else "")
            if not title:
                title = "Untitled"
        with self.conn:
            cursor = self.conn.execute(
                "INSERT INTO memories (type, title, content, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (mem_type, title, content, now, now),
            )
            return cursor.lastrowid

    def search(self, query: str) -> list[dict]:
        cursor = self.conn.execute(
            """
            SELECT d.id, d.content, d.type as mem_type, (CASE WHEN d.superseded_by IS NULL THEN 0 ELSE 1 END) as superseded 
            FROM memory_fts f
            JOIN memories d ON f.rowid = d.id
            WHERE memory_fts MATCH ? AND d.superseded_by IS NULL
            """,
            (query,),
        )
        return [dict(row) for row in cursor.fetchall()]

    def mark_superseded(self, memory_id: int, superseded_by: int = -1):
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with self.conn:
            self.conn.execute(
                "UPDATE memories SET superseded_by = ?, updated_at = ? WHERE id = ?",
                (superseded_by, now, memory_id),
            )

    def close(self):
        self.conn.close()
