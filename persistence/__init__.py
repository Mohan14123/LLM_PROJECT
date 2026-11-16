"""
persistence package
-------------------
Transactional SQLite persistence and SHA-256 cryptographic audit chain.
"""

from persistence.database import get_db_connection, init_db, get_db_path
from persistence.audit_chain import append_audit_event, verify_audit_chain, export_external_anchor
from persistence.repository import ClaimRepository

__all__ = [
    "get_db_connection",
    "init_db",
    "get_db_path",
    "append_audit_event",
    "verify_audit_chain",
    "export_external_anchor",
    "ClaimRepository",
]
