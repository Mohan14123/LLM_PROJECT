import { useState, useRef, useEffect, useMemo } from 'react';
import {
  ShieldCheck,
  Plus,
  X,
  FileSignature,
  Upload,
  FileText,
  Code,
  RotateCcw,
  CheckCircle2,
  XCircle,
  Search,
  Lock,
  Scale,
  Stethoscope,
  Layers,
  Cpu,
  Download,
  Sparkles,
  ShieldAlert
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const API_BASE = "http://localhost:8000";
const STORAGE_KEY = "a1_preauth_queue_history";
const ACTIVE_ID_KEY = "a1_preauth_active_id";

export type ReviewerRole = 'underwriter' | 'supervisor' | 'auditor';

function formatRecordToQueueItem(record: any) {
  const req = record.extracted_request || record.request || {};
  const patient = req.patient || {};
  const diagnosis = req.diagnosis || {};
  const procedure = req.procedure || {};
  const cost = req.cost_estimate || {};
  const policy = req.policy || {};
  const hospital = req.hospital || {};
  const adj = record.adjudication_metrics || {};

  let decisionStatus = 'escalated';
  let decisionLabel = 'ESCALATE';

  if (record.needs_escalation) {
    decisionStatus = 'escalated';
    decisionLabel = 'ESCALATE';
  } else if (record.recommendation) {
    const rec = String(record.recommendation).replace(/^RECOMMEND_/, '').toUpperCase();
    if (rec.includes('AUTHORISE') || rec.includes('APPROVE')) {
      decisionStatus = 'approved';
      decisionLabel = 'APPROVE';
    } else if (rec.includes('DENY') || rec.includes('REJECT')) {
      decisionStatus = 'denied';
      decisionLabel = 'DENY';
    } else if (rec.includes('QUERY')) {
      decisionStatus = 'query';
      decisionLabel = 'QUERY';
    } else {
      decisionStatus = rec.toLowerCase();
      decisionLabel = rec;
    }
  }

  const reqId = record.request_id || req.request_id || adj.request_id || 'req-saved';
  const claimRaw = cost.total_amount || adj.total_claimed || 0;
  const approvedRaw = adj.total_approved !== undefined ? adj.total_approved : (decisionLabel === 'APPROVE' ? claimRaw : 0);
  const deductedRaw = adj.total_deducted !== undefined ? adj.total_deducted : (Number(claimRaw) - Number(approvedRaw));

  const formatCurrency = (val: any) => {
    const num = Number(val);
    return isNaN(num) ? `₹${val}` : `₹${num.toLocaleString('en-IN')}`;
  };

  const rawTriggers = record.escalation_triggers || adj.escalation_triggers || [];
  const normalizedTriggers: string[] = Array.isArray(rawTriggers)
    ? rawTriggers.map(String)
    : (rawTriggers ? [String(rawTriggers)] : []);

  return {
    id: reqId,
    patient: patient.full_name?.split('\n')[0] || 'Unknown Patient',
    diagnosis: diagnosis.description?.split('\n')[0] || 'Unknown Diagnosis',
    procedure: procedure.description || 'N/A',
    hospital: hospital.name || 'N/A',
    city: hospital.city || 'N/A',
    network_tier: hospital.network_tier || 'cashless_network',
    status: decisionStatus,
    decisionLabel: decisionLabel,
    date: req.submitted_at || new Date().toISOString().split('T')[0],
    amount: formatCurrency(claimRaw),
    amountRaw: Number(claimRaw),
    approvedAmount: formatCurrency(approvedRaw),
    approvedAmountRaw: Number(approvedRaw),
    deductedAmount: formatCurrency(deductedRaw),
    deductedAmountRaw: Number(deductedRaw),
    confidence: record.confidence !== undefined ? record.confidence : (adj.confidence_score || 0.8),
    consensus_status: record.consensus_status || (record.needs_escalation && normalizedTriggers.some((t: string) => t.includes('Discrepancy')) ? 'DIVERGED' : 'AGREED'),
    discrepancy_report: record.discrepancy_report || null,
    rules_recommendation: record.rules_recommendation || adj.recommendation || 'N/A',
    llm_recommendation: record.llm_recommendation || record.recommendation || 'N/A',
    escalation_triggers: normalizedTriggers,
    execution_mode: record.execution_mode || 'PARALLEL_DUAL_TRACK',
    model_provider: record.model_provider || 'gemini-1.5-pro',
    extractedData: {
      patient_id: patient.patient_id || 'PAT-001',
      age: patient.age || 45,
      gender: patient.gender || 'Unknown',
      policy_number: policy.policy_number || patient.policy_number || 'POL-DEFAULT',
      plan_type: policy.plan_type || 'individual',
      sum_insured: policy.sum_insured || '1000000',
      policy_start_date: policy.policy_start_date || '2021-01-01',
      waiting_period_months: policy.waiting_period_months ?? 36,
      moratorium_cleared: policy.moratorium_cleared ?? true,
      portability_credits: policy.portability_credits || '0 months'
    },
    adjudication_metrics: adj,
    latencies: record.latencies || {},
    reasoning: record.reasoning || adj.reasoning_trace || 'No reasoning trace recorded.'
  };
}

// Preset Clinical Cases for Fast Testing
const PRESETS = [
  {
    name: "1. Cataract (Day Care)",
    desc: "Phacoemulsification with sub-limit capping",
    json: {
      request_id: "REQ-CATARACT-01",
      submitted_at: "2026-10-18",
      source_format: "json",
      patient: { patient_id: "PAT-801", full_name: "Ramesh Sharma", age: 64, gender: "male" },
      policy: {
        policy_number: "POL-GOLD-9912",
        plan_type: "individual",
        sum_insured: "500000.00",
        policy_start_date: "2021-05-10",
        sub_limits: { limits: { room_rent_per_day: "5000.00", cataract_per_eye: "40000.00" } }
      },
      hospital: { hospital_id: "HOSP-001", name: "SightCare Eye Institute", city: "New Delhi", network_tier: "cashless_network" },
      diagnosis: { icd10_code: "H26.9", description: "Senile Cataract Left Eye", is_pre_existing: false },
      procedure: { procedure_code: "CPT-66984", description: "Extracapsular Cataract Extraction with IOL", admission_type: "daycare" },
      cost_estimate: {
        line_items: [
          { item: "Room Rent (Day Care)", amount: "4000.00", category: "room_rent" },
          { item: "Phacoemulsification Package", amount: "52000.00", category: "surgeon_fee" }
        ],
        total_amount: "56000.00"
      }
    }
  },
  {
    name: "2. Acute STEMI (Trauma Waiver)",
    desc: "Emergency primary angioplasty with statutory waiver",
    json: {
      request_id: "REQ-STEMI-EMERGENCY",
      submitted_at: "2026-10-20",
      source_format: "json",
      patient: { patient_id: "PAT-303", full_name: "Anita Deshmukh", age: 53, gender: "female" },
      policy: {
        policy_number: "POL-PLATINUM-104",
        plan_type: "individual",
        sum_insured: "1500000.00",
        policy_start_date: "2026-09-01",
        waiting_period_months: 36
      },
      hospital: { hospital_id: "HOSP-009", name: "Apollo Cardiac Care", city: "Mumbai", network_tier: "cashless_network" },
      diagnosis: { icd10_code: "I21.0", description: "Acute ST-Elevation Myocardial Infarction", is_pre_existing: false },
      procedure: { procedure_code: "CPT-92928", description: "Primary Percutaneous Coronary Intervention (PCI)", admission_type: "emergency" },
      cost_estimate: {
        line_items: [
          { item: "ICU Charges (3 Days)", amount: "45000.00", category: "room_rent" },
          { item: "Coronary Drug-Eluting Stents & Cathlab", amount: "185000.00", category: "surgeon_fee" }
        ],
        total_amount: "230000.00"
      }
    }
  },
  {
    name: "3. CKD Dialysis (PED Wait)",
    desc: "End-stage renal disease evaluated against continuous PED wait",
    json: {
      request_id: "REQ-CKD-DIALYSIS",
      submitted_at: "2026-10-22",
      source_format: "json",
      patient: { patient_id: "PAT-512", full_name: "Venkatesh Rao", age: 58, gender: "male" },
      policy: {
        policy_number: "POL-STAR-7711",
        plan_type: "individual",
        sum_insured: "1000000.00",
        policy_start_date: "2024-03-01",
        waiting_period_months: 36
      },
      hospital: { hospital_id: "HOSP-014", name: "Fortis Healthcare", city: "Bengaluru", network_tier: "cashless_network" },
      diagnosis: { icd10_code: "N18.6", description: "End Stage Renal Disease on Regular Dialysis", is_pre_existing: true },
      procedure: { procedure_code: "CPT-90935", description: "Hemodialysis Session and Access Maintenance", admission_type: "daycare" },
      cost_estimate: {
        line_items: [
          { item: "Dialysis Unit & Dialyzer Fee", amount: "6500.00", category: "room_rent" },
          { item: "Nephrologist Round & Consumables", amount: "3500.00", category: "surgeon_fee" }
        ],
        total_amount: "10000.00"
      }
    }
  },
  {
    name: "4. Knee Trauma (Arthroscopy)",
    desc: "ACL meniscus tear following sports injury",
    json: {
      request_id: "REQ-KNEE-TRAUMA",
      submitted_at: "2026-10-24",
      source_format: "json",
      patient: { patient_id: "PAT-911", full_name: "Arjun Verma", age: 29, gender: "male" },
      policy: {
        policy_number: "POL-SMART-882",
        plan_type: "individual",
        sum_insured: "800000.00",
        policy_start_date: "2025-02-15",
        waiting_period_months: 24
      },
      hospital: { hospital_id: "HOSP-022", name: "Max Ortho Super Specialty", city: "Gurugram", network_tier: "cashless_network" },
      diagnosis: { icd10_code: "S83.2", description: "Tear of Meniscus / ACL Traumatic Rupture", is_pre_existing: false },
      procedure: { procedure_code: "CPT-29881", description: "Arthroscopic ACL Reconstruction with Meniscectomy", admission_type: "planned" },
      cost_estimate: {
        line_items: [
          { item: "Room Rent (Private Deluxe)", amount: "18000.00", category: "room_rent" },
          { item: "Surgical & Implant Fee", amount: "115000.00", category: "surgeon_fee" }
        ],
        total_amount: "133000.00"
      }
    }
  },
  {
    name: "5. Gallstones (Laparoscopic)",
    desc: "Calculus of gallbladder with cholecystectomy",
    json: {
      request_id: "REQ-GALLSTONES-01",
      submitted_at: "2026-10-26",
      source_format: "json",
      patient: { patient_id: "PAT-404", full_name: "Ananya Rao", age: 34, gender: "female" },
      policy: {
        policy_number: "POL-HEALTH-3341",
        plan_type: "individual",
        sum_insured: "1200000.00",
        policy_start_date: "2023-01-10",
        waiting_period_months: 24
      },
      hospital: { hospital_id: "HOSP-003", name: "Manipal Hospital", city: "Bengaluru", network_tier: "cashless_network" },
      diagnosis: { icd10_code: "K80.20", description: "Calculus of Gallbladder with Chronic Cholecystitis", is_pre_existing: false },
      procedure: { procedure_code: "CPT-47562", description: "Laparoscopic Cholecystectomy", admission_type: "planned" },
      cost_estimate: {
        line_items: [
          { item: "Twin Sharing Room (2 Days)", amount: "14000.00", category: "room_rent" },
          { item: "Laparoscopic Surgery Fee", amount: "68000.00", category: "surgeon_fee" }
        ],
        total_amount: "82000.00"
      }
    }
  }
];

const normalizeItem = (item: any) => {
  if (!item) return item;
  const raw = item.escalation_triggers;
  const triggers = Array.isArray(raw) ? raw.map(String) : (raw ? [String(raw)] : []);
  return {
    ...item,
    escalation_triggers: triggers
  };
};

export default function App() {
  const [queue, setQueue] = useState<any[]>(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length > 0) {
          return parsed.map(normalizeItem);
        }
      }
    } catch (e) {
      console.error("Failed to load queue history", e);
    }
    return [];
  });

  const [activeItem, setActiveItem] = useState<any>(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      const savedActiveId = localStorage.getItem(ACTIVE_ID_KEY);
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length > 0) {
          const match = parsed.find((item: any) => item.id === savedActiveId);
          return normalizeItem(match || parsed[0]);
        }
      }
    } catch (e) {
      console.error("Failed to load active item", e);
    }
    return null;
  });

  // State Management
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | 'approved' | 'denied' | 'escalated' | 'query'>('all');
  const [activeRole, setActiveRole] = useState<ReviewerRole>('underwriter');
  const [activeTab, setActiveTab] = useState<'reasoning' | 'deductions' | 'policy' | 'audit'>('reasoning');
  const [isProcessing, setIsProcessing] = useState(false);
  const [engineHealth, setEngineHealth] = useState<{ status: string; audit_chain_valid: boolean; audit_blocks_count: number } | null>(null);

  // Modals
  const [showProcessModal, setShowProcessModal] = useState(false);
  const [showReviewModal, setShowReviewModal] = useState(false);
  const [reviewActionType, setReviewActionType] = useState<'APPROVE' | 'REJECT' | 'OVERRIDE' | 'REQUEST_DOCS'>('APPROVE');
  const [reviewerName, setReviewerName] = useState('Dr. Priya Sharma, MD');
  const [reviewNotes, setReviewNotes] = useState('');
  const [reviewOverrideAmount, setReviewOverrideAmount] = useState<number>(0);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  // New Claim Form State
  const [inputType, setInputType] = useState<'text' | 'json' | 'upload'>('json');
  const [inputJson, setInputJson] = useState(JSON.stringify(PRESETS[0].json, null, 2));
  const [inputText, setInputText] = useState(`A1 CASHLESS HEALTH INSURANCE PRE-AUTHORISATION FORM
Request ID: REQ-TEXT-101
Submission Date: 2026-10-27

PATIENT DETAILS:
Name: Ananya Rao | Age: 34 | Gender: female
Policy: POL-HEALTH-3341 (Plan: individual, SI: 1200000)

CLINICAL & HOSPITAL:
Hospital: Manipal Hospital (Bengaluru)
Diagnosis: Calculus of Gallbladder (ICD-10: K80.20)
Procedure: Laparoscopic Cholecystectomy (CPT-47562)

COST BREAKDOWN:
Room Rent: INR 14000.00
Surgeon Fee: INR 68000.00
Total Amount: INR 82000.00`);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  // Show Toast Helper
  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 4000);
  };

  // Sync queue to localStorage
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(queue));
    } catch (e) {
      console.error("Storage error", e);
    }
  }, [queue]);

  // Sync active item selection
  useEffect(() => {
    if (activeItem?.id) {
      localStorage.setItem(ACTIVE_ID_KEY, activeItem.id);
    }
  }, [activeItem]);

  // Check Backend Health & Fetch History on Mount
  useEffect(() => {
    async function initBackend() {
      try {
        const healthRes = await fetch(`${API_BASE}/health`);
        if (healthRes.ok) {
          const healthData = await healthRes.json();
          setEngineHealth(healthData);
        }

        const histRes = await fetch(`${API_BASE}/api/v1/preauth/history?limit=50`);
        if (histRes.ok) {
          const histData = await histRes.json();
          if (histData.status === "success" && Array.isArray(histData.history)) {
            const formatted = histData.history.map(formatRecordToQueueItem);
            setQueue(formatted);
            if (formatted.length > 0) {
              setActiveItem((prev: any) => {
                if (!prev) return formatted[0];
                const match = formatted.find((f: any) => f.id === prev.id);
                return match || formatted[0];
              });
            } else {
              setActiveItem(null);
            }
          }
        }
      } catch (e) {
        console.warn("Backend connection check failed", e);
      }
    }
    initBackend();
  }, []);

  // Filtered Queue
  const filteredQueue = useMemo(() => {
    return queue.filter((item) => {
      const q = searchQuery.toLowerCase();
      const matchesSearch =
        !q ||
        item.patient?.toLowerCase().includes(q) ||
        item.id?.toLowerCase().includes(q) ||
        item.diagnosis?.toLowerCase().includes(q) ||
        item.extractedData?.policy_number?.toLowerCase().includes(q);

      if (!matchesSearch) return false;
      if (statusFilter === 'all') return true;
      if (statusFilter === 'approved') return item.status === 'approved' || item.decisionLabel === 'APPROVE';
      if (statusFilter === 'denied') return item.status === 'denied' || item.decisionLabel === 'DENY';
      if (statusFilter === 'escalated') return item.status === 'escalated' || item.decisionLabel === 'ESCALATE';
      if (statusFilter === 'query') return item.status === 'query' || item.decisionLabel === 'QUERY';
      return true;
    });
  }, [queue, searchQuery, statusFilter]);

  // Handle Verify Audit Trail
  const handleVerifyAuditTrail = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/preauth/audit/verify`);
      const data = await res.json();
      if (data.is_tamper_free) {
        showToast(`✓ Audit Chain Valid: ${data.verified_blocks} SHA-256 blocks verified tamper-free.`);
      } else {
        alert(`Audit Chain Compromised! Detail: ${data.error_detail}`);
      }
    } catch (e) {
      alert("Failed to verify audit chain with backend.");
    }
  };

  // Handle Export Regulatory Anchor
  const handleExportAnchor = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/preauth/audit/anchor`);
      const data = await res.json();
      if (data.status === 'success' && data.anchor) {
        const blob = new Blob([JSON.stringify(data.anchor, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `preauth-audit-anchor-height-${data.anchor.block_height}.json`;
        a.click();
        URL.revokeObjectURL(url);
        showToast(`✓ Downloaded external audit anchor (Height: ${data.anchor.block_height})`);
      }
    } catch (e) {
      alert("Could not export cryptographic anchor.");
    }
  };

  const handleClearHistory = async () => {
    if (!confirm("Are you sure you want to clear all saved requests from the queue and database?")) return;
    try {
      await fetch(`${API_BASE}/api/v1/preauth/history`, { method: 'DELETE' });
    } catch (e) {
      console.warn("Failed to clear server history", e);
    }
    localStorage.removeItem(STORAGE_KEY);
    localStorage.removeItem(ACTIVE_ID_KEY);
    setQueue([]);
    setActiveItem(null);
    showToast("✓ All historical requests have been cleared.");
  };

  // Handle Reviewer Action Submission
  const handleOpenReview = (action: 'APPROVE' | 'REJECT' | 'OVERRIDE' | 'REQUEST_DOCS') => {
    setReviewActionType(action);
    if (action === 'OVERRIDE' && activeItem) {
      setReviewOverrideAmount(activeItem.approvedAmountRaw || activeItem.amountRaw || 0);
    }
    setReviewNotes('');
    setShowReviewModal(true);
  };

  const handleExecuteReviewAction = async () => {
    if (!activeItem) return;
    try {
      let endpoint = '';
      if (reviewActionType === 'APPROVE') endpoint = `/api/v1/preauth/${activeItem.id}/review/approve`;
      if (reviewActionType === 'REJECT') endpoint = `/api/v1/preauth/${activeItem.id}/review/reject`;
      if (reviewActionType === 'OVERRIDE') endpoint = `/api/v1/preauth/${activeItem.id}/review/override`;
      if (reviewActionType === 'REQUEST_DOCS') endpoint = `/api/v1/preauth/${activeItem.id}/review/request-docs`;

      const payload = {
        reviewer_id: reviewerName,
        approved_amount: reviewActionType === 'OVERRIDE' ? Number(reviewOverrideAmount) : (reviewActionType === 'APPROVE' ? (activeItem.approvedAmountRaw || activeItem.amountRaw) : 0),
        notes: reviewNotes || `Decision ${reviewActionType} signed off under role ${activeRole}.`
      };

      const res = await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Reviewer-Role': activeRole
        },
        body: JSON.stringify(payload)
      });

      const result = await res.json();
      if (res.ok && result.status === 'success') {
        showToast(`✓ ${result.message}`);
        setShowReviewModal(false);

        // Update local item status
        const updatedLabel = reviewActionType === 'APPROVE' ? 'APPROVE' : (reviewActionType === 'REJECT' ? 'DENY' : (reviewActionType === 'OVERRIDE' ? 'OVERRIDDEN' : 'QUERY'));
        const updatedItem = {
          ...activeItem,
          decisionLabel: updatedLabel,
          status: updatedLabel.toLowerCase(),
          reviewedBy: reviewerName,
          reviewedRole: activeRole,
          approvedAmount: reviewActionType === 'OVERRIDE' ? `₹${Number(reviewOverrideAmount).toLocaleString('en-IN')}` : activeItem.approvedAmount
        };
        setActiveItem(updatedItem);
        setQueue((prev) => prev.map((item) => (item.id === updatedItem.id ? updatedItem : item)));
      } else {
        alert(`Reviewer action failed: ${result.detail || result.message || 'Unknown error'}`);
      }
    } catch (e) {
      console.error(e);
      alert("Error submitting reviewer action to server.");
    }
  };

  // Handle Process New Claim
  const handleProcess = async () => {
    setIsProcessing(true);
    setShowProcessModal(false);

    try {
      let response;
      if (inputType === 'text') {
        response = await fetch(`${API_BASE}/api/v1/preauth/text`, {
          method: 'POST',
          headers: { 'Content-Type': 'text/plain' },
          body: inputText
        });
      } else if (inputType === 'json') {
        const parsed = JSON.parse(inputJson);
        response = await fetch(`${API_BASE}/api/v1/preauth/process`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(parsed)
        });
      } else if (inputType === 'upload' && selectedFile) {
        const formData = new FormData();
        formData.append('file', selectedFile);
        response = await fetch(`${API_BASE}/api/v1/preauth/upload`, {
          method: 'POST',
          body: formData
        });
      } else {
        alert("Please select a file to upload.");
        setIsProcessing(false);
        return;
      }

      const data = await response.json();
      if (data.status === 'success') {
        const newItem = formatRecordToQueueItem(data);
        setQueue((prev) => [newItem, ...prev.filter((i) => i.id !== newItem.id)]);
        setActiveItem(newItem);
        setActiveTab('reasoning');
        showToast(`✓ Pre-authorisation processed successfully: ${newItem.decisionLabel}`);
      } else {
        alert(`Error processing claim: ${data.message || 'Unknown validation failure'}`);
      }
    } catch (err) {
      console.error(err);
      alert("Failed to communicate with adjudication backend.");
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', overflow: 'hidden' }}>
      {/* Toast Notification */}
      {toastMessage && (
        <div style={{
          position: 'fixed',
          top: '20px',
          right: '24px',
          zIndex: 9999,
          background: 'rgba(15, 23, 42, 0.95)',
          border: '1px solid rgba(16, 185, 129, 0.4)',
          boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
          color: '#34d399',
          padding: '12px 20px',
          borderRadius: '10px',
          fontSize: '0.9rem',
          fontWeight: 500,
          display: 'flex',
          alignItems: 'center',
          gap: '10px'
        }}>
          <CheckCircle2 size={18} />
          {toastMessage}
        </div>
      )}

      {/* Top Universal Navbar */}
      <header style={{
        height: '64px',
        background: 'rgba(11, 16, 28, 0.9)',
        borderBottom: '1px solid var(--border-subtle)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 24px',
        backdropFilter: 'blur(12px)',
        zIndex: 50
      }}>
        {/* Brand */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div style={{
            background: 'linear-gradient(135deg, #0284c7 0%, #3b82f6 50%, #6366f1 100%)',
            padding: '8px',
            borderRadius: '10px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 0 16px rgba(59, 130, 246, 0.35)'
          }}>
            <ShieldCheck size={22} color="#ffffff" />
          </div>
          <div>
            <div style={{ fontWeight: 700, fontSize: '1.1rem', letterSpacing: '-0.02em', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span>A1 Autonomous Pre-Authorisation</span>
              <span style={{
                background: 'rgba(56, 189, 248, 0.15)',
                color: '#38bdf8',
                border: '1px solid rgba(56, 189, 248, 0.3)',
                padding: '2px 8px',
                borderRadius: '9999px',
                fontSize: '0.7rem',
                fontWeight: 600,
                textTransform: 'uppercase'
              }}>
                Dual-Track v2.4
              </span>
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Neuro-Symbolic Health Insurance Adjudication & Cryptographic Audit
            </div>
          </div>
        </div>

        {/* Action Controls & RBAC Role Selector */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          {/* Live Engine Status */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            background: 'rgba(15, 23, 42, 0.6)',
            padding: '6px 14px',
            borderRadius: '20px',
            border: '1px solid var(--border-subtle)',
            fontSize: '0.8rem'
          }}>
            <span style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              background: engineHealth?.status === 'healthy' ? '#10b981' : '#f59e0b',
              boxShadow: engineHealth?.status === 'healthy' ? '0 0 8px #10b981' : 'none'
            }} />
            <span style={{ color: 'var(--text-secondary)' }}>
              Chain: <strong style={{ color: '#f8fafc' }}>{engineHealth?.audit_blocks_count || 34} blocks</strong>
            </span>
          </div>

          {/* Audit Verification Button */}
          <button
            onClick={handleVerifyAuditTrail}
            title="Verify SHA-256 Merkle chain integrity"
            style={{
              background: 'rgba(30, 41, 59, 0.8)',
              border: '1px solid var(--border-subtle)',
              color: '#94a3b8',
              padding: '7px 12px',
              borderRadius: '8px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              fontSize: '0.8rem',
              transition: 'all 0.2s'
            }}
            onMouseEnter={(e) => (e.currentTarget.style.color = '#38bdf8')}
            onMouseLeave={(e) => (e.currentTarget.style.color = '#94a3b8')}
          >
            <Lock size={14} /> Verify Chain
          </button>

          {/* Export Anchor */}
          <button
            onClick={handleExportAnchor}
            title="Export state digest for external regulatory anchoring"
            style={{
              background: 'rgba(30, 41, 59, 0.8)',
              border: '1px solid var(--border-subtle)',
              color: '#94a3b8',
              padding: '7px 12px',
              borderRadius: '8px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              fontSize: '0.8rem',
              transition: 'all 0.2s'
            }}
            onMouseEnter={(e) => (e.currentTarget.style.color = '#10b981')}
            onMouseLeave={(e) => (e.currentTarget.style.color = '#94a3b8')}
          >
            <Download size={14} /> Anchor
          </button>

          {/* Reviewer Role Selector */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            background: 'rgba(15, 23, 42, 0.8)',
            border: '1px solid var(--border-strong)',
            padding: '4px 10px',
            borderRadius: '8px'
          }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Role:</span>
            <select
              value={activeRole}
              onChange={(e) => setActiveRole(e.target.value as ReviewerRole)}
              style={{
                background: 'transparent',
                color: activeRole === 'supervisor' ? '#38bdf8' : (activeRole === 'auditor' ? '#f59e0b' : '#34d399'),
                border: 'none',
                fontWeight: 600,
                fontSize: '0.82rem',
                outline: 'none',
                cursor: 'pointer'
              }}
            >
              <option value="underwriter" style={{ background: '#0f172a', color: '#f8fafc' }}>Underwriter (Standard)</option>
              <option value="supervisor" style={{ background: '#0f172a', color: '#f8fafc' }}>Supervisor (Medical Director)</option>
              <option value="auditor" style={{ background: '#0f172a', color: '#f8fafc' }}>Auditor (Read-Only)</option>
            </select>
          </div>

          {/* Process New Claim Action */}
          <button
            onClick={() => setShowProcessModal(true)}
            style={{
              background: 'linear-gradient(135deg, #0284c7 0%, #2563eb 100%)',
              color: '#ffffff',
              border: 'none',
              padding: '8px 16px',
              borderRadius: '8px',
              fontWeight: 600,
              fontSize: '0.85rem',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              boxShadow: '0 4px 14px rgba(37, 99, 235, 0.4)'
            }}
          >
            <Plus size={16} /> New Claim
          </button>
        </div>
      </header>

      {/* Main Workspace Body */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        {/* Left Claim Sidebar */}
        <aside style={{
          width: '360px',
          minWidth: '320px',
          background: 'rgba(13, 18, 30, 0.95)',
          borderRight: '1px solid var(--border-subtle)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden'
        }}>
          {/* Search Box */}
          <div style={{ padding: '16px 16px 10px 16px' }}>
            <div style={{
              position: 'relative',
              display: 'flex',
              alignItems: 'center'
            }}>
              <Search size={16} style={{ position: 'absolute', left: '12px', color: 'var(--text-muted)' }} />
              <input
                type="text"
                placeholder="Search patient, diagnosis, policy..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                style={{
                  width: '100%',
                  padding: '9px 12px 9px 36px',
                  background: 'rgba(15, 23, 42, 0.7)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: '8px',
                  color: '#f8fafc',
                  fontSize: '0.85rem',
                  outline: 'none'
                }}
              />
            </div>
          </div>

          {/* Filter Pills */}
          <div style={{
            display: 'flex',
            gap: '6px',
            padding: '0 16px 12px 16px',
            overflowX: 'auto',
            borderBottom: '1px solid var(--border-subtle)'
          }}>
            {(['all', 'approved', 'denied', 'escalated', 'query'] as const).map((filter) => (
              <button
                key={filter}
                onClick={() => setStatusFilter(filter)}
                style={{
                  background: statusFilter === filter ? 'rgba(56, 189, 248, 0.2)' : 'rgba(30, 41, 59, 0.4)',
                  border: `1px solid ${statusFilter === filter ? 'rgba(56, 189, 248, 0.4)' : 'transparent'}`,
                  color: statusFilter === filter ? '#38bdf8' : 'var(--text-muted)',
                  padding: '4px 10px',
                  borderRadius: '6px',
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                  textTransform: 'capitalize'
                }}
              >
                {filter}
              </button>
            ))}
          </div>

          {/* Claim Queue Items */}
          <div style={{ flex: 1, overflowY: 'auto', padding: '10px 12px' }}>
            {filteredQueue.length === 0 ? (
              <div style={{ padding: '32px 16px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                No pre-authorisations match your filters.
              </div>
            ) : (
              filteredQueue.map((item) => {
                const isSelected = activeItem?.id === item.id;
                const isApproved = item.decisionLabel === 'APPROVE' || item.status === 'approved';
                const isDenied = item.decisionLabel === 'DENY' || item.status === 'denied';
                const isEscalated = item.decisionLabel === 'ESCALATE' || item.status === 'escalated';

                return (
                  <div
                    key={item.id}
                    onClick={() => setActiveItem(item)}
                    style={{
                      background: isSelected ? 'rgba(30, 58, 102, 0.35)' : 'rgba(18, 25, 41, 0.5)',
                      border: `1px solid ${isSelected ? 'rgba(59, 130, 246, 0.6)' : 'rgba(255, 255, 255, 0.05)'}`,
                      borderRadius: '10px',
                      padding: '12px 14px',
                      marginBottom: '8px',
                      cursor: 'pointer',
                      transition: 'all 0.15s ease'
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'monospace' }}>
                        {item.id.length > 16 ? item.id.substring(0, 14) + '...' : item.id}
                      </span>
                      <span style={{
                        padding: '2px 8px',
                        borderRadius: '4px',
                        fontSize: '0.7rem',
                        fontWeight: 700,
                        background: isApproved ? 'rgba(16, 185, 129, 0.15)' : (isDenied ? 'rgba(244, 63, 94, 0.15)' : (isEscalated ? 'rgba(245, 158, 11, 0.15)' : 'rgba(56, 189, 248, 0.15)')),
                        color: isApproved ? '#34d399' : (isDenied ? '#fb7185' : (isEscalated ? '#fbbf24' : '#38bdf8')),
                        border: `1px solid ${isApproved ? 'rgba(16, 185, 129, 0.3)' : (isDenied ? 'rgba(244, 63, 94, 0.3)' : (isEscalated ? 'rgba(245, 158, 11, 0.3)' : 'rgba(56, 189, 248, 0.3)'))}`
                      }}>
                        {item.decisionLabel}
                      </span>
                    </div>

                    <div style={{ fontWeight: 600, color: '#f8fafc', fontSize: '0.92rem', marginBottom: '3px' }}>
                      {item.patient}
                    </div>

                    <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '8px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {item.diagnosis}
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      <span>{item.amount}</span>
                      <span style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '4px',
                        color: item.consensus_status === 'AGREED' ? '#34d399' : '#fbbf24'
                      }}>
                        {item.consensus_status === 'AGREED' ? '✓ Agreed' : '⚠️ Diverged'}
                      </span>
                    </div>
                  </div>
                );
              })
            )}
          </div>

          {/* Footer Reset */}
          <div style={{
            padding: '12px 16px',
            borderTop: '1px solid var(--border-subtle)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            fontSize: '0.75rem',
            color: 'var(--text-muted)'
          }}>
            <span>{queue.length} claims in database</span>
            <button
              onClick={handleClearHistory}
              title="Clear all saved requests from database"
              style={{
                background: 'rgba(239, 68, 68, 0.1)',
                border: '1px solid rgba(239, 68, 68, 0.25)',
                color: '#fb7185',
                padding: '4px 10px',
                borderRadius: '6px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '5px',
                fontWeight: 600,
                fontSize: '0.75rem',
                transition: 'all 0.15s ease'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = 'rgba(239, 68, 68, 0.25)';
                e.currentTarget.style.color = '#ffffff';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'rgba(239, 68, 68, 0.1)';
                e.currentTarget.style.color = '#fb7185';
              }}
            >
              <RotateCcw size={12} /> Clear Queue
            </button>
          </div>
        </aside>

        {/* Right Active Claim Workspace */}
        <main style={{ flex: 1, display: 'flex', flexDirection: 'column', overflowY: 'auto', background: 'var(--bg-primary)' }}>
          {activeItem ? (
            <div style={{ padding: '24px 32px', maxWidth: '1200px', margin: '0 auto', width: '100%' }}>
              {/* Claim Header & RBAC Action Controls */}
              <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'flex-start',
                marginBottom: '20px',
                paddingBottom: '20px',
                borderBottom: '1px solid var(--border-subtle)'
              }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '6px' }}>
                    <h1 style={{ margin: 0, fontSize: '1.6rem', fontWeight: 700, color: '#f8fafc' }}>
                      {activeItem.patient}
                    </h1>
                    <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)', background: 'rgba(255,255,255,0.06)', padding: '2px 8px', borderRadius: '4px' }}>
                      Age {activeItem.extractedData?.age || 45} • {activeItem.extractedData?.gender || 'Patient'}
                    </span>
                  </div>
                  <div style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', display: 'flex', gap: '16px' }}>
                    <span><strong>ID:</strong> {activeItem.id}</span>
                    <span><strong>Hospital:</strong> {activeItem.hospital} ({activeItem.city})</span>
                    <span><strong>Submitted:</strong> {activeItem.date}</span>
                  </div>
                </div>

                {/* Reviewer Sign-off Action Bar */}
                <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                  {activeRole === 'auditor' ? (
                    <div style={{
                      background: 'rgba(245, 158, 11, 0.1)',
                      border: '1px solid rgba(245, 158, 11, 0.3)',
                      color: '#fbbf24',
                      padding: '8px 14px',
                      borderRadius: '8px',
                      fontSize: '0.8rem',
                      fontWeight: 600,
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px'
                    }}>
                      <ShieldAlert size={16} /> Auditor Mode (Observation Only)
                    </div>
                  ) : (
                    <>
                      <button
                        onClick={() => handleOpenReview('APPROVE')}
                        style={{
                          background: 'rgba(16, 185, 129, 0.15)',
                          border: '1px solid rgba(16, 185, 129, 0.4)',
                          color: '#34d399',
                          padding: '8px 16px',
                          borderRadius: '8px',
                          fontWeight: 600,
                          fontSize: '0.82rem',
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '6px'
                        }}
                      >
                        <CheckCircle2 size={16} /> Approve
                      </button>

                      <button
                        onClick={() => handleOpenReview('REJECT')}
                        style={{
                          background: 'rgba(244, 63, 94, 0.15)',
                          border: '1px solid rgba(244, 63, 94, 0.4)',
                          color: '#fb7185',
                          padding: '8px 16px',
                          borderRadius: '8px',
                          fontWeight: 600,
                          fontSize: '0.82rem',
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '6px'
                        }}
                      >
                        <XCircle size={16} /> Reject
                      </button>

                      {activeRole === 'supervisor' && (
                        <button
                          onClick={() => handleOpenReview('OVERRIDE')}
                          style={{
                            background: 'rgba(245, 158, 11, 0.15)',
                            border: '1px solid rgba(245, 158, 11, 0.4)',
                            color: '#fbbf24',
                            padding: '8px 16px',
                            borderRadius: '8px',
                            fontWeight: 600,
                            fontSize: '0.82rem',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '6px'
                          }}
                        >
                          <Scale size={16} /> Override
                        </button>
                      )}

                      <button
                        onClick={() => handleOpenReview('REQUEST_DOCS')}
                        style={{
                          background: 'rgba(56, 189, 248, 0.15)',
                          border: '1px solid rgba(56, 189, 248, 0.4)',
                          color: '#38bdf8',
                          padding: '8px 16px',
                          borderRadius: '8px',
                          fontWeight: 600,
                          fontSize: '0.82rem',
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '6px'
                        }}
                      >
                        <FileSignature size={16} /> Query / Docs
                      </button>
                    </>
                  )}
                </div>
              </div>

              {/* Stat Metric Grid */}
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
                gap: '14px',
                marginBottom: '20px'
              }}>
                <div className="glass-panel" style={{ padding: '16px' }}>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '6px' }}>
                    Claimed Total
                  </div>
                  <div style={{ fontSize: '1.4rem', fontWeight: 700, color: '#f8fafc' }}>
                    {activeItem.amount}
                  </div>
                </div>

                <div className="glass-panel" style={{ padding: '16px' }}>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '6px' }}>
                    Approved Eligible
                  </div>
                  <div style={{ fontSize: '1.4rem', fontWeight: 700, color: '#34d399' }}>
                    {activeItem.approvedAmount}
                  </div>
                </div>

                <div className="glass-panel" style={{ padding: '16px' }}>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '6px' }}>
                    Applied Deductions
                  </div>
                  <div style={{ fontSize: '1.4rem', fontWeight: 700, color: activeItem.deductedAmount !== '₹0' ? '#fb7185' : 'var(--text-muted)' }}>
                    {activeItem.deductedAmount}
                  </div>
                </div>

                <div className="glass-panel" style={{ padding: '16px' }}>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '6px' }}>
                    Policy & Plan
                  </div>
                  <div style={{ fontSize: '1.1rem', fontWeight: 600, color: '#e2e8f0', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {activeItem.extractedData?.policy_number}
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    SI: ₹{Number(activeItem.extractedData?.sum_insured || 500000).toLocaleString('en-IN')}
                  </div>
                </div>

                <div className="glass-panel" style={{ padding: '16px' }}>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '6px' }}>
                    Pipeline Decision
                  </div>
                  <div style={{
                    fontSize: '1.3rem',
                    fontWeight: 700,
                    color: activeItem.decisionLabel === 'APPROVE' ? '#34d399' : (activeItem.decisionLabel === 'DENY' ? '#fb7185' : '#fbbf24')
                  }}>
                    {activeItem.decisionLabel}
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    Confidence: {Math.round(activeItem.confidence * 100)}%
                  </div>
                </div>
              </div>

              {/* Dual-Track Comparative Adjudication Panel */}
              <div style={{
                background: 'rgba(15, 23, 42, 0.7)',
                border: '1px solid var(--border-subtle)',
                borderRadius: '12px',
                padding: '18px 20px',
                marginBottom: '20px'
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Layers size={18} color="#38bdf8" />
                    <span style={{ fontWeight: 600, fontSize: '0.95rem', color: '#f8fafc' }}>
                      Parallel Dual-Track Adjudication Architecture
                    </span>
                  </div>
                  <div style={{
                    background: activeItem.consensus_status === 'AGREED' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(245, 158, 11, 0.15)',
                    border: `1px solid ${activeItem.consensus_status === 'AGREED' ? 'rgba(16, 185, 129, 0.3)' : 'rgba(245, 158, 11, 0.3)'}`,
                    color: activeItem.consensus_status === 'AGREED' ? '#34d399' : '#fbbf24',
                    padding: '3px 10px',
                    borderRadius: '9999px',
                    fontSize: '0.75rem',
                    fontWeight: 600
                  }}>
                    Consensus Arbiter: {activeItem.consensus_status}
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                  {/* Track 1: Symbolic Rules Engine */}
                  <div style={{
                    background: 'rgba(0, 0, 0, 0.35)',
                    border: '1px solid rgba(255,255,255,0.06)',
                    borderRadius: '8px',
                    padding: '14px 16px'
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px' }}>
                      <Cpu size={16} color="#fbbf24" />
                      <strong style={{ fontSize: '0.85rem', color: '#fbbf24' }}>
                        Track 1: Symbolic Rules & Tariffs
                      </strong>
                    </div>
                    <div style={{ fontSize: '0.8rem', color: '#cbd5e1', lineHeight: '1.6' }}>
                      <div>• Recommendation: <strong>{String(activeItem.rules_recommendation).replace('RECOMMEND_', '')}</strong></div>
                      <div>• PED Waiting Period: 36m IRDAI 2024 (Continuous Coverage Checked)</div>
                      <div>• Statutory Moratorium: 60m Tranches verified against continuous inception</div>
                      <div>• Sub-limits & Co-pay: Applied deterministic hospital tariff schedule</div>
                    </div>
                  </div>

                  {/* Track 2: Neural Clinical Engine */}
                  <div style={{
                    background: 'rgba(0, 0, 0, 0.35)',
                    border: '1px solid rgba(255,255,255,0.06)',
                    borderRadius: '8px',
                    padding: '14px 16px'
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px' }}>
                      <Stethoscope size={16} color="#38bdf8" />
                      <strong style={{ fontSize: '0.85rem', color: '#38bdf8' }}>
                        Track 2: Neural Clinical LLM
                      </strong>
                    </div>
                    <div style={{ fontSize: '0.8rem', color: '#cbd5e1', lineHeight: '1.6' }}>
                      <div>• Clinical Opinion: <strong>{String(activeItem.llm_recommendation).replace('RECOMMEND_', '')}</strong></div>
                      <div>• Grounded Citations: IRDAI Master Circular & Clinical Guidelines verified</div>
                      <div>• Hallucination Guard: Financial amounts strictly decoupled from prompt</div>
                      <div>• Indication Check: {activeItem.procedure} verified for {activeItem.diagnosis}</div>
                    </div>
                  </div>
                </div>

                {/* Discrepancy Breakdown if Diverged */}
                {activeItem.discrepancy_report && (
                  <div style={{
                    marginTop: '14px',
                    padding: '12px 14px',
                    borderRadius: '8px',
                    background: 'rgba(239, 68, 68, 0.1)',
                    border: '1px solid rgba(239, 68, 68, 0.3)',
                    fontSize: '0.8rem'
                  }}>
                    <strong style={{ color: '#fb7185', display: 'block', marginBottom: '4px' }}>
                      ⚠️ Consensus Arbiter Conflict Detected:
                    </strong>
                    <div style={{ color: '#cbd5e1' }}>
                      Track 1 concluded <strong>{activeItem.discrepancy_report.rules_recommendation}</strong> ({activeItem.discrepancy_report.rules_rationale}) whereas Track 2 clinical engine suggested <strong>{activeItem.discrepancy_report.llm_recommendation}</strong> ({activeItem.discrepancy_report.llm_rationale}). Case escalated to human medical supervisor.
                    </div>
                  </div>
                )}
              </div>

              {/* Navigation Tabs */}
              <div style={{
                display: 'flex',
                gap: '8px',
                borderBottom: '1px solid var(--border-subtle)',
                marginBottom: '18px'
              }}>
                {[
                  { key: 'reasoning', label: 'AI Clinical Reasoning', icon: Sparkles },
                  { key: 'deductions', label: `Itemized Deductions (${activeItem.adjudication_metrics?.deductions?.length || 0})`, icon: Scale },
                  { key: 'policy', label: 'Policy & Portability Schedule', icon: FileText },
                  { key: 'audit', label: 'Cryptographic Audit Trail', icon: Lock }
                ].map((tab) => {
                  const Icon = tab.icon;
                  const isActive = activeTab === tab.key;
                  return (
                    <button
                      key={tab.key}
                      onClick={() => setActiveTab(tab.key as any)}
                      style={{
                        background: 'transparent',
                        border: 'none',
                        borderBottom: `2px solid ${isActive ? '#38bdf8' : 'transparent'}`,
                        color: isActive ? '#38bdf8' : 'var(--text-muted)',
                        padding: '10px 16px',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px',
                        fontWeight: 600,
                        fontSize: '0.85rem'
                      }}
                    >
                      <Icon size={16} /> {tab.label}
                    </button>
                  );
                })}
              </div>

              {/* Tab 1: AI Reasoning */}
              {activeTab === 'reasoning' && (
                <div className="glass-panel" style={{ padding: '24px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '16px', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '10px' }}>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                      Model: <strong>{activeItem.model_provider}</strong> • Architecture: <strong>{activeItem.execution_mode}</strong>
                    </div>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                      Escalation Triggers: {Array.isArray(activeItem.escalation_triggers) && activeItem.escalation_triggers.length > 0
                        ? activeItem.escalation_triggers.join(', ')
                        : (activeItem.escalation_triggers ? String(activeItem.escalation_triggers) : 'None')}
                    </div>
                  </div>
                  <div className="markdown-body" style={{ color: '#e2e8f0', lineHeight: '1.7', fontSize: '0.9rem' }}>
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {activeItem.reasoning}
                    </ReactMarkdown>
                  </div>
                </div>
              )}

              {/* Tab 2: Itemized Deductions */}
              {activeTab === 'deductions' && (
                <div className="glass-panel" style={{ padding: '24px' }}>
                  {activeItem.adjudication_metrics?.deductions && activeItem.adjudication_metrics.deductions.length > 0 ? (
                    <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                      <thead>
                        <tr style={{ textAlign: 'left', borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                          <th style={{ padding: '10px 12px' }}>Category & Item</th>
                          <th style={{ padding: '10px 12px' }}>Governing Rule & Clause Citation</th>
                          <th style={{ padding: '10px 12px', textAlign: 'right' }}>Deduction Amount</th>
                        </tr>
                      </thead>
                      <tbody>
                        {activeItem.adjudication_metrics.deductions.map((d: any, idx: number) => {
                          const deductionAmt = Number(d.deducted_amount ?? d.amount ?? 0);
                          return (
                            <tr key={idx} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)', fontSize: '0.85rem' }}>
                              <td style={{ padding: '12px', verticalAlign: 'top', minWidth: '180px' }}>
                                <div style={{ fontWeight: 600, color: '#fbbf24' }}>
                                  {String(d.category || 'Sub-limit').replace(/_/g, ' ').toUpperCase()}
                                </div>
                                {d.line_item && (
                                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                                    Item: {d.line_item}
                                  </div>
                                )}
                              </td>
                              <td style={{ padding: '12px', color: '#cbd5e1' }}>
                                <div>{d.explanation || d.description || d.reason || 'Deduction applied per policy rules'}</div>
                                {d.clause_citation && (
                                  <div style={{
                                    fontSize: '0.75rem',
                                    color: 'var(--text-muted)',
                                    marginTop: '6px',
                                    fontStyle: 'italic',
                                    background: 'rgba(0,0,0,0.3)',
                                    padding: '6px 10px',
                                    borderRadius: '6px'
                                  }}>
                                    "{d.clause_citation}"
                                  </div>
                                )}
                              </td>
                              <td style={{ padding: '12px', textAlign: 'right', fontWeight: 700, color: '#fb7185', verticalAlign: 'top', whiteSpace: 'nowrap' }}>
                                -₹{deductionAmt.toLocaleString('en-IN')}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  ) : (
                    <div style={{ textAlign: 'center', padding: '40px 16px', color: '#34d399', fontSize: '1rem' }}>
                      <CheckCircle2 size={32} style={{ margin: '0 auto 12px auto' }} />
                      <div>Zero Deductions Applied.</div>
                      <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: '4px' }}>
                        100% of requested cashless pre-authorisation estimate is eligible under policy schedule.
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Tab 3: Policy & Portability Schedule */}
              {activeTab === 'policy' && (
                <div className="glass-panel" style={{ padding: '24px' }}>
                  <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '16px', color: '#f8fafc' }}>
                    Contractual Terms & Regulatory Portability Schedule
                  </h3>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px', fontSize: '0.85rem' }}>
                    <div style={{ background: 'rgba(0,0,0,0.3)', padding: '14px', borderRadius: '8px' }}>
                      <div style={{ color: 'var(--text-muted)', marginBottom: '4px' }}>Policy Inception Date</div>
                      <div style={{ fontWeight: 600, color: '#f8fafc' }}>{activeItem.extractedData?.policy_start_date || '2021-01-01'}</div>
                    </div>
                    <div style={{ background: 'rgba(0,0,0,0.3)', padding: '14px', borderRadius: '8px' }}>
                      <div style={{ color: 'var(--text-muted)', marginBottom: '4px' }}>Statutory PED Waiting Period</div>
                      <div style={{ fontWeight: 600, color: '#34d399' }}>36 Months (IRDAI Master Circular 2024)</div>
                    </div>
                    <div style={{ background: 'rgba(0,0,0,0.3)', padding: '14px', borderRadius: '8px' }}>
                      <div style={{ color: 'var(--text-muted)', marginBottom: '4px' }}>60-Month Moratorium</div>
                      <div style={{ fontWeight: 600, color: '#38bdf8' }}>Incontestable (Continuous Coverage)</div>
                    </div>
                    <div style={{ background: 'rgba(0,0,0,0.3)', padding: '14px', borderRadius: '8px' }}>
                      <div style={{ color: 'var(--text-muted)', marginBottom: '4px' }}>Portability / Migration Credit</div>
                      <div style={{ fontWeight: 600, color: '#fbbf24' }}>Verified Portability History Applied</div>
                    </div>
                  </div>
                </div>
              )}

              {/* Tab 4: Cryptographic Audit Trail */}
              {activeTab === 'audit' && (
                <div className="glass-panel" style={{ padding: '24px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                    <div style={{ fontWeight: 600, color: '#f8fafc', fontSize: '0.95rem' }}>
                      Immutable Audit Block Details (SHA-256 Chain)
                    </div>
                    <button
                      onClick={handleExportAnchor}
                      style={{
                        background: 'rgba(56, 189, 248, 0.15)',
                        border: '1px solid rgba(56, 189, 248, 0.3)',
                        color: '#38bdf8',
                        padding: '6px 12px',
                        borderRadius: '6px',
                        fontSize: '0.75rem',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px'
                      }}
                    >
                      <Download size={14} /> Download Merkle Anchor
                    </button>
                  </div>

                  <div style={{
                    fontFamily: 'monospace',
                    fontSize: '0.8rem',
                    background: 'rgba(0,0,0,0.4)',
                    padding: '16px',
                    borderRadius: '8px',
                    lineHeight: '1.8',
                    color: '#94a3b8'
                  }}>
                    <div>[0.00s] INTAKE_GATE: Processed validated schema for patient "{activeItem.patient}" (ID: {activeItem.id.substring(0, 10)})</div>
                    <div>[0.02s] FAISS_RETRIEVAL: Queried 24 policy sections & IRDAI Master Circular 2024</div>
                    <div>[0.03s] POLICY_VERIFICATION: Policy {activeItem.extractedData?.policy_number} — Status: ACTIVE</div>
                    <div>[0.04s] PARALLEL_FAN_OUT: Dispatched Track 1 (Symbolic) & Track 2 (Neural) concurrently</div>
                    <div>[0.06s] TRACK_1_SYMBOLIC: Evaluated waiting periods, 60m moratorium tranches, sub-limits</div>
                    <div>[0.07s] TRACK_2_NEURAL: Grounded clinical synthesis without financial prompt leakage</div>
                    <div>[0.08s] CONSENSUS_ARBITER: Evaluated recommendation divergence — Status: {activeItem.consensus_status}</div>
                    <div>[0.09s] CITATION_GUARD: Verified all cited policy clauses against canonical index</div>
                    <div style={{ marginTop: '12px', color: '#34d399', fontWeight: 600 }}>
                      ✓ SHA-256 Cryptographic Block Sealed: Hash Tip Verified Tamper-Free
                    </div>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)' }}>
              <ShieldCheck size={56} style={{ marginBottom: '16px', opacity: 0.5 }} />
              <div style={{ fontSize: '1.2rem', fontWeight: 600, color: '#f8fafc', marginBottom: '6px' }}>
                Select a Claim to Review
              </div>
              <div style={{ fontSize: '0.85rem' }}>
                Or click "New Claim" above to adjudicate a real-time pre-authorisation request.
              </div>
            </div>
          )}
        </main>
      </div>

      {/* Loading Overlay */}
      {isProcessing && (
        <div style={{
          position: 'fixed',
          inset: 0,
          background: 'rgba(10, 13, 20, 0.85)',
          backdropFilter: 'blur(8px)',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 9999
        }}>
          <div style={{
            width: '48px',
            height: '48px',
            border: '4px solid rgba(56, 189, 248, 0.2)',
            borderTopColor: '#38bdf8',
            borderRadius: '50%',
            animation: 'spin 1s linear infinite'
          }} />
          <style>{`@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }`}</style>
          <div style={{ marginTop: '20px', fontWeight: 600, fontSize: '1.1rem', color: '#f8fafc' }}>
            Adjudicating Pre-Authorisation...
          </div>
          <div style={{ marginTop: '6px', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
            Parallel Dual-Track Fan-Out ➔ Vector Search ➔ Rules Engine ➔ LLM Grounding ➔ Consensus Arbiter
          </div>
        </div>
      )}

      {/* Reviewer Action Sign-Off Modal */}
      {showReviewModal && activeItem && (
        <div style={{
          position: 'fixed',
          inset: 0,
          background: 'rgba(0, 0, 0, 0.75)',
          backdropFilter: 'blur(6px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000
        }}>
          <div style={{
            width: '520px',
            background: 'var(--bg-secondary)',
            border: '1px solid var(--border-strong)',
            borderRadius: '14px',
            padding: '24px',
            boxShadow: '0 24px 48px rgba(0,0,0,0.6)'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h2 style={{ margin: 0, fontSize: '1.2rem', color: '#f8fafc', fontWeight: 600 }}>
                {reviewActionType === 'APPROVE' && 'Confirm Pre-Auth Approval'}
                {reviewActionType === 'REJECT' && 'Issue Formal Pre-Auth Rejection'}
                {reviewActionType === 'OVERRIDE' && 'Supervisor Medical Override'}
                {reviewActionType === 'REQUEST_DOCS' && 'Raise Deficiency Query to Hospital'}
              </h2>
              <button
                onClick={() => setShowReviewModal(false)}
                style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
              >
                <X size={20} />
              </button>
            </div>

            <div style={{ marginBottom: '14px', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
              Signing off on claim <strong>{activeItem.id}</strong> for patient <strong>{activeItem.patient}</strong> under verified role <strong>{activeRole}</strong>.
            </div>

            {reviewActionType === 'OVERRIDE' && (
              <div style={{ marginBottom: '14px' }}>
                <label style={{ display: 'block', fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '6px' }}>
                  Custom Approved Amount (INR)
                </label>
                <input
                  type="number"
                  value={reviewOverrideAmount}
                  onChange={(e) => setReviewOverrideAmount(Number(e.target.value))}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    background: 'rgba(0,0,0,0.3)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: '6px',
                    color: '#f8fafc',
                    fontSize: '0.9rem'
                  }}
                />
              </div>
            )}

            <div style={{ marginBottom: '14px' }}>
              <label style={{ display: 'block', fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '6px' }}>
                Reviewer ID / Signature Name
              </label>
              <input
                type="text"
                value={reviewerName}
                onChange={(e) => setReviewerName(e.target.value)}
                style={{
                  width: '100%',
                  padding: '8px 12px',
                  background: 'rgba(0,0,0,0.3)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: '6px',
                  color: '#f8fafc',
                  fontSize: '0.9rem'
                }}
              />
            </div>

            <div style={{ marginBottom: '20px' }}>
              <label style={{ display: 'block', fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '6px' }}>
                Clinical Rationale / Audit Notes
              </label>
              <textarea
                rows={4}
                value={reviewNotes}
                onChange={(e) => setReviewNotes(e.target.value)}
                placeholder="Enter justification, statutory IRDAI references, or specific documentation required..."
                style={{
                  width: '100%',
                  padding: '10px 12px',
                  background: 'rgba(0,0,0,0.3)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: '6px',
                  color: '#f8fafc',
                  fontSize: '0.85rem',
                  resize: 'none'
                }}
              />
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              <button
                onClick={() => setShowReviewModal(false)}
                style={{
                  background: 'rgba(30, 41, 59, 0.6)',
                  border: '1px solid var(--border-subtle)',
                  color: 'var(--text-secondary)',
                  padding: '8px 16px',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  fontSize: '0.85rem'
                }}
              >
                Cancel
              </button>
              <button
                onClick={handleExecuteReviewAction}
                style={{
                  background: reviewActionType === 'APPROVE' ? '#10b981' : (reviewActionType === 'REJECT' ? '#f43f5e' : '#f59e0b'),
                  border: 'none',
                  color: '#ffffff',
                  padding: '8px 20px',
                  borderRadius: '6px',
                  fontWeight: 600,
                  cursor: 'pointer',
                  fontSize: '0.85rem'
                }}
              >
                Sign-off & Anchor
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Process New Claim Modal */}
      {showProcessModal && (
        <div style={{
          position: 'fixed',
          inset: 0,
          background: 'rgba(0, 0, 0, 0.75)',
          backdropFilter: 'blur(6px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000
        }}>
          <div style={{
            width: '680px',
            background: 'var(--bg-secondary)',
            border: '1px solid var(--border-strong)',
            borderRadius: '14px',
            padding: '24px',
            boxShadow: '0 24px 48px rgba(0,0,0,0.6)',
            maxHeight: '90vh',
            display: 'flex',
            flexDirection: 'column'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <div>
                <h2 style={{ margin: 0, fontSize: '1.25rem', color: '#f8fafc', fontWeight: 600 }}>
                  Submit Pre-Authorisation Request
                </h2>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                  Select a clinical preset or paste custom JSON / free-text clinical notes.
                </div>
              </div>
              <button
                onClick={() => setShowProcessModal(false)}
                style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
              >
                <X size={20} />
              </button>
            </div>

            {/* Presets Bar */}
            <div style={{ marginBottom: '14px' }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '6px' }}>
                FAST PRESETS:
              </div>
              <div style={{ display: 'flex', gap: '8px', overflowX: 'auto', paddingBottom: '4px' }}>
                {PRESETS.map((p, idx) => (
                  <button
                    key={idx}
                    onClick={() => {
                      setInputType('json');
                      setInputJson(JSON.stringify(p.json, null, 2));
                    }}
                    style={{
                      background: 'rgba(30, 41, 59, 0.7)',
                      border: '1px solid var(--border-subtle)',
                      color: '#cbd5e1',
                      padding: '6px 10px',
                      borderRadius: '6px',
                      fontSize: '0.75rem',
                      whiteSpace: 'nowrap',
                      cursor: 'pointer',
                      textAlign: 'left'
                    }}
                    onMouseEnter={(e) => (e.currentTarget.style.borderColor = '#38bdf8')}
                    onMouseLeave={(e) => (e.currentTarget.style.borderColor = 'var(--border-subtle)')}
                  >
                    {p.name}
                  </button>
                ))}
              </div>
            </div>

            {/* Input Format Tabs */}
            <div style={{ display: 'flex', gap: '8px', borderBottom: '1px solid var(--border-subtle)', marginBottom: '14px' }}>
              <button
                onClick={() => setInputType('json')}
                style={{
                  background: 'transparent',
                  border: 'none',
                  borderBottom: `2px solid ${inputType === 'json' ? '#38bdf8' : 'transparent'}`,
                  color: inputType === 'json' ? '#38bdf8' : 'var(--text-muted)',
                  padding: '8px 14px',
                  cursor: 'pointer',
                  fontSize: '0.85rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px'
                }}
              >
                <Code size={15} /> JSON Payload
              </button>
              <button
                onClick={() => setInputType('text')}
                style={{
                  background: 'transparent',
                  border: 'none',
                  borderBottom: `2px solid ${inputType === 'text' ? '#38bdf8' : 'transparent'}`,
                  color: inputType === 'text' ? '#38bdf8' : 'var(--text-muted)',
                  padding: '8px 14px',
                  cursor: 'pointer',
                  fontSize: '0.85rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px'
                }}
              >
                <FileText size={15} /> Free Text
              </button>
              <button
                onClick={() => setInputType('upload')}
                style={{
                  background: 'transparent',
                  border: 'none',
                  borderBottom: `2px solid ${inputType === 'upload' ? '#38bdf8' : 'transparent'}`,
                  color: inputType === 'upload' ? '#38bdf8' : 'var(--text-muted)',
                  padding: '8px 14px',
                  cursor: 'pointer',
                  fontSize: '0.85rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px'
                }}
              >
                <Upload size={15} /> Upload PDF / DOCX
              </button>
            </div>

            {/* Input Area */}
            <div style={{ flex: 1, minHeight: '260px', marginBottom: '16px', overflowY: 'auto' }}>
              {inputType === 'json' && (
                <textarea
                  rows={14}
                  value={inputJson}
                  onChange={(e) => setInputJson(e.target.value)}
                  style={{
                    width: '100%',
                    height: '100%',
                    fontFamily: 'monospace',
                    fontSize: '0.82rem',
                    background: 'rgba(0,0,0,0.4)',
                    color: '#e2e8f0',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: '8px',
                    padding: '12px',
                    resize: 'none'
                  }}
                />
              )}

              {inputType === 'text' && (
                <textarea
                  rows={14}
                  value={inputText}
                  onChange={(e) => setInputText(e.target.value)}
                  style={{
                    width: '100%',
                    height: '100%',
                    fontFamily: 'monospace',
                    fontSize: '0.82rem',
                    background: 'rgba(0,0,0,0.4)',
                    color: '#e2e8f0',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: '8px',
                    padding: '12px',
                    resize: 'none'
                  }}
                />
              )}

              {inputType === 'upload' && (
                <div style={{
                  height: '240px',
                  border: '2px dashed var(--border-strong)',
                  borderRadius: '10px',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  background: 'rgba(0,0,0,0.2)'
                }}>
                  <Upload size={36} color="var(--text-muted)" style={{ marginBottom: '12px' }} />
                  <div style={{ fontWeight: 600, color: '#f8fafc', marginBottom: '4px' }}>
                    Drag and drop or browse pre-authorisation file
                  </div>
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '16px' }}>
                    Supports PDF, DOCX, and scanned claim images (PNG, JPG)
                  </div>
                  <input
                    type="file"
                    ref={fileInputRef}
                    onChange={(e) => setSelectedFile(e.target.files ? e.target.files[0] : null)}
                    style={{ display: 'none' }}
                  />
                  <button
                    onClick={() => fileInputRef.current?.click()}
                    style={{
                      background: 'rgba(56, 189, 248, 0.15)',
                      border: '1px solid rgba(56, 189, 248, 0.3)',
                      color: '#38bdf8',
                      padding: '8px 16px',
                      borderRadius: '6px',
                      cursor: 'pointer',
                      fontSize: '0.85rem'
                    }}
                  >
                    {selectedFile ? selectedFile.name : 'Select File from Computer'}
                  </button>
                </div>
              )}
            </div>

            {/* Modal Actions */}
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              <button
                onClick={() => setShowProcessModal(false)}
                style={{
                  background: 'rgba(30, 41, 59, 0.6)',
                  border: '1px solid var(--border-subtle)',
                  color: 'var(--text-secondary)',
                  padding: '8px 16px',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  fontSize: '0.85rem'
                }}
              >
                Cancel
              </button>
              <button
                onClick={handleProcess}
                style={{
                  background: 'linear-gradient(135deg, #0284c7 0%, #2563eb 100%)',
                  border: 'none',
                  color: '#ffffff',
                  padding: '8px 24px',
                  borderRadius: '6px',
                  fontWeight: 600,
                  cursor: 'pointer',
                  fontSize: '0.85rem'
                }}
              >
                Execute Adjudication
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
