import aiosqlite
import logging
from pathlib import Path
from typing import Optional, List, Tuple
from antigracall.db.models import Session, Message

logger = logging.getLogger("antigracall.db.repository")

class DatabaseRepository:
    """Gestisce la persistenza in SQLite in modo asincrono."""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path

    async def initialize(self):
        """Crea le tabelle necessarie se non esistono."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"Inizializzazione database SQLite in: {self.db_path}")
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    workspace_path TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active INTEGER DEFAULT 1,
                    model TEXT
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT REFERENCES sessions(id) ON DELETE CASCADE,
                    role TEXT CHECK(role IN ('user', 'agent')),
                    content TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Migrazione: aggiunge la colonna 'model' se non presente in un DB preesistente
            try:
                await db.execute("ALTER TABLE sessions ADD COLUMN model TEXT")
            except aiosqlite.OperationalError:
                pass
            await db.commit()

    async def get_active_session(self) -> Optional[Session]:
        """Recupera l'ultima sessione attiva salvata."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM sessions WHERE is_active = 1 ORDER BY updated_at DESC LIMIT 1"
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return Session(
                        row['id'], 
                        row['workspace_path'], 
                        row['created_at'], 
                        row['updated_at'], 
                        row['is_active'],
                        row['model'] if 'model' in row.keys() else None
                    )
        return None

    async def get_session(self, session_id: str) -> Optional[Session]:
        """Recupera i dettagli di una specifica sessione."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM sessions WHERE id = ?",
                (session_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return Session(
                        row['id'], 
                        row['workspace_path'], 
                        row['created_at'], 
                        row['updated_at'], 
                        row['is_active'],
                        row['model'] if 'model' in row.keys() else None
                    )
        return None

    async def create_session(self, session_id: str, workspace_path: str, model: Optional[str] = None) -> Session:
        """Crea una nuova sessione e disattiva le precedenti."""
        async with aiosqlite.connect(self.db_path) as db:
            # Disattiva le vecchie sessioni
            await db.execute("UPDATE sessions SET is_active = 0 WHERE is_active = 1")
            # Inserisce la nuova
            await db.execute(
                "INSERT INTO sessions (id, workspace_path, model) VALUES (?, ?, ?)",
                (session_id, workspace_path, model)
            )
            await db.commit()
            return Session(session_id, workspace_path, "", "", 1, model)

    async def activate_session(self, session_id: str):
        """Disattiva tutte le sessioni e attiva quella specificata."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE sessions SET is_active = 0 WHERE is_active = 1")
            await db.execute(
                "UPDATE sessions SET is_active = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (session_id,)
            )
            await db.commit()

    async def update_session_workspace(self, session_id: str, workspace_path: str):
        """Aggiorna il workspace della sessione corrente."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE sessions SET workspace_path = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (workspace_path, session_id)
            )
            await db.commit()

    async def update_session_model(self, session_id: str, model: Optional[str]):
        """Aggiorna il modello associato alla sessione corrente."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE sessions SET model = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (model, session_id)
            )
            await db.commit()

    async def close_session(self, session_id: str):
        """Marca una sessione come inattiva (chiusa)."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE sessions SET is_active = 0, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (session_id,)
            )
            await db.commit()

    async def delete_session(self, session_id: str):
        """Elimina una sessione (e per cascata i suoi messaggi)."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            await db.commit()

    async def add_message(self, session_id: str, role: str, content: str):
        """Salva un messaggio ed aggiorna il timestamp della sessione."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)",
                (session_id, role, content)
            )
            await db.execute(
                "UPDATE sessions SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (session_id,)
            )
            await db.commit()

    async def get_history(self, session_id: str) -> List[Message]:
        """Ottiene lo storico dei messaggi per una determinata sessione."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM messages WHERE session_id = ? ORDER BY timestamp ASC",
                (session_id,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [
                    Message(r['id'], r['session_id'], r['role'], r['content'], r['timestamp']) 
                    for r in rows
                ]

    async def get_recent_sessions(self, limit: int = 10) -> List[Tuple[str, str, str]]:
        """Recupera le ultime sessioni con una preview del primo messaggio dell'utente."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(r"""
                SELECT s.id, s.workspace_path, COALESCE(m.content, '[Nessun messaggio]') as preview
                FROM sessions s
                LEFT JOIN messages m ON m.session_id = s.id AND m.role = 'user'
                GROUP BY s.id
                ORDER BY s.updated_at DESC
                LIMIT ?
            """, (limit,)) as cursor:
                return await cursor.fetchall()
