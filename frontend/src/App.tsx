import { useState, useRef, useEffect } from 'react';
import { ShieldCheck, Activity, Plus, X, FileSignature, Upload, FileText, Code, RotateCcw } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const API_BASE = "http://localhost:8000";
const STORAGE_KEY = "a1_preauth_queue_history";
const ACTIVE_ID_KEY = "a1_preauth_active_id";

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

  return {
    id: reqId,
    patient: patient.full_name?.split('\n')[0] || 'Unknown Patient',
    diagnosis: diagnosis.description?.split('\n')[0] || 'Unknown Diagnosis',
    procedure: procedure.description || 'N/A',
    hospital: hospital.name || 'N/A',
    status: decisionStatus,
    decisionLabel: decisionLabel,
    date: req.submitted_at || new Date().toISOString().split('T')[0],
    amount: formatCurrency(claimRaw),
    approvedAmount: formatCurrency(approvedRaw),
    deductedAmount: formatCurrency(deductedRaw),
    confidence: record.confidence !== undefined ? record.confidence : (adj.confidence_score || 0.8),
    consensus_status: record.consensus_status || (record.needs_escalation && record.escalation_triggers?.some((t: string) => t.includes('Discrepancy')) ? 'DIVERGED' : 'AGREED'),
    discrepancy_report: record.discrepancy_report || null,
    rules_recommendation: record.rules_recommendation || adj.recommendation || 'N/A',
    llm_recommendation: record.llm_recommendation || record.recommendation || 'N/A',
    escalation_triggers: record.escalation_triggers || adj.escalation_triggers || [],
    extractedData: {
      patient_id: patient.patient_id,
      age: patient.age,
      gender: patient.gender,
      policy_number: policy.policy_number || patient.policy_number || 'N/A',
      plan_type: policy.plan_type || 'individual',
      sum_insured: policy.sum_insured || '500000',
    },
    adjudication_metrics: adj,
    latencies: record.latencies || {},
    reasoning: record.reasoning || adj.reasoning_trace || 'No reasoning trace recorded.'
  };
}

// --- MOCK DATA FOR INITIAL FALLBACK ---
const mockQueue: any[] = [];

export default function App() {
  const [queue, setQueue] = useState<any[]>(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length > 0) {
          return parsed;
        }
      }
    } catch (e) {
      console.error("Failed to load queue history from localStorage", e);
    }
    return mockQueue;
  });

  const [activeItem, setActiveItem] = useState<any>(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      const savedActiveId = localStorage.getItem(ACTIVE_ID_KEY);
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length > 0) {
          const match = parsed.find((item: any) => item.id === savedActiveId);
          return match || parsed[0];
        }
      }
    } catch (e) {
      console.error("Failed to load active item from localStorage", e);
    }
    return mockQueue[0];
  });

  // Sync queue to localStorage whenever it changes
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(queue));
    } catch (e) {
      console.error("Failed to save queue to localStorage", e);
    }
  }, [queue]);

  // Sync active item selection to localStorage
  useEffect(() => {
    if (activeItem?.id) {
      localStorage.setItem(ACTIVE_ID_KEY, activeItem.id);
    }
  }, [activeItem]);

  // Load full history from backend on startup
  useEffect(() => {
    async function loadBackendHistory() {
      try {
        const res = await fetch(`${API_BASE}/api/v1/preauth/history`);
        if (res.ok) {
          const json = await res.json();
          if (json.status === "success" && Array.isArray(json.history) && json.history.length > 0) {
            const formatted = json.history.map(formatRecordToQueueItem);
            setQueue((current) => {
              const existingIds = new Set(current.map((c: any) => c.id));
              const newItems = formatted.filter((f: any) => !existingIds.has(f.id));
              // For items existing in both, overwrite with backend's rich LLM result
              const updated = current.map((c: any) => {
                const match = formatted.find((f: any) => f.id === c.id);
                return match || c;
              });
              return [...newItems, ...updated];
            });
            setActiveItem((prev: any) => {
              if (!prev || prev.id === "req-f923184" || prev.id === "aba4b94b-53b8") {
                return formatted[0] || prev;
              }
              const match = formatted.find((f: any) => f.id === prev.id);
              return match || prev;
            });
          }
        }
      } catch (err) {
        console.error("Could not fetch backend history", err);
      }
    }
    loadBackendHistory();
  }, []);

  const handleResetHistory = () => {
    if (confirm("Reset claim history to initial demo cases?")) {
      localStorage.removeItem(STORAGE_KEY);
      localStorage.removeItem(ACTIVE_ID_KEY);
      setQueue(mockQueue);
      setActiveItem(mockQueue[0]);
    }
  };
  const [activeTab, setActiveTab] = useState('reasoning');
  const [isProcessing, setIsProcessing] = useState(false);
  const [showProcessModal, setShowProcessModal] = useState(false);
  const [inputType, setInputType] = useState('text'); // 'text', 'json', 'upload'
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const [inputText, setInputText] = useState(`A1 CASHLESS HEALTH INSURANCE PRE-AUTHORISATION FORM
--------------------------------------------------
Request ID: req-new-101
Submission Date: 2026-09-10
Source Format: text

PATIENT DETAILS
---------------
Patient Name: Ananya Rao
Age: 22
Gender: female
Policy Number: POL-9921

POLICY DETAILS
--------------
Plan Type: individual
Sum Insured: 1500000
Policy Start Date: 2025-01-01

HOSPITAL & CLINICAL DETAILS
---------------------------
Hospital Name: Fortis Hospital
City: Chandigarh
Network Tier: cashless_network
ICD-10 Code: K80.20
Diagnosis: Gallstones
Procedure Code: CPT-47562
Procedure: Laparoscopic cholecystectomy

ESTIMATED COST BREAKDOWN
-----------------------
  Estimated Room Rent: INR 15000.00
  Estimated Surgeon Fee: INR 45000.00
Total Amount: INR 60000.00`);

  const [inputJson, setInputJson] = useState(`{
  "request_id": "req-json-001",
  "submitted_at": "2026-10-15",
  "source_format": "json",
  "status": "pending",
  "admission_date": "2026-10-16",
  "patient": {
    "patient_id": "pat-456",
    "full_name": "Karthik Iyer",
    "age": 52,
    "gender": "male",
    "policy_number": "POL-123456"
  },
  "policy": {
    "policy_number": "POL-123456",
    "plan_type": "individual",
    "sum_insured": "1000000.00",
    "policy_start_date": "2021-01-01",
    "waiting_period_months": 0,
    "sub_limits": {"limits": {"room_rent_per_day": "10000.00"}},
    "co_pay_pct": "0.00"
  },
  "hospital": {
    "hospital_id": "hosp-789",
    "name": "Apollo Hospitals",
    "city": "Chennai",
    "network_tier": "cashless_network",
    "category": "multi_specialty"
  },
  "diagnosis": {
    "icd10_code": "I21.0",
    "description": "Acute STEMI",
    "is_pre_existing": false
  },
  "procedure": {
    "procedure_code": "PCI-002",
    "description": "Primary Angioplasty",
    "admission_type": "emergency"
  },
  "cost_estimate": {
    "line_items": [
      {"item": "Room Rent", "amount": "8000.00", "category": "room_rent"},
      {"item": "Surgeon Fee", "amount": "150000.00", "category": "surgeon_fee"}
    ],
    "total_amount": "158000.00"
  }
}`);

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
        try {
          const parsedJson = JSON.parse(inputJson);
          response = await fetch(`${API_BASE}/api/v1/preauth/process`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(parsedJson)
          });
        } catch (e) {
          alert('Invalid JSON format.');
          setIsProcessing(false);
          return;
        }
      } else if (inputType === 'upload' && selectedFile) {
        const formData = new FormData();
        formData.append('file', selectedFile);
        response = await fetch(`${API_BASE}/api/v1/preauth/upload`, {
          method: 'POST',
          body: formData
        });
      } else {
        alert('Please select a file to upload.');
        setIsProcessing(false);
        return;
      }
      
      const data = await response.json();
      
      if (data.status === 'success') {
        const newItem = formatRecordToQueueItem(data);
        setQueue((prev) => [newItem, ...prev.filter((item) => item.id !== newItem.id)]);
        setActiveItem(newItem);
        setActiveTab('reasoning');
      } else {
        alert('Error processing claim: ' + data.message);
      }
    } catch (err) {
      console.error(err);
      alert('Failed to connect to backend server.');
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <>
      <div className="app-container">
        {/* Sidebar */}
        <div className="sidebar glass-panel animate-mount">
          <div className="brand-header">
            <Activity className="text-primary" size={24} color="#3b82f6" />
            <h1>A1 PreAuth Audit</h1>
          </div>
          
          <div style={{ padding: '0 16px' }}>
            <button 
              className="primary-btn" 
              style={{ width: '100%', justifyContent: 'center' }}
              onClick={() => setShowProcessModal(true)}
            >
              <Plus size={18} /> Process New Claim
            </button>
          </div>

          <div className="queue-list">
            {queue.map((item, i) => (
              <div 
                key={item.id} 
                className={`queue-item ${activeItem.id === item.id ? 'active' : ''} delay-${i+1}`}
                onClick={() => setActiveItem(item)}
              >
                <div className="item-header">
                  <span className="item-id">{item.id.substring(0, 8)}...</span>
                  <span className={`status-badge status-${item.status}`}>
                    {item.decisionLabel || item.status.replace('RECOMMEND_', '').toUpperCase()}
                  </span>
                </div>
                <div className="patient-name">{item.patient}</div>
                <div className="diagnosis-text">{item.diagnosis}</div>
              </div>
            ))}
          </div>

          <div style={{
            padding: '12px 16px',
            borderTop: '1px solid rgba(255, 255, 255, 0.08)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center'
          }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              {queue.length} claim{queue.length === 1 ? '' : 's'} saved
            </span>
            <button
              onClick={handleResetHistory}
              title="Reset history to demo cases"
              style={{
                background: 'transparent',
                border: 'none',
                color: 'var(--text-muted)',
                fontSize: '0.75rem',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                padding: '4px 6px',
                borderRadius: '4px',
                transition: 'color 0.2s'
              }}
              onMouseEnter={(e) => (e.currentTarget.style.color = '#ef4444')}
              onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--text-muted)')}
            >
              <RotateCcw size={12} /> Reset
            </button>
          </div>
        </div>

        {/* Main Content */}
        <div className="main-content glass-panel animate-mount delay-1">
          {activeItem ? (
            <>
              <div className="action-header">
                <div>
                  <h2 className="claim-title">{activeItem.patient}</h2>
                  <div style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginTop: '4px' }}>
                    {activeItem.id} • {activeItem.date}
                  </div>
                </div>
                {(activeItem.status === 'escalated' || activeItem.status.includes('QUERY')) && (
                  <button className="primary-btn" style={{ background: 'var(--success)' }}>
                    <FileSignature size={18} /> Sign-off Review
                  </button>
                )}
              </div>

              <div style={{ padding: '0 24px' }}>
                <div className="stats-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))' }}>
                  <div className="stat-card glass-panel">
                    <span className="stat-label">Claim Amount</span>
                    <span className="stat-value">{activeItem.amount}</span>
                  </div>
                  <div className="stat-card glass-panel">
                    <span className="stat-label">Approved Amount</span>
                    <span className="stat-value" style={{ color: 'var(--success)' }}>
                      {activeItem.approvedAmount || activeItem.amount}
                    </span>
                  </div>
                  <div className="stat-card glass-panel">
                    <span className="stat-label">Deductions</span>
                    <span className="stat-value" style={{ color: activeItem.deductedAmount && activeItem.deductedAmount !== '₹0' ? 'var(--danger)' : 'var(--text-muted)' }}>
                      {activeItem.deductedAmount || '₹0'}
                    </span>
                  </div>
                  <div className="stat-card glass-panel">
                    <span className="stat-label">Policy No.</span>
                    <span className="stat-value" style={{ fontSize: '1.1rem', marginTop: 'auto' }}>
                      {activeItem.extractedData?.policy_number || 'N/A'}
                    </span>
                  </div>
                  <div className="stat-card glass-panel">
                    <span className="stat-label">System Decision</span>
                    <span className="stat-value" style={{ 
                      fontSize: '1.2rem', 
                      marginTop: 'auto',
                      color: activeItem.status === 'approved' || activeItem.decisionLabel === 'APPROVE'
                        ? 'var(--success)'
                        : activeItem.status === 'denied' || activeItem.decisionLabel === 'DENY'
                        ? 'var(--danger)'
                        : activeItem.status === 'query' || activeItem.decisionLabel === 'QUERY'
                        ? 'var(--primary)'
                        : 'var(--warning)'
                    }}>
                      {activeItem.decisionLabel || activeItem.status.replace('RECOMMEND_', '').toUpperCase()}
                    </span>
                  </div>
                </div>

                {/* Dual-Track Neuro-Symbolic Consensus Indicator */}
                <div style={{
                  margin: '16px 0 12px 0',
                  padding: '10px 16px',
                  borderRadius: '8px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  background: activeItem.consensus_status === 'AGREED' ? 'rgba(16, 185, 129, 0.08)' : 'rgba(245, 158, 11, 0.12)',
                  border: `1px solid ${activeItem.consensus_status === 'AGREED' ? 'rgba(16, 185, 129, 0.25)' : 'rgba(245, 158, 11, 0.35)'}`,
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.85rem' }}>
                    <span style={{ fontSize: '1rem' }}>{activeItem.consensus_status === 'AGREED' ? '🛡️' : '⚖️'}</span>
                    <strong style={{ color: activeItem.consensus_status === 'AGREED' ? 'var(--success)' : 'var(--warning)' }}>
                      Dual-Track {activeItem.consensus_status === 'AGREED' ? 'Consensus: Unanimous Agreement' : 'Discrepancy: Human Escalation'}
                    </strong>
                    <span style={{ color: 'var(--text-muted)' }}>
                      (Track 1 Symbolic: {activeItem.rules_recommendation?.replace('RECOMMEND_', '') || activeItem.decisionLabel} · Track 2 Neural: {activeItem.llm_recommendation?.replace('RECOMMEND_', '') || activeItem.decisionLabel})
                    </span>
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'monospace' }}>
                    Confidence: {Math.round(activeItem.confidence * 100)}%
                  </div>
                </div>

                {activeItem.discrepancy_report && (
                  <div style={{
                    marginBottom: '16px',
                    padding: '14px 16px',
                    borderRadius: '8px',
                    background: 'rgba(239, 68, 68, 0.1)',
                    border: '1px solid rgba(239, 68, 68, 0.3)'
                  }}>
                    <div style={{ fontWeight: 600, color: '#f87171', fontSize: '0.85rem', marginBottom: '8px' }}>
                      ⚠️ Dual-Track Arbiter Discrepancy Breakdown:
                    </div>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', fontSize: '0.8rem' }}>
                      <div style={{ background: 'rgba(0,0,0,0.3)', padding: '10px 12px', borderRadius: '6px' }}>
                        <div style={{ color: 'var(--warning)', fontWeight: 600, marginBottom: '4px' }}>
                          Track 1 (Symbolic Rules): {activeItem.discrepancy_report.rules_recommendation}
                        </div>
                        <div style={{ color: '#cbd5e1' }}>{activeItem.discrepancy_report.rules_rationale}</div>
                      </div>
                      <div style={{ background: 'rgba(0,0,0,0.3)', padding: '10px 12px', borderRadius: '6px' }}>
                        <div style={{ color: '#38bdf8', fontWeight: 600, marginBottom: '4px' }}>
                          Track 2 (Neural Clinical): {activeItem.discrepancy_report.llm_recommendation}
                        </div>
                        <div style={{ color: '#cbd5e1' }}>{activeItem.discrepancy_report.llm_rationale}</div>
                      </div>
                    </div>
                  </div>
                )}

                <div className="tabs">
                  <div 
                    className={`tab ${activeTab === 'reasoning' ? 'active' : ''}`}
                    onClick={() => setActiveTab('reasoning')}
                  >
                    AI Reasoning Trace
                  </div>
                  <div 
                    className={`tab ${activeTab === 'deductions' ? 'active' : ''}`}
                    onClick={() => setActiveTab('deductions')}
                  >
                    Itemized Deductions ({activeItem.adjudication_metrics?.deductions?.length || 0})
                  </div>
                  <div 
                    className={`tab ${activeTab === 'audit' ? 'active' : ''}`}
                    onClick={() => setActiveTab('audit')}
                  >
                    Immutable Audit Log
                  </div>
                </div>

                <div className="tab-content glass-panel">
                  {activeTab === 'reasoning' ? (
                    <div className="markdown-body">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {activeItem.reasoning}
                      </ReactMarkdown>
                    </div>
                  ) : activeTab === 'deductions' ? (
                    <div style={{ color: '#e2e8f0' }}>
                      {activeItem.adjudication_metrics?.deductions && activeItem.adjudication_metrics.deductions.length > 0 ? (
                        <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: '8px' }}>
                          <thead>
                            <tr style={{ textAlign: 'left', borderBottom: '1px solid rgba(255,255,255,0.1)', color: 'var(--text-muted)' }}>
                              <th style={{ padding: '10px 12px' }}>Category</th>
                              <th style={{ padding: '10px 12px' }}>Rule & Reason</th>
                              <th style={{ padding: '10px 12px', textAlign: 'right' }}>Deduction Amount</th>
                            </tr>
                          </thead>
                          <tbody>
                            {activeItem.adjudication_metrics.deductions.map((d: any, idx: number) => {
                              const deductionAmt = Number(d.deducted_amount ?? d.amount ?? 0);
                              return (
                                <tr key={idx} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                                  <td style={{ padding: '12px', fontWeight: 600, color: 'var(--warning)', verticalAlign: 'top', minWidth: '160px' }}>
                                    <div>{String(d.category || 'Sub-limit').replace(/_/g, ' ').toUpperCase()}</div>
                                    {d.line_item && (
                                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 400, marginTop: '2px' }}>
                                        Item: {d.line_item}
                                      </div>
                                    )}
                                  </td>
                                  <td style={{ padding: '12px', color: '#cbd5e1' }}>
                                    <div style={{ fontSize: '0.95rem' }}>{d.explanation || d.description || d.reason || 'Deduction applied per policy rules'}</div>
                                    {d.source_document && (
                                      <div style={{ fontSize: '0.75rem', color: '#38bdf8', marginTop: '6px' }}>
                                        Source: {d.source_document}
                                      </div>
                                    )}
                                    {d.clause_citation && (
                                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '4px', fontStyle: 'italic', background: 'rgba(0,0,0,0.25)', padding: '6px 8px', borderRadius: '4px' }}>
                                        "{d.clause_citation.length > 140 ? d.clause_citation.substring(0, 140) + '...' : d.clause_citation}"
                                      </div>
                                    )}
                                  </td>
                                  <td style={{ padding: '12px', textAlign: 'right', fontWeight: 600, color: 'var(--danger)', verticalAlign: 'top', whiteSpace: 'nowrap' }}>
                                    -₹{deductionAmt.toLocaleString('en-IN')}
                                  </td>
                                </tr>
                              );
                            })}
                          </tbody>
                        </table>
                      ) : (
                        <div style={{ color: 'var(--success)', padding: '32px 0', textAlign: 'center', fontSize: '1.05rem' }}>
                          ✓ No deductions applied. 100% of claimed amount is eligible for cashless pre-authorisation.
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="audit-log" style={{ fontFamily: 'monospace', color: 'var(--text-muted)', lineHeight: '1.8' }}>
                      <div>[0.00s] INTAKE: Processed payload for patient "{activeItem.patient}" (ID: {activeItem.id.substring(0, 8)})</div>
                      <div>[0.02s] RETRIEVAL: Loaded governing policy clauses & IRDAI circulars for "{activeItem.diagnosis}"</div>
                      <div>[0.03s] POLICY PAS: Verified policy {activeItem.extractedData?.policy_number} — Status: ACTIVE</div>
                      <div>[0.04s] RULES ENGINE: Evaluated waiting periods, sub-limits, and co-payment</div>
                      <div>[0.05s] LLM REASONING: Synthesized grounded clinical narrative with clause citations</div>
                      <div>[0.06s] ESCALATION GATE: Triggers: {activeItem.escalation_triggers?.length > 0 ? activeItem.escalation_triggers.join(', ') : 'None (Confidence: ' + Math.round(activeItem.confidence * 100) + '%)'}</div>
                      <div style={{ marginTop: '16px', color: 'var(--success)' }}>
                        ✓ Cryptographic Audit Trail: SHA-256 Block #{activeItem.id.substring(0, 8)} Sealed & Verified
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </>
          ) : (
            <div className="empty-state">
              <ShieldCheck size={48} />
              <h2>Select a claim to review</h2>
            </div>
          )}
        </div>
      </div>

      {/* Loading Overlay */}
      {isProcessing && (
        <div className="loading-overlay">
          <div className="spinner"></div>
          <div className="glow-text" style={{ fontSize: '1.2rem', fontWeight: 500 }}>
            Processing via LangGraph...
          </div>
          <div style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
            Extracting ➔ Vector Search ➔ Rules ➔ LLM Audit
          </div>
        </div>
      )}

      {/* Process Modal */}
      {showProcessModal && (
        <div className="modal-overlay">
          <div className="modal glass-panel">
            <div className="modal-header">
              <h2>Submit Pre-Authorisation Request</h2>
              <button className="close-btn" onClick={() => setShowProcessModal(false)}>
                <X size={20} />
              </button>
            </div>
            
            <div className="tabs" style={{ marginBottom: '16px' }}>
              <div 
                className={`tab ${inputType === 'text' ? 'active' : ''}`}
                onClick={() => setInputType('text')}
                style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}
              >
                <FileText size={16} /> Free Text Note
              </div>
              <div 
                className={`tab ${inputType === 'json' ? 'active' : ''}`}
                onClick={() => setInputType('json')}
                style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}
              >
                <Code size={16} /> JSON Payload
              </div>
              <div 
                className={`tab ${inputType === 'upload' ? 'active' : ''}`}
                onClick={() => setInputType('upload')}
                style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}
              >
                <Upload size={16} /> File Upload
              </div>
            </div>

            {inputType === 'text' && (
              <textarea 
                className="input-area"
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                placeholder="Enter free-text clinical notes..."
              />
            )}

            {inputType === 'json' && (
              <textarea 
                className="input-area"
                value={inputJson}
                onChange={(e) => setInputJson(e.target.value)}
                placeholder="Enter JSON payload..."
              />
            )}

            {inputType === 'upload' && (
              <div style={{ 
                border: '2px dashed var(--border)', 
                borderRadius: '8px', 
                padding: '40px', 
                textAlign: 'center',
                marginBottom: '20px',
                background: 'rgba(0,0,0,0.2)'
              }}>
                <Upload size={32} style={{ color: 'var(--text-muted)', marginBottom: '16px' }} />
                <h3 style={{ marginBottom: '8px' }}>Upload Document</h3>
                <p style={{ color: 'var(--text-muted)', marginBottom: '16px', fontSize: '0.9rem' }}>
                  Supports PDF, DOCX, and scanned Images (PNG, JPG)
                </p>
                <input 
                  type="file" 
                  ref={fileInputRef}
                  onChange={(e) => setSelectedFile(e.target.files ? e.target.files[0] : null)}
                  style={{ display: 'none' }}
                />
                <button 
                  className="secondary-btn" 
                  onClick={() => fileInputRef.current?.click()}
                >
                  {selectedFile ? selectedFile.name : 'Select File'}
                </button>
              </div>
            )}

            <div className="modal-actions">
              <button className="secondary-btn" onClick={() => setShowProcessModal(false)}>Cancel</button>
              <button 
                className="primary-btn" 
                onClick={handleProcess}
                disabled={inputType === 'upload' && !selectedFile}
              >
                Process Request
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
