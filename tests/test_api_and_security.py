"""
tests/test_api_and_security.py
------------------------------
Unit tests for FastAPI endpoints, reviewer action workflows, and security safeguards
(magic byte checking, size bounds, and audit verification).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestAPIAndReviewerEndpoints:
    def test_health_check_returns_ok_and_audit_status(self, client):
        res = client.get("/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "healthy"
        assert "audit_chain_valid" in data

    def test_audit_verify_endpoint(self, client):
        res = client.get("/api/v1/preauth/audit/verify")
        assert res.status_code == 200
        data = res.json()
        assert data["is_tamper_free"] is True
        assert data["verified_blocks"] >= 1

    def test_reviewer_approval_workflow(self, client):
        req_id = "TEST-API-APPROVAL-01"
        res = client.post(f"/api/v1/preauth/{req_id}/review/approve", json={
            "reviewer_id": "DR_MENON",
            "approved_amount": 50000.0,
            "notes": "Verified clinical necessity and tariff rates."
        })
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert data["action"] == "APPROVE"

    def test_reviewer_override_workflow_requires_amount(self, client):
        req_id = "TEST-API-OVERRIDE-01"
        # Missing approved_amount
        res = client.post(f"/api/v1/preauth/{req_id}/review/override", json={
            "reviewer_id": "DR_MENON",
            "notes": "Overriding without amount"
        })
        assert res.status_code == 400

        # With approved_amount
        res = client.post(f"/api/v1/preauth/{req_id}/review/override", json={
            "reviewer_id": "DR_MENON",
            "approved_amount": 42000.0,
            "notes": "Emergency exception override"
        })
        assert res.status_code == 200
        assert res.json()["action"] == "OVERRIDE"

    def test_reviewer_rbac_unauthorized_role_rejected(self, client):
        req_id = "TEST-API-RBAC-01"
        # Auditor role is read-only and cannot approve
        res = client.post(
            f"/api/v1/preauth/{req_id}/review/approve",
            json={"reviewer_id": "AUDITOR_01", "approved_amount": 10000.0, "notes": "Auditor attempt"},
            headers={"X-Reviewer-Role": "auditor"}
        )
        assert res.status_code == 403
        assert "not authorized" in res.json()["detail"]

    def test_external_audit_anchor_export(self, client):
        res = client.get("/api/v1/preauth/audit/anchor")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        anchor = data["anchor"]
        assert "chain_tip_hash" in anchor
        assert "cumulative_digest" in anchor
        assert anchor["block_height"] >= 1

    def test_pii_redaction_scrubber(self):
        from intake.pii_scrubber import scrub_pii
        text = "Patient phone is +91-9876543210 and Aadhaar is 1234 5678 9012 with email test@carehospital.com"
        redacted = scrub_pii(text)
        assert "1234 5678 9012" not in redacted
        assert "XXXX-XXXX-9012" in redacted
        assert "9876543210" not in redacted
        assert "[EMAIL_REDACTED]" in redacted


class TestUploadSecuritySafeguards:
    def test_rejects_unallowed_binary_formats(self, client):
        res = client.post("/api/v1/preauth/upload", files={
            "file": ("payload.exe", b"MZ\x90\x00\x03\x00\x00\x00", "application/octet-stream")
        })
        assert res.status_code == 400
        assert "allowed types" in res.json()["detail"]

    def test_rejects_oversized_file(self, client):
        # 11 MB fake payload
        large_bytes = b"%PDF-" + b"0" * (11 * 1024 * 1024)
        res = client.post("/api/v1/preauth/upload", files={
            "file": ("giant.pdf", large_bytes, "application/pdf")
        })
        assert res.status_code == 413
