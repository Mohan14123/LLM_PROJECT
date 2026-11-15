"""
persistence/database.py
-----------------------
SQLite database connection and schema initialization with WAL mode for concurrency
and transactional guarantees.
"""

from __future__ import annotations

import os
import sqlite3
import logging
from typing import Generator
from contextlib import contextmanager

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "claims.db"
)


def get_db_path() -> str:
    """Return database file path from environment or default."""
    return os.environ.get("DATABASE_PATH", DEFAULT_DB_PATH)


@contextmanager
def get_db_connection(db_path: str | None = None) -> Generator[sqlite3.Connection, None, None]:
    """Provide a transactional SQLite connection with WAL mode and foreign keys enabled."""
    path = db_path or get_db_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path, timeout=30.0)
    conn.row_factory = sqlite3.Row
    try:
        # Enable WAL mode for concurrent reads/writes and enforce foreign keys
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error("Database transaction rolled back due to error: %s", e)
        raise
    finally:
        conn.close()


def init_db(db_path: str | None = None) -> None:
    """Initialize database tables, indexes, and genesis audit record if not present."""
    target_path = db_path or get_db_path()
    with get_db_connection(target_path) as conn:
        cursor = conn.cursor()

        # 1. Pre-Auth Requests Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS preauth_requests (
                request_id TEXT PRIMARY KEY,
                submitted_at TEXT NOT NULL,
                source_format TEXT NOT NULL,
                patient_name TEXT,
                patient_age INTEGER,
                patient_gender TEXT,
                policy_number TEXT NOT NULL,
                hospital_name TEXT,
                diagnosis_code TEXT,
                diagnosis_description TEXT,
                procedure_code TEXT,
                procedure_description TEXT,
                total_claimed REAL NOT NULL,
                raw_payload TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 2. Adjudication Decisions Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS adjudication_decisions (
                decision_id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id TEXT NOT NULL,
                recommendation TEXT NOT NULL,
                confidence REAL NOT NULL,
                rules_recommendation TEXT,
                llm_recommendation TEXT,
                consensus_status TEXT NOT NULL,
                total_claimed REAL NOT NULL,
                total_approved REAL NOT NULL,
                total_deducted REAL NOT NULL,
                needs_escalation INTEGER NOT NULL,
                escalation_triggers TEXT,
                reasoning TEXT,
                deductions_json TEXT,
                retrieved_clauses_json TEXT,
                latency_seconds REAL,
                cost_inr REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (request_id) REFERENCES preauth_requests(request_id)
            );
        """)

        # 3. Reviewer Actions Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reviewer_actions (
                action_id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id TEXT NOT NULL,
                reviewer_id TEXT NOT NULL,
                action TEXT NOT NULL, -- 'APPROVE', 'REJECT', 'OVERRIDE', 'REQUEST_DOCS'
                approved_amount REAL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (request_id) REFERENCES preauth_requests(request_id)
            );
        """)

        # 4. Cryptographic Audit Log Table (SHA-256 Hash Chain)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                event_payload TEXT NOT NULL,
                prev_hash TEXT NOT NULL,
                current_hash TEXT NOT NULL,
                timestamp TEXT NOT NULL
            );
        """)

        # Indexes for query performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_requests_policy ON preauth_requests(policy_number);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_decisions_req ON adjudication_decisions(request_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_reviewer_req ON reviewer_actions(request_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_req ON audit_log(request_id);")

        # Initialize Genesis block in audit log if empty
        cursor.execute("SELECT COUNT(*) FROM audit_log;")
        if cursor.fetchone()[0] == 0:
            import hashlib
            genesis_payload = "GENESIS_BLOCK: Cashless Pre-Authorisation Audit Trail Initialized"
            genesis_ts = "2026-01-01T00:00:00Z"
            genesis_hash = hashlib.sha256(f"0000000000000000000000000000000000000000000000000000000000000000:{genesis_payload}:{genesis_ts}".encode()).hexdigest()
            cursor.execute("""
                INSERT INTO audit_log (request_id, event_type, event_payload, prev_hash, current_hash, timestamp)
                VALUES ('SYSTEM', 'GENESIS', ?, '0000000000000000000000000000000000000000000000000000000000000000', ?, ?);
            """, (genesis_payload, genesis_hash, genesis_ts))

        logger.info("Database initialized successfully at %s", target_path)
