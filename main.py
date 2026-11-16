"""
main.py
-------
FastAPI entry point for the A1 Cashless Pre-Auth Pipeline.
Provides endpoints to process pre-auth requests, human reviewer actions,
audit chain verification, and interactive API documentation.

Usage:
    uvicorn main:app --reload --port 8000
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from decimal import Decimal
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from fastapi import Body, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Load environment configuration (.env)
load_dotenv()

logger = logging.getLogger(__name__)

from intake import process_intake
from intake.pii_scrubber import PIIRedactingFilter
from orchestration import run_pipeline
from persistence import ClaimRepository
from schemas import SourceFormat

# Attach PII redaction filter to root logging
logging.getLogger().addFilter(PIIRedactingFilter())

app = FastAPI(
    title="A1 Cashless Pre-Auth API",
    description="Enterprise API for cashless health insurance pre-authorisation with neuro-symbolic adjudication and cryptographic audit trail.",
    version="2.0.0",
)

# ----------------------------------------------------------------------------
# CORS Security Hardening
# ----------------------------------------------------------------------------
allowed_origins_env = os.environ.get("ALLOWED_ORIGINS")
if allowed_origins_env:
    allowed_origins = [orig.strip() for orig in allowed_origins_env.split(",") if orig.strip()]
else:
    allowed_origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# ----------------------------------------------------------------------------
# Persistence Layer
# ----------------------------------------------------------------------------
repository = ClaimRepository()
HISTORY_FILE = os.path.join(os.path.dirname(__file__), "data", "claim_history.json")


def _save_record(record: dict, raw_payload: Any = None, source_format: str = "json") -> None:
    """Save record both to SQLite transactional repository and legacy JSON file."""
    try:
        req = record.get("extracted_request") or record.get("pre_auth_request")
        req_id = record.get("request_id")
        if req:
            repository.save_request(req, raw_payload=raw_payload, source_format=source_format)
            if "recommendation" in record:
                repository.save_decision(req_id, record)
    except Exception as e:
        logger.error("Failed to save claim to SQLite repository: %s", e)

    # Legacy JSON file persistence for UI compatibility
    try:
        history = []
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)

        req_id = record.get("request_id")
        history = [h for h in history if h.get("request_id") != req_id]
        history.insert(0, record)
        history = history[:60]

        os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, default=str)
    except Exception as e:
        logger.error("Failed to write legacy JSON history: %s", e)


# ----------------------------------------------------------------------------
# Request Models
# ----------------------------------------------------------------------------
class ReviewerActionPayload(BaseModel):
    reviewer_id: str = Field(..., description="ID or username of the medical reviewer.")
    approved_amount: Optional[float] = Field(default=None, description="Approved amount if approving or overriding.")
    notes: Optional[str] = Field(default="", description="Clinical reasoning or justification for the action.")


# ----------------------------------------------------------------------------
# API Endpoints
# ----------------------------------------------------------------------------
@app.get("/api/v1/preauth/history", summary="Get Processed Claim History")
async def get_preauth_history(limit: int = 50):
    """Returns historically processed claims in reverse chronological order from SQLite."""
    try:
        history = repository.get_history(limit=limit)
        return {"status": "success", "count": len(history), "history": history}
    except Exception as e:
        logger.error("Error fetching history from repository: %s", e)
        # Fallback to JSON history
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return {"status": "success", "history": json.load(f)}
        return {"status": "success", "history": []}


@app.delete("/api/v1/preauth/history", summary="Clear Claim History")
@app.post("/api/v1/preauth/history/clear", summary="Clear Claim History")
async def clear_preauth_history():
    """Clears all historical claims from the database and history JSON file."""
    try:
        repository.clear_history()
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump([], f)
        return {"status": "success", "message": "Claim history cleared successfully."}
    except Exception as e:
        logger.error("Error clearing history: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/preauth/audit/verify", summary="Verify SHA-256 Cryptographic Audit Chain")
async def verify_audit_trail():
    """Validates the complete SHA-256 hash chain from the Genesis block to the tip."""
    is_valid, record_count, error = repository.verify_integrity()
    return {
        "status": "success" if is_valid else "compromised",
        "is_tamper_free": is_valid,
        "verified_blocks": record_count,
        "error_detail": error,
    }


@app.post("/api/v1/preauth/process", summary="Process a Pre-Auth Request")
async def process_preauth_request(payload: Dict[str, Any] = Body(...)):
    """Process a structured JSON pre-authorization request through the dual-track pipeline."""
    try:
        intake_result = process_intake(payload, format_override="1")
        if not intake_result.is_success:
            return {
                "status": "error",
                "message": "Intake validation failed.",
                "validation_errors": intake_result.validation_errors,
            }

        intake_dict = intake_result.model_dump()
        final_state = run_pipeline(intake_dict)

        req_id = final_state.get("pre_auth_request", {}).get("request_id") or intake_dict.get("request", {}).get("request_id")

        resp = {
            "status": "success",
            "request_id": str(req_id),
            "extracted_request": intake_dict.get("request"),
            "pipeline_status": final_state.get("pipeline_status"),
            "recommendation": final_state.get("recommendation"),
            "confidence": final_state.get("confidence"),
            "consensus_status": final_state.get("consensus_status", "AGREED"),
            "discrepancy_report": final_state.get("discrepancy_report"),
            "rules_recommendation": final_state.get("adjudication_result", {}).get("recommendation"),
            "llm_recommendation": final_state.get("llm_recommendation"),
            "needs_escalation": final_state.get("needs_escalation"),
            "escalation_triggers": final_state.get("escalation_triggers", []),
            "reasoning": final_state.get("reasoning_narrative"),
            "adjudication_result": final_state.get("adjudication_result", {}),
            "latencies": final_state.get("node_latencies", {}),
            "total_latency": final_state.get("total_latency", 0.0),
            "llm_cost_inr": final_state.get("llm_cost_inr", 0.0),
        }
        _save_record(resp, raw_payload=payload, source_format="json")
        return resp

    except Exception as e:
        import traceback
        logger.error("Processing failed: %s\n%s", e, traceback.format_exc())
        return {"status": "error", "message": str(e), "traceback": traceback.format_exc()}


@app.post("/api/v1/preauth/text", summary="Process Free-Text Request")
async def process_text_request(request: Request):
    """Process unstructured clinical text narrative through NLP extraction and dual-track pipeline."""
    try:
        body_bytes = await request.body()
        text_content = body_bytes.decode("utf-8").strip()

        if not text_content:
            raise HTTPException(status_code=400, detail="Text payload cannot be empty.")

        intake_result = process_intake(text_content, format_override="6")
        if not intake_result.is_success:
            return {
                "status": "error",
                "message": "Clinical text extraction failed.",
                "validation_errors": getattr(intake_result, "validation_errors", [])
            }

        intake_dict = intake_result.model_dump()
        final_state = run_pipeline(intake_dict)

        req_id = intake_dict.get("request", {}).get("request_id")
        resp = {
            "status": "success",
            "request_id": str(req_id),
            "extracted_request": intake_dict.get("request"),
            "pipeline_status": final_state.get("pipeline_status"),
            "recommendation": final_state.get("recommendation"),
            "confidence": final_state.get("confidence"),
            "consensus_status": final_state.get("consensus_status", "AGREED"),
            "discrepancy_report": final_state.get("discrepancy_report"),
            "rules_recommendation": final_state.get("adjudication_result", {}).get("recommendation"),
            "llm_recommendation": final_state.get("llm_recommendation"),
            "needs_escalation": final_state.get("needs_escalation"),
            "escalation_triggers": final_state.get("escalation_triggers", []),
            "reasoning": final_state.get("reasoning_narrative"),
            "adjudication_result": final_state.get("adjudication_result", {}),
            "latencies": final_state.get("node_latencies", {}),
        }
        _save_record(resp, raw_payload=text_content, source_format="text")
        return resp
    except Exception as e:
        import traceback
        logger.error("Text processing failed: %s\n%s", e, traceback.format_exc())
        return {"status": "error", "message": str(e), "traceback": traceback.format_exc()}


@app.post("/api/v1/preauth/upload", summary="Process File Upload (PDF/Image/DOCX)")
async def process_file_upload(file: UploadFile = File(...)):
    """Upload and process document with magic-byte security checks and file size limits."""
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB limit
    content = await file.read()

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds maximum allowable size of {MAX_FILE_SIZE // (1024 * 1024)} MB."
        )

    # Magic byte validation
    filename_lower = (file.filename or "").lower()
    is_valid_format = False

    if content.startswith(b"%PDF-"):
        is_valid_format = True
    elif content.startswith(b"\x89PNG\r\n\x1a\n"):
        is_valid_format = True
    elif content.startswith(b"\xff\xd8\xff"):
        is_valid_format = True
    elif content.startswith(b"PK\x03\x04") and filename_lower.endswith(".docx"):
        is_valid_format = True

    if not is_valid_format:
        raise HTTPException(
            status_code=400,
            detail="File content does not match allowed types (PDF, JPEG, PNG, DOCX)."
        )

    suffix = os.path.splitext(file.filename)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        intake_result = process_intake(tmp_path, original_filename=file.filename)
        if not intake_result.is_success:
            return {
                "status": "error",
                "message": f"Extraction failed for file {file.filename}.",
                "validation_errors": getattr(intake_result, "validation_errors", [])
            }

        intake_dict = intake_result.model_dump()
        final_state = run_pipeline(intake_dict)

        req_id = intake_dict.get("request", {}).get("request_id")
        resp = {
            "status": "success",
            "request_id": str(req_id),
            "extracted_request": intake_dict.get("request"),
            "pipeline_status": final_state.get("pipeline_status"),
            "recommendation": final_state.get("recommendation"),
            "confidence": final_state.get("confidence"),
            "consensus_status": final_state.get("consensus_status", "AGREED"),
            "discrepancy_report": final_state.get("discrepancy_report"),
            "rules_recommendation": final_state.get("adjudication_result", {}).get("recommendation"),
            "llm_recommendation": final_state.get("llm_recommendation"),
            "needs_escalation": final_state.get("needs_escalation"),
            "escalation_triggers": final_state.get("escalation_triggers", []),
            "reasoning": final_state.get("reasoning_narrative"),
            "adjudication_result": final_state.get("adjudication_result", {}),
            "latencies": final_state.get("node_latencies", {}),
        }
        _save_record(resp, raw_payload=f"File: {file.filename} ({len(content)} bytes)", source_format=suffix.lstrip("."))
        return resp
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


# ----------------------------------------------------------------------------
# Reviewer Role-Based Access Control (RBAC) & Endpoints
# ----------------------------------------------------------------------------
def _check_reviewer_role(request: Request, allowed_roles: set[str]) -> str:
    """Enforce role-based access control for medical and administrative reviewer endpoints."""
    role = request.headers.get("X-Reviewer-Role", "underwriter").strip().lower()
    if role not in allowed_roles:
        raise HTTPException(
            status_code=403,
            detail=f"Reviewer role '{role}' is not authorized for this operation. Allowed roles: {sorted(list(allowed_roles))}"
        )
    return role


@app.get("/api/v1/preauth/audit/anchor", summary="Export External Anchor for Audit Trail")
async def get_audit_anchor():
    """Generates an external cryptographic anchor state for regulatory anchoring."""
    anchor = repository.export_anchor()
    return {"status": "success", "anchor": anchor}


@app.post("/api/v1/preauth/{request_id}/review/approve", summary="Human Reviewer Approval Sign-off")
async def review_approve(request_id: str, payload: ReviewerActionPayload, request: Request):
    """Medical reviewer grants formal approval sign-off for a pre-auth recommendation."""
    role = _check_reviewer_role(request, {"underwriter", "supervisor", "medical_officer"})
    if not repository.get_request(request_id):
        # Insert minimal placeholder if request was processed before DB schema
        repository.save_request({"request_id": request_id, "submitted_at": "UNKNOWN", "cost_estimate": {"total_amount": 0}})

    action_id = repository.record_reviewer_action(
        request_id=request_id,
        reviewer_id=payload.reviewer_id,
        action="APPROVE",
        approved_amount=payload.approved_amount,
        notes=payload.notes,
    )
    return {
        "status": "success",
        "action_id": action_id,
        "request_id": request_id,
        "action": "APPROVE",
        "reviewer_role": role,
        "message": f"Pre-authorisation {request_id} signed off by reviewer {payload.reviewer_id} ({role})."
    }


@app.post("/api/v1/preauth/{request_id}/review/reject", summary="Human Reviewer Rejection")
async def review_reject(request_id: str, payload: ReviewerActionPayload, request: Request):
    """Medical reviewer issues formal rejection for a pre-auth recommendation."""
    role = _check_reviewer_role(request, {"underwriter", "supervisor", "medical_officer"})
    if not repository.get_request(request_id):
        repository.save_request({"request_id": request_id, "submitted_at": "UNKNOWN", "cost_estimate": {"total_amount": 0}})

    action_id = repository.record_reviewer_action(
        request_id=request_id,
        reviewer_id=payload.reviewer_id,
        action="REJECT",
        approved_amount=0.0,
        notes=payload.notes,
    )
    return {
        "status": "success",
        "action_id": action_id,
        "request_id": request_id,
        "action": "REJECT",
        "reviewer_role": role,
        "message": f"Pre-authorisation {request_id} rejected by reviewer {payload.reviewer_id} ({role})."
    }


@app.post("/api/v1/preauth/{request_id}/review/override", summary="Human Reviewer Override")
async def review_override(request_id: str, payload: ReviewerActionPayload, request: Request):
    """Medical reviewer overrides the automated pipeline recommendation."""
    role = _check_reviewer_role(request, {"supervisor", "senior_underwriter", "underwriter"})
    if payload.approved_amount is None:
        raise HTTPException(status_code=400, detail="Approved amount is required when overriding.")

    if not repository.get_request(request_id):
        repository.save_request({"request_id": request_id, "submitted_at": "UNKNOWN", "cost_estimate": {"total_amount": 0}})

    action_id = repository.record_reviewer_action(
        request_id=request_id,
        reviewer_id=payload.reviewer_id,
        action="OVERRIDE",
        approved_amount=payload.approved_amount,
        notes=payload.notes,
    )
    return {
        "status": "success",
        "action_id": action_id,
        "request_id": request_id,
        "action": "OVERRIDE",
        "reviewer_role": role,
        "message": f"Pre-authorisation {request_id} overridden by reviewer {payload.reviewer_id} ({role})."
    }


@app.post("/api/v1/preauth/{request_id}/review/request-docs", summary="Request Additional Medical Documents")
async def review_request_docs(request_id: str, payload: ReviewerActionPayload, request: Request):
    """Medical reviewer places pre-authorisation in queried state requesting further documentation."""
    role = _check_reviewer_role(request, {"underwriter", "supervisor", "medical_officer"})
    if not repository.get_request(request_id):
        repository.save_request({"request_id": request_id, "submitted_at": "UNKNOWN", "cost_estimate": {"total_amount": 0}})

    action_id = repository.record_reviewer_action(
        request_id=request_id,
        reviewer_id=payload.reviewer_id,
        action="REQUEST_DOCS",
        notes=payload.notes,
    )
    return {
        "status": "success",
        "action_id": action_id,
        "request_id": request_id,
        "action": "REQUEST_DOCS",
        "message": f"Clarifications/documentation requested for {request_id}."
    }


@app.get("/health")
async def health_check():
    """Liveness probe with database and LLM status."""
    is_valid, count, _ = repository.verify_integrity()
    return {
        "status": "healthy",
        "audit_chain_valid": is_valid,
        "audit_blocks_count": count,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
