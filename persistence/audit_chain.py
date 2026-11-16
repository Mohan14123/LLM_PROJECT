"""
persistence/audit_chain.py
---------------------------
Cryptographic SHA-256 tamper-evident hash chain for statutory IRDAI compliance
and verifiable decision audit trails.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Tuple, Optional


def compute_record_hash(prev_hash: str, request_id: str, event_type: str, payload_str: str, timestamp: str) -> str:
    """Compute SHA-256 digest binding previous hash, event metadata, and payload."""
    raw_bytes = f"{prev_hash}|{request_id}|{event_type}|{payload_str}|{timestamp}".encode("utf-8")
    return hashlib.sha256(raw_bytes).hexdigest()


def append_audit_event(
    conn: sqlite3.Connection,
    request_id: str,
    event_type: str,
    payload: dict[str, Any] | str,
    timestamp: Optional[str] = None
) -> dict[str, Any]:
    """Append a new event block to the immutable cryptographic audit chain.

    Args:
        conn: Open SQLite connection inside an active transaction.
        request_id: Pre-auth request ID.
        event_type: Classification (e.g. INTAKE_RECEIVED, ADJUDICATION_COMPLETED, REVIEWER_ACTION).
        payload: Event payload dictionary or string.
        timestamp: Optional ISO-8601 timestamp string (defaults to UTC now).

    Returns:
        The inserted audit block record dictionary.
    """
    cursor = conn.cursor()

    # Fetch latest hash tip in the chain
    cursor.execute("SELECT current_hash FROM audit_log ORDER BY log_id DESC LIMIT 1;")
    row = cursor.fetchone()
    prev_hash = row[0] if row else "0000000000000000000000000000000000000000000000000000000000000000"

    ts = timestamp or datetime.now(timezone.utc).isoformat()
    payload_str = json.dumps(payload, sort_keys=True, default=str) if isinstance(payload, dict) else str(payload)

    current_hash = compute_record_hash(prev_hash, request_id, event_type, payload_str, ts)

    cursor.execute("""
        INSERT INTO audit_log (request_id, event_type, event_payload, prev_hash, current_hash, timestamp)
        VALUES (?, ?, ?, ?, ?, ?);
    """, (request_id, event_type, payload_str, prev_hash, current_hash, ts))

    return {
        "log_id": cursor.lastrowid,
        "request_id": request_id,
        "event_type": event_type,
        "prev_hash": prev_hash,
        "current_hash": current_hash,
        "timestamp": ts,
    }


def verify_audit_chain(conn: sqlite3.Connection) -> Tuple[bool, int, Optional[str]]:
    """Verify integrity of the entire cryptographic audit trail from Genesis to tip.

    Returns:
        Tuple of (is_valid: bool, verified_count: int, error_message: Optional[str])
    """
    cursor = conn.cursor()
    cursor.execute("SELECT log_id, request_id, event_type, event_payload, prev_hash, current_hash, timestamp FROM audit_log ORDER BY log_id ASC;")
    records = cursor.fetchall()

    if not records:
        return True, 0, None

    expected_prev = "0000000000000000000000000000000000000000000000000000000000000000"

    for i, r in enumerate(records):
        log_id, req_id, ev_type, payload, prev_h, curr_h, ts = r

        # Genesis record check
        if i == 0 and ev_type == "GENESIS":
            expected_prev = curr_h
            continue

        # Check chain link
        if prev_h != expected_prev:
            return False, i, f"Hash link broken at log_id={log_id}: prev_hash '{prev_h[:12]}...' != expected '{expected_prev[:12]}...'"

        # Verify hash computation
        recomputed = compute_record_hash(prev_h, req_id, ev_type, payload, ts)
        if recomputed != curr_h:
            return False, i, f"Payload tampering detected at log_id={log_id}: current_hash '{curr_h[:12]}...' != recomputed '{recomputed[:12]}...'"

        expected_prev = curr_h

    return True, len(records), None


def export_external_anchor(
    conn: sqlite3.Connection,
    anchor_path: Optional[str] = None,
) -> dict[str, Any]:
    """Export an external anchor summary of the cryptographic audit chain.

    Anchors the current block height, chain tip hash, cumulative state digest,
    and UTC timestamp to prevent retroactive alteration or truncation attacks.
    """
    import os
    cursor = conn.cursor()
    cursor.execute("SELECT log_id, current_hash, timestamp FROM audit_log ORDER BY log_id DESC LIMIT 1;")
    row = cursor.fetchone()

    if not row:
        return {"block_height": 0, "tip_hash": None, "anchored_at": datetime.now(timezone.utc).isoformat()}

    block_height, tip_hash, last_ts = row

    # Calculate cumulative hash over all block hashes
    cursor.execute("SELECT current_hash FROM audit_log ORDER BY log_id ASC;")
    all_hashes = [r[0] for r in cursor.fetchall()]
    cumulative_digest = hashlib.sha256("".join(all_hashes).encode("utf-8")).hexdigest()

    anchor = {
        "version": "1.0",
        "block_height": block_height,
        "chain_tip_hash": tip_hash,
        "cumulative_digest": cumulative_digest,
        "anchored_at": datetime.now(timezone.utc).isoformat(),
        "last_block_timestamp": last_ts,
    }

    if anchor_path:
        os.makedirs(os.path.dirname(os.path.abspath(anchor_path)), exist_ok=True)
        with open(anchor_path, "w", encoding="utf-8") as f:
            json.dump(anchor, f, indent=2)

    return anchor

