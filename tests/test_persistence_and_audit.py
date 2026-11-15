"""
tests/test_persistence_and_audit.py
-----------------------------------
Unit and integration tests for SQLite persistence, transactional operations,
and SHA-256 cryptographic audit chain tamper-evidence.
"""

from __future__ import annotations

import tempfile
import sqlite3
import pytest

from persistence import ClaimRepository, init_db, get_db_connection


@pytest.fixture
def temp_repo():
    with tempfile.NamedTemporaryFile(suffix=".db") as f:
        db_path = f.name
    repo = ClaimRepository(db_path=db_path)
    return repo, db_path


class TestPersistenceAndAuditChain:
    def test_genesis_block_initialization(self, temp_repo):
        repo, db_path = temp_repo
        is_valid, count, err = repo.verify_integrity()
        assert is_valid is True
        assert count == 1  # Genesis block present
        assert err is None

    def test_save_request_and_audit_link(self, temp_repo):
        repo, _ = temp_repo
        req = {
            "request_id": "REQ-PERSIST-101",
            "submitted_at": "2026-11-15",
            "patient": {"full_name": "Deepak Kumar", "age": 42, "gender": "male"},
            "policy": {"policy_number": "POL-999"},
            "hospital": {"name": "Metro Hospital"},
            "diagnosis": {"description": "Appendicitis"},
            "procedure": {"description": "Appendectomy"},
            "cost_estimate": {"total_amount": "50000.00"},
        }
        repo.save_request(req, source_format="json")

        fetched = repo.get_request("REQ-PERSIST-101")
        assert fetched is not None
        assert fetched["patient_name"] == "Deepak Kumar"
        assert fetched["total_claimed"] == 50000.0

        is_valid, count, _ = repo.verify_integrity()
        assert is_valid is True
        assert count == 2  # Genesis + REQUEST_INGESTED

    def test_full_claim_decision_and_reviewer_chain(self, temp_repo):
        repo, _ = temp_repo
        req = {
            "request_id": "REQ-PERSIST-202",
            "submitted_at": "2026-11-15",
            "patient": {"full_name": "Meera Sen", "age": 55, "gender": "female"},
            "policy": {"policy_number": "POL-888"},
            "cost_estimate": {"total_amount": "80000.00"},
        }
        repo.save_request(req)

        pipeline_res = {
            "recommendation": "RECOMMEND_AUTHORISE",
            "confidence": 0.90,
            "consensus_status": "AGREED",
            "needs_escalation": False,
            "adjudication_result": {
                "recommendation": "RECOMMEND_AUTHORISE",
                "total_claimed": 80000.0,
                "total_approved": 75000.0,
                "total_deducted": 5000.0,
            },
        }
        repo.save_decision("REQ-PERSIST-202", pipeline_res)

        repo.record_reviewer_action(
            request_id="REQ-PERSIST-202",
            reviewer_id="DR_GUPTA",
            action="APPROVE",
            approved_amount=75000.0,
            notes="Case approved after secondary audit."
        )

        is_valid, count, _ = repo.verify_integrity()
        assert is_valid is True
        assert count == 4  # Genesis + Ingest + Decision + Reviewer Action

    def test_tamper_detection_in_audit_chain(self, temp_repo):
        repo, db_path = temp_repo
        req = {
            "request_id": "REQ-TAMPER-001",
            "submitted_at": "2026-11-15",
            "patient": {"full_name": "Siddharth Rao"},
            "policy": {"policy_number": "POL-TAMPER"},
            "cost_estimate": {"total_amount": "10000.00"},
        }
        repo.save_request(req)

        # Directly tamper with SQLite audit_log record
        conn = sqlite3.connect(db_path)
        conn.execute("UPDATE audit_log SET event_payload = 'TAMPERED_DATA' WHERE request_id = 'REQ-TAMPER-001';")
        conn.commit()
        conn.close()

        is_valid, _, err = repo.verify_integrity()
        assert is_valid is False
        assert "tampering detected" in err.lower()
