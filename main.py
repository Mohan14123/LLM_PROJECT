"""
main.py
-------
FastAPI entry point for the A1 Cashless Pre-Auth Pipeline.
Provides endpoints to process pre-auth requests and view swagger docs.

Usage:
    uvicorn main:app --reload --port 8000
"""

from fastapi import FastAPI, HTTPException, Body, UploadFile, File
from pydantic import BaseModel, Field
from typing import Any, Dict
import tempfile
import os
import json
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

from intake import process_intake
from orchestration import run_pipeline
from schemas import SourceFormat

app = FastAPI(
    title="A1 Cashless Pre-Auth API",
    description="API for evaluating health insurance pre-authorisation requests via LangGraph rules engine.",
    version="1.0.0",
)

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

HISTORY_FILE = os.path.join(os.path.dirname(__file__), "data", "claim_history.json")


def _load_history() -> list[dict]:
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception as e:
        logger.error("Failed to load history: %s", e)
        return []


def _save_to_history(record: dict) -> None:
    try:
        history = _load_history()
        req_id = record.get("request_id") or record.get("extracted_request", {}).get("request_id")
        if not req_id and record.get("adjudication_metrics"):
            req_id = record["adjudication_metrics"].get("request_id")

        record["request_id"] = req_id

        # Deduplicate: replace previous entry with same id, or insert at head
        history = [h for h in history if (h.get("request_id") or h.get("extracted_request", {}).get("request_id")) != req_id]
        history.insert(0, record)
        history = history[:60]

        os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, default=str)
    except Exception as e:
        logger.error("Failed to save history record: %s", e)


@app.get("/api/v1/preauth/history", summary="Get Processed Claim History")
async def get_preauth_history():
    """Returns all historically processed claims in reverse chronological order."""
    return {"status": "success", "history": _load_history()}

class PreAuthPayload(BaseModel):
    """
    Standard JSON payload representing a hospital's pre-auth request.
    This structure should match the schema expected by the JSON intake handler.
    """
    request_id: str = Field(..., description="Unique ID for the request")
    submitted_at: str = Field(..., description="Submission date (YYYY-MM-DD)")
    source_format: str = Field(default="json")
    status: str = Field(default="pending")
    admission_date: str = Field(..., description="Expected admission date")
    patient: Dict[str, Any]
    policy: Dict[str, Any]
    hospital: Dict[str, Any]
    diagnosis: Dict[str, Any]
    procedure: Dict[str, Any]
    cost_estimate: Dict[str, Any]


@app.post("/api/v1/preauth/process", summary="Process a Pre-Auth Request")
async def process_preauth_request(payload: Dict[str, Any] = Body(
    ...,
    openapi_examples={
        "standard_stemi": {
            "summary": "Standard STEMI Emergency",
            "value": {
                "request_id": "123e4567-e89b-12d3-a456-426614174000",
                "submitted_at": "2025-06-01",
                "source_format": "json",
                "status": "pending",
                "admission_date": "2025-06-01",
                "patient": {
                    "patient_id": "123e4567-e89b-12d3-a456-426614174001",
                    "full_name": "Rajesh Kumar",
                    "age": 45,
                    "gender": "male",
                    "policy_number": "POL-ACTIVE-101"
                },
                "policy": {
                    "policy_number": "POL-ACTIVE-101",
                    "plan_type": "individual",
                    "sum_insured": "500000.00",
                    "policy_start_date": "2023-01-01",
                    "waiting_period_months": 0,
                    "sub_limits": {"limits": {"room_rent_per_day": "5000.00"}},
                    "co_pay_pct": "0.00"
                },
                "hospital": {
                    "hospital_id": "123e4567-e89b-12d3-a456-426614174002",
                    "name": "Synthetic Metro Hospital",
                    "city": "Mumbai",
                    "network_tier": "cashless_network",
                    "category": "multi_specialty"
                },
                "diagnosis": {
                    "icd10_code": "I21.0",
                    "description": "Acute STEMI",
                    "is_pre_existing": False
                },
                "procedure": {
                    "procedure_code": "PCI-001",
                    "description": "Primary PCI with DES",
                    "admission_type": "emergency"
                },
                "cost_estimate": {
                    "line_items": [
                        {"item": "Room Rent", "amount": "4000.00", "category": "room_rent"},
                        {"item": "Surgeon Fee", "amount": "80000.00", "category": "surgeon_fee"}
                    ],
                    "total_amount": "84000.00"
                }
            }
        }
    }
)):
    """
    Submit a JSON payload representing a hospital pre-authorization request.
    
    The payload runs through:
    1. Intake validation (Track 1)
    2. LangGraph state machine & rules engine (Track 2 & 3)
    
    Returns the final adjudication recommendation and reasoning narrative.
    """
    try:
        # 1. Process intake
        # The detect_format logic in process_intake will correctly handle dicts as JSON ("1")
        intake_result = process_intake(payload, format_override="1")
        
        if not intake_result.is_success:
            return {
                "status": "error",
                "message": "Intake validation failed.",
                "validation_errors": intake_result.validation_errors,
            }
            
        # We need to serialize the intake result into a dict to pass into the graph
        # Since IntakeResult is a Pydantic model (or dataclass), we use model_dump
        if hasattr(intake_result, "model_dump"):
            intake_dict = intake_result.model_dump()
        elif hasattr(intake_result, "dict"):
            intake_dict = intake_result.dict()
        else:
            intake_dict = intake_result.__dict__

        # 2. Run LangGraph pipeline
        final_state = run_pipeline(intake_dict)

        # 3. Format response
        resp = {
            "status": "success",
            "request_id": final_state.get("pre_auth_request", {}).get("request_id") or intake_dict.get("request", {}).get("request_id"),
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
            "adjudication_metrics": final_state.get("adjudication_result", {}),
            "latencies": final_state.get("node_latencies", {}),
        }
        _save_to_history(resp)
        return resp

    except Exception as e:
        import traceback
        return {
            "status": "error",
            "message": str(e),
            "traceback": traceback.format_exc(),
        }


from fastapi import Request

@app.post("/api/v1/preauth/text", summary="Process Free-Text Request")
async def process_text_request(request: Request):
    """
    Submit raw text (e.g., doctor's clinical notes) for pre-authorization.
    The system will use LLM extraction to populate the structured schema before running rules.
    """
    try:
        body_bytes = await request.body()
        text_content = body_bytes.decode('utf-8').strip()
        
        if not text_content:
            return {"status": "error", "message": "Text payload cannot be empty."}

        intake_result = process_intake(text_content, format_override="6")
        
        if not intake_result.is_success:
            return {
                "status": "error",
                "message": "Text extraction failed.",
                "validation_errors": getattr(intake_result, "validation_errors", [])
            }

        intake_dict = intake_result.model_dump() if hasattr(intake_result, "model_dump") else intake_result.__dict__
        final_state = run_pipeline(intake_dict)

        resp = {
            "status": "success",
            "request_id": intake_dict.get("request", {}).get("request_id"),
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
            "adjudication_metrics": final_state.get("adjudication_result", {}),
            "latencies": final_state.get("node_latencies", {}),
        }
        _save_to_history(resp)
        return resp
    except Exception as e:
        import traceback
        return {"status": "error", "message": str(e), "traceback": traceback.format_exc()}


@app.post("/api/v1/preauth/upload", summary="Process File Upload (PDF/Image/DOCX)")
async def process_file_upload(file: UploadFile = File(...)):
    """
    Upload a document (e.g., scanned PDF, image, DOCX) for pre-authorization processing.
    The system will auto-detect the format and run the correct extraction pipeline.
    """
    try:
        # Save file to a temporary location for the intake processor
        suffix = os.path.splitext(file.filename)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await file.read()
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

            intake_dict = intake_result.model_dump() if hasattr(intake_result, "model_dump") else intake_result.__dict__
            final_state = run_pipeline(intake_dict)

            resp = {
                "status": "success",
                "request_id": intake_dict.get("request", {}).get("request_id"),
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
                "adjudication_metrics": final_state.get("adjudication_result", {}),
                "latencies": final_state.get("node_latencies", {}),
            }
            _save_to_history(resp)
            return resp
        finally:
            os.unlink(tmp_path)
    except Exception as e:
        import traceback
        return {"status": "error", "message": str(e), "traceback": traceback.format_exc()}


@app.get("/health")
async def health_check():
    """Simple health check endpoint."""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
