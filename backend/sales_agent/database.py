"""
backend/sales_agent/database.py — Isolated SQLite storage manager for the Autonomous AI Sales Voice Agent.
Completely separated from Drax AI's main database (data/drax.db).
Manages sales leads, explainable lead scores, and customer conversation history.
"""

import json
import os
import sqlite3
import threading
from typing import Optional, List, Dict, Any

from backend.sales_agent.schemas import (
    LeadCreate,
    LeadUpdate,
    LeadRead,
    ConversationTurnCreate,
    ConversationTurnRead,
)

# Default path points to data/sales_agent.db (completely separate from data/drax.db)
_DEFAULT_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data",
    "sales_agent.db",
)

_db_lock = threading.RLock()


def resolve_db_path(db_path: Optional[str] = None) -> str:
    """Resolve the active SQLite database path, prioritizing explicit parameter or environment variable."""
    if db_path:
        return db_path
    return os.getenv("SALES_DB_PATH", _DEFAULT_DB_PATH)


def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Create a thread-safe connection to the isolated sales SQLite database with row factory."""
    resolved = resolve_db_path(db_path)
    if resolved != ":memory:":
        os.makedirs(os.path.dirname(os.path.abspath(resolved)), exist_ok=True)

    conn = sqlite3.connect(resolved, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_sales_db(db_path: Optional[str] = None) -> None:
    """Initialize the sales database schema with tables and indexes."""
    with _db_lock:
        conn = get_connection(db_path)
        try:
            cursor = conn.cursor()

            # 1. Leads Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS sales_leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT UNIQUE NOT NULL,
                name TEXT DEFAULT NULL,
                email TEXT DEFAULT NULL,
                phone TEXT DEFAULT NULL,
                company TEXT DEFAULT NULL,
                role TEXT DEFAULT NULL,
                product_interest TEXT DEFAULT NULL,
                budget TEXT DEFAULT NULL,
                timeline TEXT DEFAULT NULL,
                authority TEXT DEFAULT NULL,
                need TEXT DEFAULT NULL,
                buying_intent TEXT DEFAULT 'unqualified',
                lead_score INTEGER DEFAULT 0,
                score_breakdown TEXT DEFAULT '{}',
                qualification_status TEXT DEFAULT 'in_progress',
                conversation_summary TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)

            # 2. Conversation History Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS sales_conversation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sales_leads(session_id) ON DELETE CASCADE
            );
            """)

            # 3. Indexes for fast retrieval
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_leads_session ON sales_leads(session_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_leads_status ON sales_leads(qualification_status);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_leads_score ON sales_leads(lead_score);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_session ON sales_conversation_history(session_id);")

            conn.commit()
        finally:
            conn.close()


def _row_to_lead(row: sqlite3.Row) -> LeadRead:
    """Convert an SQLite Row into a validated LeadRead Pydantic model."""
    data = dict(row)
    breakdown_raw = data.get("score_breakdown")
    if isinstance(breakdown_raw, str):
        try:
            data["score_breakdown"] = json.loads(breakdown_raw)
        except Exception:
            data["score_breakdown"] = {}
    elif not isinstance(breakdown_raw, dict):
        data["score_breakdown"] = {}

    return LeadRead(**data)


def create_lead(lead_data: LeadCreate, db_path: Optional[str] = None) -> LeadRead:
    """Insert a new lead record using safe parameterized SQL."""
    with _db_lock:
        conn = get_connection(db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO sales_leads (
                session_id, name, email, phone, company, role,
                product_interest, budget, timeline, authority, need,
                buying_intent, qualification_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                lead_data.session_id,
                lead_data.name,
                lead_data.email,
                lead_data.phone,
                lead_data.company,
                lead_data.role,
                lead_data.product_interest,
                lead_data.budget,
                lead_data.timeline,
                lead_data.authority,
                lead_data.need,
                lead_data.buying_intent,
                lead_data.qualification_status,
            ))
            conn.commit()
            lead_id = cursor.lastrowid

            cursor.execute("SELECT * FROM sales_leads WHERE id = ?;", (lead_id,))
            row = cursor.fetchone()
            if not row:
                raise RuntimeError(f"Failed to fetch newly created lead {lead_id}")
            return _row_to_lead(row)
        finally:
            conn.close()


def get_lead_by_id(lead_id: int, db_path: Optional[str] = None) -> Optional[LeadRead]:
    """Retrieve a lead by primary key ID."""
    with _db_lock:
        conn = get_connection(db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sales_leads WHERE id = ?;", (lead_id,))
            row = cursor.fetchone()
            return _row_to_lead(row) if row else None
        finally:
            conn.close()


def get_lead_by_session(session_id: str, db_path: Optional[str] = None) -> Optional[LeadRead]:
    """Retrieve a lead by its unique conversation session_id."""
    with _db_lock:
        conn = get_connection(db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sales_leads WHERE session_id = ?;", (session_id,))
            row = cursor.fetchone()
            return _row_to_lead(row) if row else None
        finally:
            conn.close()


def update_lead(session_id: str, lead_update: LeadUpdate, db_path: Optional[str] = None) -> Optional[LeadRead]:
    """Update fields of an existing lead dynamically using safe parameterized queries."""
    update_data = lead_update.model_dump(exclude_unset=True)
    if not update_data:
        return get_lead_by_session(session_id, db_path=db_path)

    # Serialize score_breakdown dictionary to JSON string for SQLite storage
    if "score_breakdown" in update_data and update_data["score_breakdown"] is not None:
        update_data["score_breakdown"] = json.dumps(update_data["score_breakdown"])

    with _db_lock:
        conn = get_connection(db_path)
        try:
            cursor = conn.cursor()

            set_clauses = [f"{field} = ?" for field in update_data.keys()]
            set_clauses.append("updated_at = CURRENT_TIMESTAMP")
            values = list(update_data.values())
            values.append(session_id)

            sql = f"UPDATE sales_leads SET {', '.join(set_clauses)} WHERE session_id = ?;"
            cursor.execute(sql, values)
            conn.commit()

            cursor.execute("SELECT * FROM sales_leads WHERE session_id = ?;", (session_id,))
            row = cursor.fetchone()
            return _row_to_lead(row) if row else None
        finally:
            conn.close()


def list_leads(
    status: Optional[str] = None,
    min_score: Optional[int] = None,
    limit: int = 50,
    offset: int = 0,
    db_path: Optional[str] = None,
) -> List[LeadRead]:
    """Retrieve paginated leads with optional status and score filtering."""
    with _db_lock:
        conn = get_connection(db_path)
        try:
            cursor = conn.cursor()

            query = "SELECT * FROM sales_leads WHERE 1=1"
            params: List[Any] = []

            if status:
                query += " AND qualification_status = ?"
                params.append(status)

            if min_score is not None:
                query += " AND lead_score >= ?"
                params.append(min_score)

            query += " ORDER BY id DESC LIMIT ? OFFSET ?;"
            params.extend([limit, offset])

            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [_row_to_lead(row) for row in rows]
        finally:
            conn.close()


def delete_lead(session_id: str, db_path: Optional[str] = None) -> bool:
    """Delete a lead and its associated conversation turns via cascade."""
    with _db_lock:
        conn = get_connection(db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM sales_leads WHERE session_id = ?;", (session_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()


def record_conversation_turn(turn: ConversationTurnCreate, db_path: Optional[str] = None) -> ConversationTurnRead:
    """Record a single message turn in the conversation history."""
    with _db_lock:
        conn = get_connection(db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO sales_conversation_history (session_id, role, content)
            VALUES (?, ?, ?);
            """, (turn.session_id, turn.role, turn.content))
            conn.commit()
            turn_id = cursor.lastrowid

            cursor.execute("SELECT * FROM sales_conversation_history WHERE id = ?;", (turn_id,))
            row = cursor.fetchone()
            if not row:
                raise RuntimeError(f"Failed to fetch newly recorded turn {turn_id}")

            return ConversationTurnRead(
                id=row["id"],
                session_id=row["session_id"],
                role=row["role"],
                content=row["content"],
                timestamp=str(row["timestamp"]),
            )
        finally:
            conn.close()


def get_conversation_history(
    session_id: str,
    limit: int = 100,
    db_path: Optional[str] = None,
) -> List[ConversationTurnRead]:
    """Retrieve full conversation message history in chronological order."""
    with _db_lock:
        conn = get_connection(db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT * FROM sales_conversation_history
            WHERE session_id = ?
            ORDER BY id ASC
            LIMIT ?;
            """, (session_id, limit))
            rows = cursor.fetchall()
            return [
                ConversationTurnRead(
                    id=row["id"],
                    session_id=row["session_id"],
                    role=row["role"],
                    content=row["content"],
                    timestamp=str(row["timestamp"]),
                )
                for row in rows
            ]
        finally:
            conn.close()
