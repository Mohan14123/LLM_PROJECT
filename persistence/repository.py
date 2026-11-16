"""
persistence/repository.py
-------------------------
Repository data access layer handling transactional persistence of requests,
decisions, reviewer actions, and audit chain updates.
"""

from __future__ import annotations

import json
import logging
import os
from decimal import Decimal
from typing import Any, Optional

from persistence.database import get_db_connection, init_db
from persistence.audit_chain import append_audit_event, verify_audit_chain

logger = logging.getLogger(__name__)


class ClaimRepository:
    """Transactional repository for pre-auth claims persistence."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        self.db_path = db_path
        init_db(self.db_path)

    def save_request(self, pre_auth_request: dict[str, Any], raw_payload: Any = None, source_format: str = "json") -> str:
        """Persist a parsed pre-authorisation request and record audit block."""
        req_id = str(pre_auth_request.get("request_id", ""))
        patient = pre_auth_request.get("patient", {})
        policy = pre_auth_request.get("policy", {})
        hospital = pre_auth_request.get("hospital", {})
        diagnosis = pre_auth_request.get("diagnosis", {})
        procedure = pre_auth_request.get("procedure", {})
        cost = pre_auth_request.get("cost_estimate", {})

        total_claimed = float(cost.get("total_amount", 0.0))

        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO preauth_requests (
                    request_id, submitted_at, source_format,
                    patient_name, patient_age, patient_gender, policy_number,
                    hospital_name, diagnosis_code, diagnosis_description,
                    procedure_code, procedure_description, total_claimed,
                    raw_payload
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                req_id,
                str(pre_auth_request.get("submitted_at", "")),
                str(source_format),
                str(patient.get("full_name", "")),
                patient.get("age"),
                str(patient.get("gender", "")),
                str(policy.get("policy_number", "")),
                str(hospital.get("name", "")),
                str(diagnosis.get("icd10_code", "")),
                str(diagnosis.get("description", "")),
                str(procedure.get("procedure_code", "")),
                str(procedure.get("description", "")),
                total_claimed,
                json.dumps(raw_payload, default=str) if raw_payload is not None else None,
            ))

            append_audit_event(
                conn,
                request_id=req_id,
                event_type="REQUEST_INGESTED",
                payload={
                    "policy_number": policy.get("policy_number"),
                    "total_claimed": total_claimed,
                    "source_format": source_format,
                }
            )

        logger.info("Saved request %s to database.", req_id)
        return req_id

    def save_decision(self, request_id: str, pipeline_result: dict[str, Any]) -> int:
        """Persist pipeline adjudication decision and record audit block."""
        adj = pipeline_result.get("adjudication_result", {})
        rec = str(pipeline_result.get("recommendation", "UNKNOWN"))
        conf = float(pipeline_result.get("confidence", 0.0))
        rules_rec = str(adj.get("recommendation", ""))
        llm_rec = str(pipeline_result.get("llm_recommendation", ""))
        consensus = str(pipeline_result.get("consensus_status", "AGREED"))

        claimed = float(adj.get("total_claimed", 0.0))
        approved = float(adj.get("total_approved", 0.0))
        deducted = float(adj.get("total_deducted", 0.0))

        needs_esc = 1 if pipeline_result.get("needs_escalation", False) else 0
        triggers = json.dumps(pipeline_result.get("escalation_triggers", []))
        reasoning = str(pipeline_result.get("reasoning_narrative", ""))
        deductions_json = json.dumps(adj.get("deductions", []), default=str)
        retrieved_json = json.dumps(pipeline_result.get("retrieved_clauses", []), default=str)

        latencies = pipeline_result.get("node_latencies", {})
        tot_latency = float(pipeline_result.get("total_latency", sum(latencies.values()) if latencies else 0.0))
        cost_inr = float(pipeline_result.get("llm_cost_inr", 0.0))

        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO adjudication_decisions (
                    request_id, recommendation, confidence,
                    rules_recommendation, llm_recommendation, consensus_status,
                    total_claimed, total_approved, total_deducted,
                    needs_escalation, escalation_triggers, reasoning,
                    deductions_json, retrieved_clauses_json,
                    latency_seconds, cost_inr
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                request_id, rec, conf,
                rules_rec, llm_rec, consensus,
                claimed, approved, deducted,
                needs_esc, triggers, reasoning,
                deductions_json, retrieved_json,
                tot_latency, cost_inr
            ))
            decision_id = cursor.lastrowid

            # Model execution metadata for regulatory traceability
            model_provider = str(pipeline_result.get("model_provider") or os.environ.get("LLM_PROVIDER", "openai_compatible"))
            execution_mode = str(pipeline_result.get("execution_mode") or os.environ.get("LLM_EXECUTION_MODE", "FALLBACK_ONLY"))
            model_name = str(pipeline_result.get("model_name") or os.environ.get("OPENAI_MODEL", "gpt-4o"))
            prompt_version = str(pipeline_result.get("prompt_version", "v2.1"))

            append_audit_event(
                conn,
                request_id=request_id,
                event_type="DECISION_ADJUDICATED",
                payload={
                    "recommendation": rec,
                    "approved_amount": approved,
                    "consensus_status": consensus,
                    "needs_escalation": bool(needs_esc),
                    "model_provider": model_provider,
                    "execution_mode": execution_mode,
                    "model_name": model_name,
                    "prompt_version": prompt_version,
                }
            )

        logger.info("Saved decision #%d for request %s.", decision_id, request_id)
        return decision_id

    def export_anchor(self, anchor_path: Optional[str] = None) -> dict[str, Any]:
        """Export external anchor summary of the audit chain."""
        from persistence.audit_chain import export_external_anchor
        with get_db_connection(self.db_path) as conn:
            return export_external_anchor(conn, anchor_path=anchor_path)

    def get_request(self, request_id: str) -> Optional[dict[str, Any]]:
        """Fetch pre-authorisation request by ID."""
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM preauth_requests WHERE request_id = ?;", (request_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def record_reviewer_action(
        self,
        request_id: str,
        reviewer_id: str,
        action: str,
        approved_amount: Optional[float] = None,
        notes: Optional[str] = None
    ) -> int:
        """Record a human reviewer's final sign-off or override action."""
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO reviewer_actions (request_id, reviewer_id, action, approved_amount, notes)
                VALUES (?, ?, ?, ?, ?);
            """, (request_id, reviewer_id, action.upper(), approved_amount, notes or ""))
            action_id = cursor.lastrowid

            append_audit_event(
                conn,
                request_id=request_id,
                event_type="REVIEWER_ACTION",
                payload={
                    "reviewer_id": reviewer_id,
                    "action": action.upper(),
                    "approved_amount": approved_amount,
                    "notes": notes,
                }
            )

        logger.info("Recorded reviewer action #%d (%s) for request %s.", action_id, action, request_id)
        return action_id

    def get_history(self, limit: int = 50) -> list[dict[str, Any]]:
        """Retrieve recent pre-auth decisions with request and reviewer details."""
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    r.request_id, r.submitted_at, r.source_format,
                    r.patient_name, r.patient_age, r.patient_gender, r.policy_number,
                    r.hospital_name, r.diagnosis_description, r.procedure_description,
                    r.total_claimed,
                    d.recommendation, d.confidence, d.consensus_status,
                    d.total_approved, d.total_deducted, d.needs_escalation,
                    d.escalation_triggers, d.reasoning, d.latency_seconds, d.cost_inr,
                    d.created_at as adjudicated_at
                FROM preauth_requests r
                LEFT JOIN adjudication_decisions d ON r.request_id = d.request_id
                ORDER BY r.created_at DESC
                LIMIT ?;
            """, (limit,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def verify_integrity(self) -> tuple[bool, int, Optional[str]]:
        """Verify the entire SHA-256 hash chain audit trail."""
        with get_db_connection(self.db_path) as conn:
            return verify_audit_chain(conn)
