import sqlite3
import datetime
import pathlib
import tempfile

class MemoryStore:
    def __init__(self, db_path: str = "memory.db", skills_dir: pathlib.Path | str | None = None):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.db_path = pathlib.Path(db_path)
        if db_path == ":memory:":
            self._temp_dir = tempfile.TemporaryDirectory()
            self.skills_dir = pathlib.Path(self._temp_dir.name) / "skills"
        else:
            self._temp_dir = None
            if skills_dir:
                self.skills_dir = pathlib.Path(skills_dir)
            else:
                self.skills_dir = self.db_path.parent / "skills"
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
                    prerequisites TEXT,
                    verification TEXT,
                    confidence REAL DEFAULT 0.5,
                    success_count INTEGER DEFAULT 0,
                    failure_count INTEGER DEFAULT 0,
                    last_used TEXT,
                    state TEXT DEFAULT 'candidate',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            try:
                self.conn.execute("ALTER TABLE skills ADD COLUMN state TEXT DEFAULT 'candidate'")
            except sqlite3.OperationalError:
                pass
                
            # Drop legacy triggers that relied on procedure in skills
            self.conn.execute("DROP TRIGGER IF EXISTS skills_fts_insert")
            self.conn.execute("DROP TRIGGER IF EXISTS skills_fts_update")
            self.conn.execute("DROP TRIGGER IF EXISTS skills_fts_delete")

            # Migrate old schemas by dropping the duplicate procedure column
            try:
                self.conn.execute("ALTER TABLE skills DROP COLUMN procedure")
            except sqlite3.OperationalError:
                pass
                
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
            
            # Recreate FTS for skills as a standalone table to keep procedure searchable
            # We drop it first to ensure we migrate from content='skills' and keep it synced with markdown
            self.conn.execute("DROP TABLE IF EXISTS skills_fts")
            self.conn.execute("""
                CREATE VIRTUAL TABLE skills_fts USING fts5(
                    name,
                    description,
                    procedure
                )
            """)
            
            # Sync existing skills into the standalone FTS index
            cursor = self.conn.execute("SELECT id, name, description FROM skills")
            for row in cursor.fetchall():
                proc = self._read_skill_markdown(row["name"], "")
                self.conn.execute(
                    "INSERT INTO skills_fts(rowid, name, description, procedure) VALUES (?, ?, ?, ?)",
                    (row["id"], row["name"], row["description"], proc)
                )

    def add_memory(self, content: str, mem_type: str = "semantic", title: str = "") -> int:
        now = datetime.datetime.now(datetime.UTC).isoformat()
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
        now = datetime.datetime.now(datetime.UTC).isoformat()
        with self.conn:
            self.conn.execute(
                "UPDATE memories SET superseded_by = ?, updated_at = ? WHERE id = ?",
                (superseded_by, now, memory_id),
            )

    def update_skill_state(self, name: str, state: str) -> None:
        now = datetime.datetime.now(datetime.UTC).isoformat()
        with self.conn:
            self.conn.execute(
                "UPDATE skills SET state = ?, updated_at = ? WHERE name = ?",
                (state, now, name)
            )

    def _get_safe_skill_path(self, name: str) -> pathlib.Path:
        skill_path = (self.skills_dir / f"{name}.md").resolve()
        if not skill_path.is_relative_to(self.skills_dir.resolve()):
            raise ValueError(f"Invalid skill name: {name}")
        return skill_path

    def _write_skill_markdown(self, name: str, procedure: str):
        skill_path = self._get_safe_skill_path(name)
        skill_path.parent.mkdir(parents=True, exist_ok=True)
        with open(skill_path, "w", encoding="utf-8") as f:
            f.write(procedure)

    def _read_skill_markdown(self, name: str, default_procedure: str) -> str:
        try:
            skill_path = self._get_safe_skill_path(name)
            if skill_path.exists():
                with open(skill_path, "r", encoding="utf-8") as f:
                    return f.read()
        except ValueError:
            pass
        return default_procedure

    def get_skill(self, name: str) -> dict | None:
        cursor = self.conn.execute("SELECT * FROM skills WHERE name = ?", (name,))
        row = cursor.fetchone()
        if not row:
            return None
        result = dict(row)
        result["procedure"] = self._read_skill_markdown(name, result.get("procedure", ""))
        return result

    def add_skill(
        self,
        name: str,
        description: str,
        procedure: str,
        trigger: str = "",
        prerequisites: str = "",
        verification: str = "",
        confidence: float = 0.5,
    ) -> int:
        """Insert a new skill or update an existing one by name (upsert)."""
        now = datetime.datetime.now(datetime.UTC).isoformat()
        
        self._write_skill_markdown(name, procedure)
        
        with self.conn:
            existing = self.conn.execute(
                "SELECT id FROM skills WHERE name = ?", (name,)
            ).fetchone()
            if existing:
                skill_id = existing["id"]
                self.conn.execute(
                    """UPDATE skills
                       SET description=?, trigger=?,
                           prerequisites=?, verification=?, confidence=?,
                           updated_at=?
                       WHERE name=?""",
                    (description, trigger, prerequisites,
                     verification, confidence, now, name),
                )
                # Attempt to clear dead procedure data if the column wasn't dropped
                try:
                    self.conn.execute("UPDATE skills SET procedure='' WHERE name=?", (name,))
                except sqlite3.OperationalError:
                    pass
                
                # Update standalone FTS
                self.conn.execute("DELETE FROM skills_fts WHERE rowid = ?", (skill_id,))
                self.conn.execute(
                    "INSERT INTO skills_fts(rowid, name, description, procedure) VALUES (?, ?, ?, ?)",
                    (skill_id, name, description, procedure)
                )
                return skill_id
            
            try:
                cursor = self.conn.execute(
                    """INSERT INTO skills
                       (name, description, trigger, prerequisites,
                        verification, confidence, created_at, updated_at)
                       VALUES (?,?,?,?,?,?,?,?)""",
                    (name, description, trigger, prerequisites,
                     verification, confidence, now, now),
                )
            except sqlite3.IntegrityError:
                # Fallback for old SQLite schemas where ALTER TABLE DROP COLUMN procedure failed
                cursor = self.conn.execute(
                    """INSERT INTO skills
                       (name, description, trigger, procedure, prerequisites,
                        verification, confidence, created_at, updated_at)
                       VALUES (?,?,?,?,?,?,?,?,?)""",
                    (name, description, trigger, "", prerequisites,
                     verification, confidence, now, now),
                )
            
            skill_id = cursor.lastrowid
            self.conn.execute(
                "INSERT INTO skills_fts(rowid, name, description, procedure) VALUES (?, ?, ?, ?)",
                (skill_id, name, description, procedure)
            )
            return skill_id

    def search_skills(self, query: str) -> list[dict]:
        """Full-text search across skills."""
        cursor = self.conn.execute(
            """SELECT s.*
               FROM skills_fts f
               JOIN skills s ON f.rowid = s.id
               WHERE skills_fts MATCH ? ORDER BY f.rank""",
            (query,),
        )
        results = [dict(row) for row in cursor.fetchall()]
        for r in results:
            r["procedure"] = self._read_skill_markdown(r["name"], r.get("procedure", ""))
        return results

    def record_skill_success(self, name: str) -> None:
        now = datetime.datetime.now(datetime.UTC).isoformat()
        with self.conn:
            skill = self.conn.execute("SELECT confidence, success_count FROM skills WHERE name = ?", (name,)).fetchone()
            if skill:
                increments = [0.15, 0.10, 0.05, 0.02, 0.01]
                inc = increments[skill["success_count"]] if skill["success_count"] < len(increments) else 0.01
                new_conf = round(min(1.0, skill["confidence"] + inc), 2)
                self.conn.execute(
                    "UPDATE skills SET confidence = ?, success_count = ?, last_used = ?, updated_at = ? WHERE name = ?",
                    (new_conf, skill["success_count"] + 1, now, now, name)
                )

    def record_skill_failure(self, name: str) -> None:
        now = datetime.datetime.now(datetime.UTC).isoformat()
        with self.conn:
            skill = self.conn.execute("SELECT confidence, failure_count FROM skills WHERE name = ?", (name,)).fetchone()
            if skill:
                new_conf = round(max(0.0, skill["confidence"] - 0.15), 2)
                self.conn.execute(
                    "UPDATE skills SET confidence = ?, failure_count = ?, last_used = ?, state = 'degraded', updated_at = ? WHERE name = ?",
                    (new_conf, skill["failure_count"] + 1, now, now, name)
                )

    def close(self):
        self.conn.close()
