"""
retrieval/corpus/generate_corpus.py
------------------------------------
Generates synthetic policy wordings, benefit tables, IRDAI circular excerpts,
and insurer-specific policy documents for the retrieval pipeline.

This script creates the knowledge base that the FAISS vector store indexes.
All documents are synthetic — no real policyholder data (Guardrail #3).
Every IRDAI reference includes circular number + date (Guardrail #6).

Corpus Structure:
    retrieval/corpus/
    ├── policy_wordings/     → 14 policy wording docs (plan types + procedure guidelines)
    ├── benefit_tables/      → 4 benefit schedule documents
    ├── irdai_circulars/     → 8 IRDAI regulatory excerpts
    └── insurer_policies/    → 8 insurer-specific policy schedule documents

Usage:
    python -m retrieval.corpus.generate_corpus
    # or
    python retrieval/corpus/generate_corpus.py
"""

from __future__ import annotations

import os
import logging

logger = logging.getLogger(__name__)

CORPUS_DIR = os.path.join(os.path.dirname(__file__))

# ============================================================================
# Policy Wording Documents
# ============================================================================

POLICY_WORDINGS = {
    "individual_health_standard.txt": """POLICY WORDING: STANDARD INDIVIDUAL HEALTH INSURANCE
Policy Type: Individual
Insurer: Synthetic Insurance Co. Ltd.
Product: HealthGuard Individual Plan
UIN: SYNTH-IND-HLT-001/V1/2024

SECTION 1 — SCOPE OF COVER
1.1 This policy covers the Insured Person against financial loss arising from
hospitalization necessitated by illness or accidental bodily injury during
the policy period, subject to the terms, conditions, and exclusions herein.

1.2 Coverage is available for hospitalization requiring a minimum continuous
period of 24 hours as an inpatient in a hospital, except for Day Care
Procedures listed in Annexure A.

SECTION 2 — SUM INSURED AND LIMITS
2.1 The maximum liability of the Company shall not exceed the Sum Insured
stated in the Policy Schedule for any one policy year.

2.2 Room Rent Sub-Limit: The daily room rent charges payable shall not exceed
1% of the Sum Insured or the amount specified in the Policy Schedule,
whichever is lower.

2.3 ICU Charges: ICU charges shall not exceed 2% of the Sum Insured per day.

2.4 Proportionate Deduction: If the actual room rent exceeds the eligible
room rent limit, all other admissible charges (surgeon fees, anaesthesia
charges, consultation fees, diagnostics, pharmacy) shall be reduced in the
same proportion as the eligible room rent bears to the actual room rent
charged by the hospital.

2.5 Ambulance Charges: Emergency ambulance charges are covered up to a maximum
of Rs. 2,000 per hospitalization.

SECTION 3 — WAITING PERIODS
3.1 Initial Waiting Period: No claim shall be admissible during the first 30
days of the first policy period, except claims arising from an accident.

3.2 Specific Disease Waiting Period: Claims arising from the following diseases
and treatments shall be admissible only after completion of 24 continuous months
(2 years) from the date of commencement of the first policy period:
    a) Cataract (ICD-10: H25, H26)
    b) Hernia of all types (ICD-10: K40-K46)
    c) Benign Prostatic Hypertrophy (ICD-10: N40)
    d) Cholelithiasis / Gallstones (ICD-10: K80)
    e) Kidney Stones / Urolithiasis (ICD-10: N20, N21)
    f) Joint Replacement Surgery (ICD-10: M17)
    g) Sinusitis and related conditions (ICD-10: J34)
    h) Internal Congenital Anomalies
    i) Haemorrhoids / Piles (ICD-10: I84)

3.3 Pre-Existing Disease (PED) Waiting Period: Any condition, ailment, injury
or disease that is diagnosed or for which medical advice or treatment was
recommended or received by the Insured Person prior to inception of the first
policy shall be covered only after completion of 48 continuous months (4 years)
from the date of commencement of the first policy period.

3.4 Moratorium Period: After completion of 8 continuous years under the policy,
no claim shall be contestable on the ground that a disease or condition was
pre-existing at the time of taking the policy, except for proven fraud.

SECTION 4 — CO-PAYMENT
4.1 The Insured Person shall bear a co-payment as a percentage of every
admissible claim, as specified in the Policy Schedule.

4.2 Co-payment shall be calculated on the admissible claim amount after
deduction of any non-payable items and sub-limit capping.

4.3 For Senior Citizen plans (entry age 60+), a mandatory co-payment of
not less than 10% shall apply unless waived by the Company.

SECTION 5 — EXCLUSIONS
5.1 Permanent Exclusions: The following are permanently excluded and shall
not be covered under this policy under any circumstances:
    a) Cosmetic or aesthetic treatment or surgery
    b) Self-inflicted injuries or attempted suicide
    c) Treatment for alcoholism or drug/substance abuse
    d) War, invasion, act of foreign enemy, terrorism
    e) Nuclear contamination or radioactive exposure
    f) Hazardous or adventure sports injuries
    g) Treatments for change of sex / gender reassignment
    h) Vaccination and inoculation (unless post-bite)
    i) Weight management / obesity treatment (unless morbid obesity with BMI > 40)

SECTION 6 — CASHLESS FACILITY
6.1 Cashless facility is available at Network Hospitals empanelled with the
Company's Third Party Administrator (TPA).

6.2 Pre-Authorisation Request: For planned hospitalization, a pre-authorisation
request must be submitted to the TPA at least 48-72 hours prior to admission.
For emergency hospitalization, the request must be submitted within 24 hours
of admission.

6.3 Decision Timeline: As per IRDAI Master Circular on Health Insurance
(IRDAI/HLT/CIR/MISC/116/05/2024, dated 29-May-2024), the initial
pre-authorisation decision shall be communicated within 1 hour of receipt
of the request with all necessary documents. Final authorization upon
discharge shall be communicated within 3 hours.

6.4 Non-Network Hospitals: Treatment at non-network hospitals is covered
on a reimbursement basis only, unless emergency pre-authorisation exception
is granted by the Company.

SECTION 7 — POLICY STATUS
7.1 Active Policy: Claims are admissible only when the policy is in active
status with all due premiums paid.

7.2 Lapsed Policy: If the premium due is not paid within the grace period of
30 days, the policy shall lapse. No claims arising during the lapsed period
shall be admissible.

7.3 Expired Policy: Upon expiry of the policy period, no new claims shall be
admissible unless the policy is renewed within the grace period.
""",

    "family_floater_plan.txt": """POLICY WORDING: FAMILY FLOATER HEALTH INSURANCE
Policy Type: Family Floater
Insurer: Synthetic Insurance Co. Ltd.
Product: HealthGuard Family Floater Plan
UIN: SYNTH-FF-HLT-002/V1/2024

SECTION 1 — FAMILY FLOATER PROVISIONS
1.1 The Sum Insured specified in the Policy Schedule is the combined maximum
liability of the Company for all Insured Persons covered under this policy
during any one policy year. Any claim by one Insured Person reduces the Sum
Insured available for all other Insured Persons.

1.2 The primary policyholder's age determines the premium. The oldest member
of the family is considered the primary insured for underwriting purposes.

SECTION 2 — SUM INSURED TIERS AND ROOM RENT
2.1 Sum Insured options: Rs. 3,00,000 / Rs. 5,00,000 / Rs. 10,00,000 / Rs. 25,00,000
2.2 Room Rent Sub-Limit:
    - Sum Insured up to Rs. 5,00,000: Rs. 5,000 per day (General Ward) or
      1% of SI, whichever is lower.
    - Sum Insured Rs. 5,00,001 to Rs. 10,00,000: Rs. 7,500 per day or
      1% of SI, whichever is lower.
    - Sum Insured above Rs. 10,00,000: No room rent sub-limit (Single AC Room).

2.3 ICU Charges: ICU charges limited to 2x the applicable room rent sub-limit.

2.4 Proportionate Deduction: If actual room rent exceeds the eligible room rent,
proportionate deduction shall apply to surgeon fees, anaesthesia, consultation,
diagnostics, and pharmacy charges in the ratio: (eligible room rent / actual room rent).

SECTION 3 — WAITING PERIODS
3.1 All waiting period provisions follow the Standard Individual Plan
(Reference: SYNTH-IND-HLT-001, Section 3).

3.2 Additional Maternity Waiting Period: Maternity expenses including normal
delivery, caesarean section, and pre/post-natal expenses are covered only
after completion of 36 continuous months (3 years) from the date of
commencement of the first policy period. Maximum limit: Rs. 50,000 for
normal delivery, Rs. 75,000 for caesarean section.

SECTION 4 — CO-PAYMENT
4.1 No mandatory co-payment for ages below 60 years.
4.2 Mandatory 10% co-payment for members aged 60-70 years.
4.3 Mandatory 20% co-payment for members aged above 70 years.
4.4 Voluntary co-payment options (10%, 20%, 25%) available for premium discount.
""",

    "group_corporate_plan.txt": """POLICY WORDING: GROUP HEALTH INSURANCE (CORPORATE)
Policy Type: Group
Insurer: Synthetic Insurance Co. Ltd.
Product: HealthGuard Corporate Shield
UIN: SYNTH-GRP-HLT-003/V1/2024

SECTION 1 — GROUP POLICY PROVISIONS
1.1 This policy is issued to the Employer (Master Policyholder) for the benefit
of eligible employees and their declared dependents.

1.2 Waiver of Initial Waiting Period: The initial 30-day waiting period
is waived for all covered members from the date of joining the group scheme.

1.3 Waiver of Specific Disease Waiting Period: The 24-month specific disease
waiting period is waived for group policies covering 100 or more lives.

1.4 Pre-Existing Disease: PED waiting period is reduced to 12 months
(from the standard 48 months) for group policies covering 500 or more lives.

SECTION 2 — SUM INSURED AND LIMITS
2.1 Sum Insured: As specified in the Group Policy Schedule, typically
Rs. 3,00,000 / Rs. 5,00,000 per employee per policy year.

2.2 Room Rent: Single occupancy room (no sub-limit) for Sum Insured of
Rs. 5,00,000 and above. For lower Sum Insured, Rs. 5,000/day limit applies.

SECTION 3 — CO-PAYMENT
3.1 No co-payment applicable for network hospital treatment.
3.2 For non-network hospitals, a 20% co-payment applies on the total
admissible claim amount.
""",

    "senior_citizen_plan.txt": """POLICY WORDING: SENIOR CITIZEN HEALTH INSURANCE
Policy Type: Senior Citizen
Insurer: Synthetic Insurance Co. Ltd.
Product: HealthGuard Senior Shield
UIN: SYNTH-SC-HLT-004/V1/2024

SECTION 1 — ELIGIBILITY
1.1 Entry age: 60 years to 80 years. Renewal available lifelong.
1.2 Pre-policy medical screening is mandatory for all applicants.

SECTION 2 — SUM INSURED AND LIMITS
2.1 Sum Insured options: Rs. 2,00,000 / Rs. 3,00,000 / Rs. 5,00,000
2.2 Room Rent: Rs. 4,000/day for SI up to Rs. 3,00,000; Rs. 5,000/day
for SI of Rs. 5,00,000.

SECTION 3 — MANDATORY CO-PAYMENT
3.1 All claims are subject to a mandatory co-payment of 20%.
3.2 This co-payment is non-waivable and applies after sub-limit deductions.

SECTION 4 — DISEASE-SPECIFIC SUB-LIMITS
4.1 Cataract Surgery: Maximum Rs. 40,000 per eye (inclusive of lens, IOL,
surgery charges, pre and post-operative care).
4.2 Knee Replacement: Maximum Rs. 1,50,000 per knee.
4.3 CABG / Cardiac Surgery: Maximum Rs. 3,00,000.
4.4 Dialysis: Maximum Rs. 2,000 per session, limited to 24 sessions per year.
""",

    "top_up_super_top_up.txt": """POLICY WORDING: TOP-UP AND SUPER TOP-UP PLANS
Policy Type: Top-Up / Super Top-Up
Insurer: Synthetic Insurance Co. Ltd.

TOP-UP PLAN (SYNTH-TU-HLT-005/V1/2024):
1.1 A Top-Up plan activates when any single claim in a policy year exceeds
the specified Deductible amount.
1.2 Deductible options: Rs. 3,00,000 / Rs. 5,00,000 / Rs. 10,00,000
1.3 Sum Insured (above deductible): Rs. 10,00,000 / Rs. 25,00,000 / Rs. 50,00,000
1.4 Only the amount exceeding the deductible in a single claim is payable.

SUPER TOP-UP PLAN (SYNTH-STU-HLT-006/V1/2024):
2.1 A Super Top-Up plan activates when the aggregate of all claims in a
policy year exceeds the specified Deductible amount.
2.2 Unlike Top-Up, multiple smaller claims can aggregate to breach the deductible.
2.3 Deductible options: Rs. 3,00,000 / Rs. 5,00,000
2.4 Sum Insured: Rs. 15,00,000 / Rs. 25,00,000 / Rs. 50,00,000
""",

    "critical_illness_plan.txt": """POLICY WORDING: CRITICAL ILLNESS BENEFIT PLAN
Policy Type: Critical Illness
Insurer: Synthetic Insurance Co. Ltd.
Product: HealthGuard Critical Care
UIN: SYNTH-CI-HLT-007/V1/2024

SECTION 1 — BENEFIT STRUCTURE
1.1 This is a fixed-benefit plan. Upon first diagnosis of a covered Critical
Illness, the entire Sum Insured is payable as a lump sum, irrespective of
actual treatment cost.

1.2 Covered Critical Illnesses (37 conditions):
    - STEMI / Myocardial Infarction (ICD-10: I21)
    - Stroke (ICD-10: I63, I64)
    - Cancer (ICD-10: C00-C97)
    - End-Stage Renal Disease (ICD-10: N18.5, N18.6)
    - Major Organ Transplant
    - Coronary Artery Bypass Graft (CABG)
    - Open Heart Surgery / Valve Replacement

1.3 Survival Period: The insured must survive for at least 30 days after
the date of first diagnosis of the Critical Illness.

SECTION 2 — WAITING PERIODS
2.1 Initial waiting period: 90 days from the date of commencement.
2.2 No specific disease waiting period applicable.
2.3 PED exclusion: Any Critical Illness that is a direct consequence of
a pre-existing disease diagnosed before policy inception is excluded
for the first 48 months.
""",

    "cataract_procedure_guidelines.txt": """PROCEDURE GUIDELINES: CATARACT SURGERY (ICD-10: H25, H26)
Applicable to all plan types under Synthetic Insurance Co. Ltd.

1. COVERAGE CRITERIA
1.1 Cataract surgery is covered under Day Care Procedures (Annexure A, Item 17).
1.2 Both phacoemulsification with IOL implantation and manual SICS are covered.
1.3 Coverage includes pre-operative investigations, surgical procedure, IOL
cost, post-operative medications for up to 6 weeks.

2. SUB-LIMITS
2.1 Individual and Family Floater Plans: Maximum Rs. 40,000 per eye.
2.2 Senior Citizen Plans: Maximum Rs. 40,000 per eye.
2.3 Group Plans: No sub-limit (covered under overall Sum Insured).

3. WAITING PERIOD
3.1 Subject to 24-month specific disease waiting period from first policy inception.
3.2 Waived for Group policies with 100+ lives.

4. SPECIAL CONDITIONS
4.1 Both eyes cannot be operated in the same sitting. A minimum gap of
15 days between surgeries for the two eyes is required.
4.2 IOL (Intraocular Lens) cost: Standard monofocal IOL is fully covered.
Premium multifocal/toric IOL: covered up to Rs. 20,000 per eye, balance
borne by the insured.

5. NON-PAYABLE ITEMS FOR CATARACT SURGERY
5.1 Eye pads, eye shields, and sunglasses post-surgery — non-payable.
5.2 Lubricant eye drops beyond the prescribed post-operative period — non-payable.
""",

    "cardiac_stemi_guidelines.txt": """PROCEDURE GUIDELINES: CARDIAC — STEMI / MYOCARDIAL INFARCTION (ICD-10: I21)
Applicable to all plan types under Synthetic Insurance Co. Ltd.

1. COVERAGE CRITERIA
1.1 Acute ST-Elevation Myocardial Infarction (STEMI) is covered as Emergency
hospitalization. Pre-authorisation request must be submitted within 24 hours.
1.2 Procedures covered: Primary PCI (percutaneous coronary intervention),
thrombolysis, CABG (coronary artery bypass graft).

2. SUB-LIMITS
2.1 Stent Cost: Drug-eluting stent (DES) covered up to NPPA ceiling price.
    - As per NPPA notification (effective 2017): DES ceiling price Rs. 30,000.
    - Bare metal stent (BMS): Rs. 7,000.
2.2 CABG: No specific sub-limit — covered under overall Sum Insured.
2.3 ICU charges: Maximum 2% of Sum Insured per day.

3. WAITING PERIOD
3.1 No specific disease waiting period for cardiac emergencies.
3.2 PED waiting period applies if patient has documented history of
ischaemic heart disease prior to policy inception (4-year exclusion).

4. NON-PAYABLE ITEMS
4.1 External cardiac monitoring devices post-discharge — non-payable.
4.2 Cardiac rehabilitation program fees — non-payable under standard plans.
""",

    "appendicitis_procedure_guidelines.txt": """PROCEDURE GUIDELINES: APPENDICITIS (ICD-10: K35, K36, K37)
Applicable to all plan types under Synthetic Insurance Co. Ltd.

1. COVERAGE CRITERIA
1.1 Acute appendicitis (K35.80, K35.20, K35.30) is covered as an Emergency
hospitalization. Pre-authorisation request must be submitted within 24 hours
of admission for cashless facility.
1.2 Procedures covered: Laparoscopic appendectomy (CPT-44970), open
appendectomy (CPT-44950), interval appendectomy for recurrent appendicitis.
1.3 Chronic / recurrent appendicitis (K36) is classified as a Planned
admission and requires pre-authorisation at least 48 hours prior.

2. SUB-LIMITS
2.1 No disease-specific sub-limit for appendicitis — covered under the
overall Sum Insured.
2.2 Room Rent: Standard plan-level room rent sub-limits apply (reference:
room_rent_schedule.txt).
2.3 Surgeon Fee: Covered as per the plan's normal admissible limits. No
separate surgeon fee cap for appendectomy.
2.4 Anaesthesia: General anaesthesia charges covered. Epidural/regional
anaesthesia for laparoscopic approach also covered.

3. WAITING PERIOD
3.1 No specific disease waiting period for appendicitis (not listed in the
24-month waiting period schedule per IRDAI standardised definitions).
3.2 Initial 30-day waiting period applies (except for emergency admissions
arising from acute appendicitis, which are exempt from initial waiting period).
3.3 PED provisions: Appendicitis is not typically a pre-existing disease.
If a patient has documented history of recurrent appendicitis prior to
policy inception, PED waiting period of 48 months applies.

4. NON-PAYABLE ITEMS
4.1 Abdominal binder / belt post-surgery — non-payable (List I consumable).
4.2 Take-home medications beyond the discharge prescription — non-payable.
4.3 Drain tubes (if used for complicated appendicitis) — payable as a
procedure-integral consumable.

5. SPECIAL CONDITIONS
5.1 Gangrenous / perforated appendicitis (K35.20, K35.30): These complicated
presentations may require extended ICU stay and IV antibiotics. ICU charges
are subject to plan ICU sub-limits.
5.2 Incidental appendectomy performed during another surgical procedure is
NOT separately payable — it is included in the primary surgical claim.
""",

    "knee_replacement_procedure_guidelines.txt": """PROCEDURE GUIDELINES: KNEE REPLACEMENT — OSTEOARTHRITIS (ICD-10: M17)
Applicable to all plan types under Synthetic Insurance Co. Ltd.

1. COVERAGE CRITERIA
1.1 Total Knee Arthroplasty (TKA) and Unicompartmental Knee Arthroplasty
(UKA) are covered as Planned hospitalization procedures.
1.2 Pre-authorisation must be submitted at least 72 hours prior to admission.
1.3 Procedures covered: Total knee replacement (CPT-27447), partial/
unicompartmental knee replacement (CPT-27446), revision knee replacement
(CPT-27487).
1.4 Bilateral TKA in a single sitting is covered as a single claim event.
The total payable shall not exceed 1.5x the sub-limit for a single knee.

2. SUB-LIMITS
2.1 Individual and Family Floater Plans: Maximum Rs. 1,50,000 per knee.
2.2 Senior Citizen Plans: Maximum Rs. 1,50,000 per knee.
2.3 Group Plans (100+ lives): No sub-limit — covered under overall Sum Insured.
2.4 Implant Cost (knee prosthesis): Capped at NPPA ceiling price of
Rs. 54,720 per total knee replacement implant. Any charge by the hospital
exceeding the NPPA cap is borne by the insured.
2.5 Physiotherapy: Post-operative inpatient physiotherapy is covered for the
duration of hospitalization. Outpatient physiotherapy post-discharge is
NOT covered under standard plans.

3. WAITING PERIOD
3.1 Subject to 24-month Specific Disease Waiting Period from first policy
inception (Gonarthrosis M17 is a listed condition).
3.2 Pre-Existing Disease: If the patient has documented osteoarthritis prior
to policy inception, the 48-month PED waiting period applies.
3.3 Moratorium: After 8 continuous years, no PED contestability applies.
3.4 Group Plans with 100+ lives: Specific disease waiting period waived.
Group Plans with 500+ lives: PED waiting period reduced to 12 months.

4. NON-PAYABLE ITEMS
4.1 Knee brace / immobilizer post-surgery — non-payable (external DME).
4.2 Walking aids (walker, crutches) — non-payable unless specifically
covered under the policy endorsement.
4.3 Compression stockings (DVT prophylaxis) — non-payable (List III).
4.4 CPM (Continuous Passive Motion) machine rental — non-payable under
standard plans, may be covered under enhanced / corporate plans.
""",

    "pneumonia_procedure_guidelines.txt": """PROCEDURE GUIDELINES: PNEUMONIA — INPATIENT MANAGEMENT (ICD-10: J12-J18)
Applicable to all plan types under Synthetic Insurance Co. Ltd.

1. COVERAGE CRITERIA
1.1 Pneumonia requiring inpatient hospitalization (minimum 24 hours) is
covered. Community-acquired pneumonia (J18.9), bacterial pneumonia (J15),
viral pneumonia (J12), and aspiration pneumonia (J69) are all covered.
1.2 This is a medical (non-surgical) admission — classified as Emergency
for acute respiratory distress or Planned for step-down management.
1.3 No specific procedure code — coded as PROC-MED-CON (inpatient
conservative medical management).
1.4 Treatment components covered: IV antibiotics, oxygen therapy, nebulization,
chest physiotherapy, diagnostic imaging (chest X-ray, CT thorax), blood
cultures, sputum analysis, ABG analysis.

2. SUB-LIMITS
2.1 No disease-specific sub-limit — covered under overall Sum Insured.
2.2 Room Rent: Standard plan-level room rent sub-limits apply.
2.3 ICU Charges: If the patient requires ICU/MICU admission (e.g., for
mechanical ventilation, non-invasive ventilation, or severe hypoxia),
ICU charges are subject to plan-level ICU sub-limits (typically 2% of
Sum Insured per day).
2.4 Ventilator charges (mechanical ventilation): Covered during ICU stay
as part of ICU bundled charges.

3. WAITING PERIOD
3.1 No specific disease waiting period for pneumonia — it is an acute
infectious condition, not a listed specific disease.
3.2 Initial 30-day waiting period applies, EXCEPT for emergency admissions
(acute pneumonia with respiratory distress qualifies as emergency).
3.3 PED provisions: If the patient has a documented chronic lung condition
(COPD, asthma, ILD) that predisposed them to recurrent pneumonia, the
insurer may invoke PED waiting period on the underlying chronic condition.

4. NON-PAYABLE ITEMS
4.1 Pulse oximeter for home monitoring post-discharge — non-payable (DME).
4.2 Incentive spirometer for home use — non-payable.
4.3 Nebulizer machine for home use — non-payable (DME).
4.4 Take-home oxygen concentrator or cylinder — non-payable under standard
plans. May be covered under critical illness rider if applicable.
""",

    "esrd_hemodialysis_guidelines.txt": """PROCEDURE GUIDELINES: END STAGE RENAL DISEASE — HEMODIALYSIS (ICD-10: N18.5, N18.6)
Applicable to all plan types under Synthetic Insurance Co. Ltd.

1. COVERAGE CRITERIA
1.1 Maintenance hemodialysis for End Stage Renal Disease (ESRD) is covered
as a Day Care Procedure (Annexure A, Item 32). No 24-hour hospitalization
requirement.
1.2 Procedures covered: Hemodialysis session (CPT-90935), hemofiltration,
hemodiafiltration, peritoneal dialysis initiation.
1.3 AV fistula creation (CPT-36825) for permanent vascular access is a
separately payable inpatient/daycare surgical procedure.
1.4 Temporary dialysis catheter insertion is covered as part of the dialysis
session charges.

2. SUB-LIMITS
2.1 Individual and Family Floater Plans: Maximum Rs. 2,000 per dialysis
session (inclusive of dialyzer, bloodlines, heparin, saline).
2.2 Annual Session Limit: Maximum 24 sessions per policy year for Individual/
FF/SC plans. Group plans may cover unlimited sessions subject to Sum Insured.
2.3 Senior Citizen Plans: Rs. 2,000 per session, 24 sessions/year.
2.4 Group Plans: Per-session limit may be waived for groups with 500+ lives.
2.5 EPO (Erythropoietin) injections: Covered up to Rs. 1,500 per injection,
maximum 12 injections per policy year.

3. WAITING PERIOD
3.1 ESRD and chronic kidney disease (CKD Stage 3-5) are considered
pre-existing diseases if diagnosed prior to policy inception. Standard
48-month PED waiting period applies.
3.2 If CKD progresses to ESRD during the policy period (i.e., first
diagnosed with CKD after policy inception), the specific disease waiting
period of 24 months applies from the date of CKD diagnosis.
3.3 Group Plans (500+ lives): PED waiting period reduced to 12 months.
3.4 Moratorium: After 8 continuous policy years, PED is no longer contestable.

4. NON-PAYABLE ITEMS
4.1 Home hemodialysis machine and supplies — non-payable under standard plans.
4.2 Dietary supplements (renal vitamins, phosphate binders taken at home) — non-payable.
4.3 Transportation to/from dialysis centre — non-payable.
4.4 Dialyzer reuse charges (if the centre reprocesses dialyzers) — non-payable.

5. SPECIAL CONDITIONS
5.1 Kidney Transplant: If the patient undergoes a kidney transplant, the
transplant surgery itself is covered under the overall Sum Insured (subject
to plan limits). Post-transplant immunosuppressant medications are covered
for the duration of hospitalization only; outpatient immunosuppressants are
NOT covered under standard indemnity plans.
5.2 AV Fistula complications (thrombosis, stenosis requiring balloon
angioplasty or surgical revision) — covered as a separate daycare claim.
""",

    "diabetes_management_guidelines.txt": """PROCEDURE GUIDELINES: TYPE 2 DIABETES MELLITUS — INPATIENT MANAGEMENT (ICD-10: E11)
Applicable to all plan types under Synthetic Insurance Co. Ltd.

1. COVERAGE CRITERIA
1.1 Inpatient admission for diabetes is covered ONLY when the patient
requires hospitalization for acute glycemic emergencies or complications:
    a) Diabetic ketoacidosis (DKA) — ICD-10: E11.10
    b) Hyperosmolar hyperglycemic state (HHS) — ICD-10: E11.00
    c) Severe hypoglycemia requiring IV dextrose — ICD-10: E11.649
    d) Diabetic foot with infection requiring IV antibiotics — ICD-10: E11.621
    e) Glycemic stabilization requiring continuous insulin infusion monitoring
1.2 Routine diabetes management (OPD consultations, HbA1c monitoring,
oral hypoglycemics) is NOT covered under indemnity hospitalization plans.
1.3 Procedure code: PROC-MED-E11 (inpatient diabetic stabilization and
multidisciplinary monitoring).

2. SUB-LIMITS
2.1 No disease-specific sub-limit for diabetic emergency admission —
covered under overall Sum Insured.
2.2 ICU charges (for DKA/HHS requiring critical care): Subject to plan ICU
sub-limits (2% of Sum Insured per day).
2.3 Insulin and injectable medications during hospitalization: Fully covered.
2.4 Continuous Glucose Monitoring (CGM) device during hospital stay: Covered
as an inpatient consumable. CGM sensors for home use — NOT covered.

3. WAITING PERIOD
3.1 Type 2 Diabetes Mellitus (E11) is almost always a Pre-Existing Disease
if diagnosed prior to policy inception. Standard 48-month PED waiting
period applies.
3.2 If diabetes is first diagnosed DURING the policy period (new onset),
the initial 30-day waiting period applies (waived for emergency DKA/HHS).
3.3 Diabetic complications (retinopathy, nephropathy, neuropathy) arising
from pre-existing diabetes are subject to PED waiting period even if the
complication itself manifests after policy inception.
3.4 Group Plans: PED waiting period may be reduced to 12 months (500+ lives).
3.5 Moratorium: After 8 continuous policy years, diabetes as PED cannot be
contested except for proven fraud.

4. NON-PAYABLE ITEMS
4.1 Glucometer and test strips for home use — non-payable (DME).
4.2 Insulin pens, insulin pump supplies for home use — non-payable.
4.3 Diabetic footwear and orthotics — non-payable.
4.4 Dietary counselling / diabetic diet consultation (outpatient) — non-payable.
4.5 HbA1c and routine blood sugar tests done on OPD basis — non-payable.

5. SPECIAL CONDITIONS
5.1 Diabetic Retinopathy Treatment: Covered as a daycare procedure (laser
photocoagulation / anti-VEGF injection). Subject to Cataract-equivalent
sub-limits if combined with cataract surgery.
5.2 Diabetic Nephropathy progressing to ESRD: Falls under ESRD/hemodialysis
guidelines (reference: esrd_hemodialysis_guidelines.txt).
""",

    "gallstones_cholecystectomy_guidelines.txt": """PROCEDURE GUIDELINES: GALLSTONES — CHOLECYSTECTOMY (ICD-10: K80)
Applicable to all plan types under Synthetic Insurance Co. Ltd.

1. COVERAGE CRITERIA
1.1 Cholelithiasis (gallstones) requiring surgical intervention is covered
as a Planned hospitalization. Pre-authorisation required 48-72 hours prior.
1.2 Procedures covered: Laparoscopic cholecystectomy (CPT-47562), open
cholecystectomy (CPT-47600), ERCP with stone extraction (CPT-43264) for
choledocholithiasis (common bile duct stones).
1.3 Acute cholecystitis (K81.0) with emergency presentation is covered as
Emergency hospitalization — pre-authorisation within 24 hours.
1.4 ERCP as a standalone daycare procedure (for CBD stone extraction without
cholecystectomy) is covered under Day Care Procedures (Annexure A).

2. SUB-LIMITS
2.1 No disease-specific sub-limit for cholecystectomy — covered under
overall Sum Insured for all plan types.
2.2 Room Rent: Standard plan-level room rent sub-limits apply.
2.3 Surgical consumables (trocars, harmonic scalpel/LigaSure, clip
appliers): Covered as procedure-integral items.
2.4 Intraoperative cholangiogram (if performed): Covered as part of the
surgical procedure charges.

3. WAITING PERIOD
3.1 Cholelithiasis (K80) is a LISTED condition subject to the 24-month
Specific Disease Waiting Period from first policy inception.
3.2 If gallstones are documented prior to policy inception, the 48-month
PED waiting period applies.
3.3 Emergency cholecystectomy for acute cholecystitis: The specific disease
waiting period still applies even for emergency presentation, UNLESS
the condition was first diagnosed after policy inception AND 24 months have
elapsed since inception.
3.4 Group Plans with 100+ lives: Specific disease waiting period waived.
Group Plans with 500+ lives: PED waiting period reduced to 12 months.

4. NON-PAYABLE ITEMS
4.1 Abdominal binder post-surgery — non-payable (List I consumable).
4.2 Ursodeoxycholic acid (UDCA) prescribed for home use post-discharge — non-payable.
4.3 Drain bags (if surgical drain placed) — payable if used during
hospitalization; non-payable for home drain care supplies.

5. SPECIAL CONDITIONS
5.1 Incidental gallstones: If gallstones are discovered incidentally during
imaging for another condition and cholecystectomy is performed electively,
the claim is subject to the 24-month waiting period.
5.2 Combined procedures (e.g., cholecystectomy with hernia repair): Payable
as a single composite claim. The higher of the two procedure charges applies
for surgeon fee computation.
""",
}

# ============================================================================
# Benefit Tables
# ============================================================================

BENEFIT_TABLES = {
    "room_rent_schedule.txt": """BENEFIT SCHEDULE: ROOM RENT AND ICU SUB-LIMITS
Effective from: 01-April-2024
Insurer: Synthetic Insurance Co. Ltd.

Room Rent Sub-Limits by Sum Insured:
+------------------+---------------------+-------------------+
| Sum Insured (SI) | Room Rent Limit/Day | ICU Limit/Day     |
+------------------+---------------------+-------------------+
| Up to Rs. 2L     | Rs. 2,000           | Rs. 4,000         |
| Rs. 2L - Rs. 3L  | Rs. 3,000           | Rs. 6,000         |
| Rs. 3L - Rs. 5L  | Rs. 5,000           | Rs. 10,000        |
| Rs. 5L - Rs. 10L | Rs. 7,500           | Rs. 15,000        |
| Rs. 10L - Rs. 25L| Rs. 10,000          | Rs. 20,000        |
| Above Rs. 25L    | No Sub-Limit        | No Sub-Limit      |
+------------------+---------------------+-------------------+

Proportionate Deduction Formula:
When actual room rent exceeds the eligible limit:
  Eligible Proportion = (Room Rent Limit) / (Actual Room Rent Charged)
  Proportionate Deduction applies to:
    - Surgeon Fee
    - Anaesthesia Fee
    - Consultation Fee
    - Diagnostic Charges
    - Pharmacy Charges

Example:
  Policy SI: Rs. 5,00,000 → Room Rent Limit: Rs. 5,000/day
  Hospital charges Rs. 8,000/day room rent.
  Eligible Proportion = 5000/8000 = 0.625 (62.5%)
  Surgeon Fee Rs. 50,000 → Eligible: Rs. 50,000 × 0.625 = Rs. 31,250
  Deducted: Rs. 50,000 - Rs. 31,250 = Rs. 18,750
""",

    "disease_sublimits_schedule.txt": """BENEFIT SCHEDULE: DISEASE-SPECIFIC AND PROCEDURE SUB-LIMITS
Effective from: 01-April-2024
Insurer: Synthetic Insurance Co. Ltd.

+-----------------------------+-------------------+--------------+
| Procedure / Disease         | Sub-Limit (Max)   | Plan Types   |
+-----------------------------+-------------------+--------------+
| Cataract (per eye)          | Rs. 40,000        | Indiv, FF, SC|
| Knee Replacement (per knee) | Rs. 1,50,000      | Indiv, FF, SC|
| CABG / Open Heart Surgery   | Rs. 3,00,000      | SC only      |
| Dialysis (per session)      | Rs. 2,000         | All plans    |
| Dialysis (annual sessions)  | 24 sessions/year  | All plans    |
| Maternity - Normal Delivery | Rs. 50,000        | FF only      |
| Maternity - Caesarean        | Rs. 75,000        | FF only      |
| Ambulance Charges           | Rs. 2,000/event   | All plans    |
| Dental (accident only)      | Rs. 25,000        | All plans    |
+-----------------------------+-------------------+--------------+

Notes:
1. Sub-limits apply independently of the overall Sum Insured.
2. For Group Plans with 100+ lives, disease-specific sub-limits may be waived.
3. Sub-limits are applied BEFORE co-payment calculation.
""",

    "copay_schedule.txt": """BENEFIT SCHEDULE: CO-PAYMENT STRUCTURE
Effective from: 01-April-2024
Insurer: Synthetic Insurance Co. Ltd.

Co-Payment Rules:
1. Co-payment is calculated on the ADMISSIBLE claim amount AFTER:
   - Deduction of non-payable items (IRDAI Lists I-IV)
   - Application of sub-limit capping
   - Application of proportionate deductions (if any)

2. Co-payment by Plan Type and Age:
   +---------------------+--------+--------+--------+
   | Plan Type           | <60 yr | 60-70  | >70 yr |
   +---------------------+--------+--------+--------+
   | Individual          | 0%     | 10%    | 20%    |
   | Family Floater      | 0%     | 10%    | 20%    |
   | Group               | 0%     | 0%     | 0%     |
   | Senior Citizen      | 20%    | 20%    | 20%    |
   +---------------------+--------+--------+--------+

3. Voluntary Co-payment Options (premium discount):
   - 10% voluntary co-pay → 10% premium discount
   - 20% voluntary co-pay → 20% premium discount
   - 25% voluntary co-pay → 25% premium discount

4. Non-Network Hospital Co-payment:
   Additional 20% co-payment applies for treatment at non-network hospitals
   (added to any existing mandatory/voluntary co-payment).

5. Deductible (Top-Up / Super Top-Up):
   Applied BEFORE co-payment. The deductible amount is the insured's
   self-retention and is not eligible for co-payment calculation.
""",

    "waiting_period_matrix.txt": """BENEFIT SCHEDULE: WAITING PERIOD MATRIX
Effective from: 01-April-2024
Insurer: Synthetic Insurance Co. Ltd.

Waiting Period by Type and Plan:
+-----------------------------+-----------+----------+---------+----------+
| Waiting Period Type         | Indiv/FF  | Group    | SC      | CI       |
+-----------------------------+-----------+----------+---------+----------+
| Initial (all illnesses)     | 30 days   | Waived   | 30 days | 90 days  |
| Specific Disease (listed)   | 24 months | Waived*  | 24 mo   | N/A      |
| Pre-Existing Disease (PED)  | 48 months | 12 mo**  | 48 mo   | 48 mo    |
| Maternity                   | 36 months | 12 mo    | N/A     | N/A      |
| Moratorium (all diseases)   | 8 years   | 8 years  | 8 years | 8 years  |
+-----------------------------+-----------+----------+---------+----------+

* Waived for groups with 100+ lives.
** Reduced to 12 months for groups with 500+ lives.

Specific Disease List (24-month waiting period):
ICD-10  | Disease
--------|--------------------------------------------------
H25-H26 | Cataract
K40-K46 | Hernia (all types)
N40     | Benign Prostatic Hypertrophy (BPH)
K80     | Cholelithiasis (Gallstones)
N20-N21 | Urolithiasis (Kidney / Ureter Stones)
M17     | Gonarthrosis (Knee Osteoarthritis)
J34     | Nasal Septum Deviation / Chronic Sinusitis
I84     | Haemorrhoids / Piles
H40     | Glaucoma

Waiting Period Calculation:
- Start date: Date of commencement of FIRST policy period (not renewal).
- Continuous coverage required — any break resets waiting periods.
- Portability: Waiting period credit given for prior continuous coverage
  with another insurer, as per IRDAI Portability Guidelines.
""",
}

# ============================================================================
# IRDAI Regulatory Circulars
# ============================================================================

IRDAI_CIRCULARS = {
    "irdai_master_circular_health_2024.txt": """IRDAI MASTER CIRCULAR ON HEALTH INSURANCE BUSINESS
Circular No.: IRDAI/HLT/CIR/MISC/116/05/2024
Date: 29-May-2024
Source: Insurance Regulatory and Development Authority of India (IRDAI)
URL: https://www.irdai.gov.in/admincms/cms/frmGeneral_Layout.aspx?page=PageNo5659

CHAPTER VI — CASHLESS FACILITY AND CLAIMS SETTLEMENT

Section 36 — Cashless Authorization Timelines:
36.1 Pre-Authorization Decision: The insurer or its TPA shall communicate the
pre-authorization decision within ONE HOUR of receipt of the pre-authorization
request along with all necessary documents from the network provider.

36.2 Enhancement / Final Authorization: Upon discharge of the insured from the
hospital, the insurer or TPA shall communicate the final authorization within
THREE HOURS of receipt of the final bill and discharge summary.

36.3 If the insurer fails to communicate within the stipulated time, the claim
shall be deemed to be approved for the amount requested, subject to policy
terms and conditions.

Section 37 — Query Communication:
37.1 If additional information is required, the insurer shall raise a query
in a single communication and not in multiple rounds. Multiple rounds of
queries for the same claim constitute poor claims servicing.

37.2 The insured shall be given a reasonable time of not less than 15 days
to respond to any query.

Section 38 — Claim Settlement:
38.1 Claims shall be settled within 30 days of receipt of the last necessary
document from the insured or the hospital.

38.2 In case of delay beyond 30 days, interest at the rate of 2% above the
bank rate shall be payable from the date of receipt of last document to the
date of payment.

CHAPTER VII — STANDARDIZATION AND REFORM

Section 42 — National Health Claims Exchange (NHCX):
42.1 All insurers shall mandatorily onboard the National Health Claims Exchange
platform operated by the National Health Authority (NHA).

42.2 Claims data exchange shall follow the FHIR (Fast Healthcare Interoperability
Resources) standard as specified by NHA.

Section 43 — Pre-Existing Disease Definition:
43.1 Pre-Existing Disease (PED) means any condition, ailment, injury or disease:
    a) That is/are diagnosed by a physician within 48 months prior to the
       effective date of the policy issued by the insurer, OR
    b) For which medical advice or treatment was recommended by, or received
       from, a physician within 48 months prior to the effective date of the
       policy issued by the insurer.

43.2 The standard moratorium period of 8 continuous years applies, after which
no claim shall be contestable for pre-existing disease, except in cases of
proven fraud or moral hazard.
""",

    "irdai_non_payables_schedule.txt": """IRDAI GUIDELINES ON NON-PAYABLE ITEMS IN HEALTH INSURANCE
Reference: IRDAI/HLT/REG/CIR/XXX/10/2019 (as updated by Master Circular 2024)
Circular No.: IRDAI/HLT/CIR/MISC/116/05/2024, Chapter IX, Section 52
Date: 29-May-2024
Source: Insurance Regulatory and Development Authority of India (IRDAI)

LIST I — ITEMS THAT ARE NOT PART OF TREATMENT (ALWAYS NON-PAYABLE)
1. Toiletries: Toilet paper, tissues, sanitary pads, diapers
2. Personal comfort items: Telephone charges, TV charges, guest bed charges
3. Administrative charges: Registration charges, admission charges, filing charges
4. Documentation charges: Medico-legal case documentation, birth/death certificate
5. Service charges: Attendant charges, extra diet charges beyond therapeutic diet
6. Laundry charges
7. Mineral water and beverages

LIST II — ITEMS RELATED TO ROOM AND BOARDING (SUBJECT TO ROOM RENT LIMIT)
1. Extra bed charges beyond entitled category
2. Charges for upgrades in room category
3. Mini-bar charges, special menu charges

LIST III — ITEMS RELATED TO CONSUMABLES / DISPOSABLES
Items not directly related to treatment and are for provider's convenience:
1. Surgical gloves, surgical masks, caps, shoe covers, gowns
2. PPE kits (Personal Protective Equipment)
3. Hand sanitizers, disinfectants for room cleaning
4. Linen savers and under-pads
5. Nebulizer masks and tubing (single-use disposable types)

Note: Items in List III that are integral to surgical procedures (e.g., sterile
drapes used during operation) may be admissible at the insurer's discretion.

LIST IV — ITEMS THAT REQUIRE SPECIFIC CONSIDERATION
1. External durable medical equipment: Wheelchair, walker, crutches
   (may be covered under specific plans if prescribed for post-surgical recovery)
2. Spectacles, contact lenses, hearing aids — generally non-payable
3. Dentures — covered only if required due to accidental injury

NPPA PRICE CAPS ON MEDICAL DEVICES:
As per National Pharmaceutical Pricing Authority (NPPA) orders:
- Drug-eluting coronary stent (DES): Ceiling price Rs. 30,000
- Bare metal stent (BMS): Ceiling price Rs. 7,000
- Knee implant: Ceiling price Rs. 54,720 (total knee replacement)
- Hip implant: Ceiling price Rs. 45,350

Any charge by hospital exceeding the NPPA ceiling price for capped devices
is non-payable and shall be deducted from the admissible claim amount.
""",

    "irdai_cashless_timeline_enforcement.txt": """IRDAI ENFORCEMENT GUIDANCE: CASHLESS PRE-AUTHORISATION TIMELINES
Reference: IRDAI/HLT/CIR/MISC/116/05/2024, Chapter VI, Sections 36-38
Date: 29-May-2024
Source: Insurance Regulatory and Development Authority of India (IRDAI)

REGULATORY COMPLIANCE REQUIREMENTS:

1. ONE-HOUR CLOCK:
   The pre-authorisation decision must be communicated to the network
   provider within 60 minutes of receipt of the request with all
   necessary supporting documents. This is a hard compliance obligation,
   not a service-level aspiration.

2. THREE-HOUR CLOCK:
   Final discharge authorization must be communicated within 3 hours of
   receipt of the final bill and discharge summary.

3. CONSEQUENCES OF NON-COMPLIANCE:
   3.1 Deemed approval: If the insurer fails to communicate within the
   stipulated time, the claim is deemed approved.
   3.2 Regulatory action: Persistent non-compliance may attract regulatory
   action under Section 102 of the Insurance Act, 1938.

4. SINGLE-QUERY RULE:
   All queries must be raised in a single communication. Serial queries
   on the same claim are treated as poor claims practice and are subject
   to penalty.

5. DOCUMENT REQUIREMENTS:
   The following documents are considered "necessary" for pre-auth decision:
   a) Duly filled pre-authorization form
   b) Doctor's prescription / case sheet recommending hospitalization
   c) Photo ID proof of insured person
   d) Health card / policy number
   e) Investigation reports supporting the diagnosis

6. RECOMMEND-ONLY AUTOMATED SYSTEMS:
   Any automated system assisting in pre-authorisation decisions must
   operate in a "recommend-only" mode. The final decision authority
   rests with the insurer's authorized medical officer or claims
   team. Automated systems shall not auto-approve or auto-deny claims.
""",

    "irdai_portability_guidelines.txt": """IRDAI GUIDELINES ON HEALTH INSURANCE PORTABILITY
Circular No.: IRDAI/HLT/REG/CIR/222/11/2020 (as updated by Master Circular 2024)
Date: 01-November-2020 (last updated 29-May-2024)
Source: Insurance Regulatory and Development Authority of India (IRDAI)

SECTION 1 — PORTABILITY FRAMEWORK
1.1 Definition: Portability means the right accorded to an individual health
insurance policyholder (including family floater) to transfer the credit
gained for pre-existing conditions and time-bound exclusions from one insurer
to another insurer or from one plan to another plan of the same insurer.

1.2 Eligibility: The policyholder must apply for portability at least 45 days
before and not later than the date of premium renewal.

1.3 Data Exchange: The previous insurer must provide the portability data
(claims history, waiting period credits, policy tenure) through the
Insurance Information Bureau (IIB) within 7 working days of receiving
the porting request.

SECTION 2 — WAITING PERIOD CREDITS
2.1 The new insurer shall give credit for the waiting periods already served
under the previous policy, provided there is continuous coverage without
a break.

2.2 Specific Disease Waiting Period Credit: If the insured has completed
18 months under the previous insurer, the remaining 6 months of the
24-month specific disease waiting period shall be carried forward.

2.3 PED Waiting Period Credit: If the insured has completed 36 months of the
48-month PED waiting period, only 12 months remain under the new insurer.

2.4 If the insured has completed the full waiting period under the previous
insurer (e.g., 48 months for PED), the new insurer CANNOT reimpose any
waiting period for the same condition.

SECTION 3 — RESTRICTIONS
3.1 Portability credit is limited to the Sum Insured of the previous policy.
Any enhancement in Sum Insured under the new policy is subject to fresh
underwriting and waiting periods on the incremental amount.

3.2 Portability is not available for group health insurance policies
transitioning to individual policies (different product category).

3.3 The new insurer cannot deny portability on the grounds of claims history
or pre-existing conditions of the insured.

SECTION 4 — COMPLIANCE
4.1 Insurers must honour portability requests within 15 days of receipt
of complete documentation from the previous insurer via IIB.
4.2 Failure to process portability within the stipulated timeline may attract
regulatory action under Section 102 of the Insurance Act, 1938.
""",

    "irdai_standardized_exclusions.txt": """IRDAI GUIDELINES ON STANDARDIZED EXCLUSIONS IN HEALTH INSURANCE
Circular No.: IRDAI/HLT/REG/CIR/XXX/09/2019 (as updated by Master Circular 2024)
Reference: IRDAI/HLT/CIR/MISC/116/05/2024, Chapter VIII, Sections 45-51
Date: 29-May-2024
Source: Insurance Regulatory and Development Authority of India (IRDAI)

SECTION 1 — PERMANENT EXCLUSIONS (NON-WAIVABLE)
The following conditions are permanently excluded from all health insurance
policies and cannot be covered under any endorsement or rider:

1.1 Cosmetic or aesthetic treatment or surgery (unless necessitated by an
accident or as a part of medically necessary reconstruction).
1.2 Treatment for change of gender / sex reassignment surgery.
1.3 Treatment for alcoholism, drug or substance abuse or misuse.
1.4 Self-inflicted injuries, attempted suicide (whether sane or insane at
the time of the attempt), or self-destructive behaviour.
1.5 War, invasion, act of foreign enemy, warlike operations (whether war be
declared or not), civil war, rebellion, revolution, insurrection.
1.6 Nuclear, chemical, or biological contamination, radioactive exposure.
1.7 Hazardous or adventure sports (unless specifically endorsed for coverage
at additional premium).
1.8 Treatment received outside India (unless covered under a specific
international coverage rider).
1.9 Expenses related to donor treatment in organ transplant cases (unless
specifically covered under the policy).

SECTION 2 — TIME-BOUND EXCLUSIONS
2.1 Initial Waiting Period (30 days): No claim for any illness (except
accidental injuries) during the first 30 days from policy inception.
2.2 Specific Disease Waiting Period (24 months): Listed diseases including
cataract, hernia, BPH, gallstones, kidney stones, knee OA, sinusitis,
haemorrhoids, glaucoma, and internal congenital anomalies.
2.3 Pre-Existing Disease Waiting Period (48 months): Any condition diagnosed
or treated within 48 months prior to policy inception.
2.4 Maternity Waiting Period (typically 36 months for Individual/FF plans).

SECTION 3 — CONDITIONAL EXCLUSIONS
3.1 Dental treatment: Excluded unless necessitated by accidental injury
requiring hospitalization.
3.2 Convalescence, general debility, or congenital external defects/anomalies.
3.3 Sterility and infertility: Excluded unless covered under a specific
fertility rider (available at additional premium).
3.4 Obesity / weight management: Excluded unless morbid obesity (BMI > 40)
requiring bariatric surgery with documented medical necessity.
3.5 Vaccination and inoculation: Excluded unless post-animal-bite prophylaxis
requiring hospitalization.

SECTION 4 — INSURER OBLIGATIONS
4.1 Insurers must clearly communicate all exclusions in the policy document
in simple, understandable language.
4.2 Exclusions not listed in the IRDAI-standardized exclusion list cannot
be applied by insurers.
4.3 Any claim denied on the basis of an exclusion must cite the specific
exclusion clause with reference to IRDAI standardization.
""",

    "irdai_telemedicine_guidelines.txt": """IRDAI GUIDELINES ON TELEMEDICINE IN HEALTH INSURANCE
Circular No.: IRDAI/HLT/MISC/CIR/237/03/2020 (as updated by Master Circular 2024)
Reference: IRDAI/HLT/CIR/MISC/116/05/2024, Chapter X, Section 55
Date: 29-May-2024
Source: Insurance Regulatory and Development Authority of India (IRDAI)

SECTION 1 — RECOGNITION OF TELEMEDICINE CONSULTATIONS
1.1 As per the Telemedicine Practice Guidelines (2020) issued by the Board
of Governors in supersession of the Medical Council of India, telemedicine
consultations are recognized as valid medical consultations.

1.2 A prescription issued through a telemedicine consultation by a Registered
Medical Practitioner (RMP) shall be considered equivalent to a physical
consultation for the purpose of health insurance claims.

1.3 Pre-hospitalisation expenses incurred through telemedicine (teleconsultation
fees, diagnostics ordered via teleconsultation) are admissible under the
pre-hospitalisation coverage period (typically 30-60 days prior to admission).

SECTION 2 — COVERAGE OF TELEMEDICINE IN PRE-AUTHORISATION
2.1 Telemedicine consultations used to diagnose or recommend hospitalization
are valid for pre-authorisation purposes.
2.2 The telemedicine prescription/referral must include:
    a) Name and registration number of the treating doctor
    b) Date and mode of consultation (video/audio/chat)
    c) Diagnosis and recommendation for hospitalization
    d) Unique teleconsultation ID (as per NMC guidelines)

2.3 Insurers cannot deny pre-authorisation solely on the basis that the
initial consultation was conducted via telemedicine.

SECTION 3 — LIMITATIONS
3.1 Telemedicine consultation fees for routine OPD management (not leading
to hospitalization) are NOT covered under standard indemnity plans.
3.2 Post-discharge teleconsultation follow-ups are admissible under the
post-hospitalisation expense coverage period (typically 60-90 days).
3.3 Mental health teleconsultation: Admissible if leading to documented
psychiatric hospitalization meeting the 24-hour inpatient requirement.
""",

    "irdai_grievance_redressal.txt": """IRDAI GUIDELINES ON POLICYHOLDER GRIEVANCE REDRESSAL
Circular No.: IRDAI/HLT/REG/GRV/156/06/2021 (as updated by Master Circular 2024)
Reference: IRDAI/HLT/CIR/MISC/116/05/2024, Chapter XI, Sections 58-62
Date: 29-May-2024
Source: Insurance Regulatory and Development Authority of India (IRDAI)

SECTION 1 — GRIEVANCE CATEGORIES
1.1 Claim-related grievances:
    a) Delay in claim settlement beyond 30 days
    b) Partial claim settlement / short payment
    c) Claim rejection / repudiation
    d) Non-compliance with cashless pre-authorisation timelines
    e) Excessive deductions (non-payable items, proportionate deductions)

1.2 Policy-related grievances:
    a) Delay in policy issuance or renewal
    b) Premium-related disputes
    c) Portability denial or delay
    d) Mis-selling of policy

SECTION 2 — RESOLUTION TIMELINE
2.1 The insurer must acknowledge the grievance within 3 working days.
2.2 The insurer must resolve the grievance within 15 working days of receipt.
2.3 If the insurer requires additional information, the request must be
made within 7 days of receiving the grievance. The 15-day resolution clock
pauses until the policyholder responds.

SECTION 3 — ESCALATION MECHANISM
3.1 Level 1: Insurer's Grievance Redressal Officer (GRO).
3.2 Level 2: IRDAI Integrated Grievance Management System (IGMS) —
    website: igms.irda.gov.in
3.3 Level 3: Insurance Ombudsman (for claims up to Rs. 30,00,000).
3.4 Level 4: Consumer Forum / NCDRC (for claims exceeding Rs. 30,00,000).

SECTION 4 — INSURER OBLIGATIONS
4.1 Every insurer must appoint a designated Grievance Redressal Officer.
4.2 The GRO's contact details must be displayed on the policy document,
website, and all claim communication.
4.3 Monthly grievance statistics must be reported to IRDAI through the
Centralised Grievance Management System.
4.4 Persistent non-resolution of grievances (>30 days) may attract
regulatory action under Section 102 of the Insurance Act, 1938.
""",

    "irdai_fraud_prevention_guidelines.txt": """IRDAI GUIDELINES ON FRAUD MONITORING AND PREVENTION IN HEALTH INSURANCE
Circular No.: IRDAI/HLT/CIR/FRD/189/08/2022 (as updated by Master Circular 2024)
Reference: IRDAI/HLT/CIR/MISC/116/05/2024, Chapter XII, Sections 63-68
Date: 29-May-2024
Source: Insurance Regulatory and Development Authority of India (IRDAI)

SECTION 1 — FRAUD CATEGORIES
1.1 Policyholder/Insured Fraud:
    a) Non-disclosure or misrepresentation of pre-existing diseases
    b) Fabricated or exaggerated claims
    c) Impersonation (claiming under another person's policy)
    d) Staged accidents or self-inflicted injuries presented as accidental

1.2 Hospital/Provider Fraud:
    a) Billing for services or procedures not rendered (phantom billing)
    b) Upcoding — billing for a more expensive procedure than performed
    c) Unbundling — separately billing components of a bundled procedure
    d) Unnecessary hospitalization (patient admitted for conditions treatable
       on OPD basis solely to generate insurance claims)
    e) Inflated room charges, consumable charges, or investigation charges

1.3 Intermediary/TPA Fraud:
    a) Manipulation of claim documents or pre-authorisation recommendations
    b) Collusion with hospitals for claim inflation

SECTION 2 — RED FLAGS FOR AUTOMATED DETECTION
2.1 Cost outliers: Claim amount exceeds 2x the median cost for the same
procedure and hospital category in the same city.
2.2 Frequency outliers: More than 3 claims from the same policy in a
12-month period (excluding chronic/maintenance treatments).
2.3 Temporal anomalies: Admission within 48 hours of policy issuance/renewal.
2.4 Diagnosis-procedure mismatch: Procedure code does not clinically
correspond to the ICD-10 diagnosis code.
2.5 Multiple policies: Same patient claiming for the same treatment under
multiple active policies from different insurers.

SECTION 3 — INVESTIGATION PROTOCOL
3.1 Claims flagged for fraud must be investigated by the insurer's in-house
investigation team or empanelled investigation agency within 30 days.
3.2 The insured must be given a fair hearing and opportunity to present
evidence before a final fraud determination.
3.3 The insurer cannot deny a claim solely based on automated fraud scores —
human review is mandatory (Guardrail #1: recommend-only for automated systems).

SECTION 4 — CONSEQUENCES
4.1 Proven policyholder fraud: Policy voidable ab initio with forfeiture
of all premiums paid. Criminal prosecution under Section 420 IPC.
4.2 Proven provider fraud: De-empanelment from the insurer's network,
reporting to IIB and IRDAI, and potential criminal prosecution.
4.3 Fraud data must be reported to the Insurance Information Bureau (IIB)
for industry-wide sharing and pattern detection.

SECTION 5 — GUARDRAILS FOR AUTOMATED SYSTEMS
5.1 Automated fraud detection systems must operate in "flag-and-refer" mode.
5.2 No claim shall be auto-denied based solely on automated fraud scores.
5.3 The fraud investigation findings must be documented with evidence trail
and communicated to the insured in writing within 45 days.
""",
}

# ============================================================================
# Insurer-Specific Policy Schedules
# ============================================================================

INSURER_POLICIES = {
    "star_health_policy_schedule.txt": """INSURER POLICY SCHEDULE: STAR HEALTH & ALLIED INSURANCE
Insurer: Star Health & Allied Insurance Co. Ltd.
IRDAI Registration No.: 129 (Standalone Health Insurance)
TPA: In-house claims processing (no external TPA)

PRODUCT PORTFOLIO:
1. Star Comprehensive Insurance Policy
   - Plan Type: Individual / Family Floater
   - Sum Insured Options: Rs. 5,00,000 / Rs. 10,00,000 / Rs. 15,00,000 / Rs. 25,00,000
   - Room Rent: No sub-limit for SI >= Rs. 10,00,000. For lower SI: 1% of SI/day.
   - Co-payment: Nil for ages below 60. 20% for ages 60+.
   - Ambulance: Rs. 2,500 per hospitalization.

2. Star Health Senior Citizens Red Carpet Policy
   - Entry Age: 60-75 years (renewable lifelong)
   - Sum Insured: Rs. 1,00,000 / Rs. 2,00,000 / Rs. 3,00,000 / Rs. 5,00,000 / Rs. 10,00,000
   - Mandatory Co-payment: 30% for SI up to Rs. 3,00,000; 20% for higher SI.
   - Room Rent: Rs. 4,000/day for SI up to Rs. 3L; Rs. 6,000/day for higher SI.
   - Cataract Sub-limit: Rs. 40,000 per eye.

3. Star Cardiac Care Insurance Policy
   - Specialized cardiac-only plan
   - Covers STEMI, CABG, angioplasty, valve replacement
   - No waiting period for cardiac emergencies
   - Stent cap: NPPA ceiling (Rs. 30,000 DES / Rs. 7,000 BMS)

NETWORK: 14,000+ network hospitals across India.
Cashless Pre-Auth TAT: 30 minutes for emergencies, 2 hours for planned.
""",

    "hdfc_ergo_policy_schedule.txt": """INSURER POLICY SCHEDULE: HDFC ERGO GENERAL INSURANCE
Insurer: HDFC ERGO General Insurance Co. Ltd.
IRDAI Registration No.: 146 (General Insurance)
TPA: Medi Assist Insurance TPA Pvt. Ltd. / In-house

PRODUCT PORTFOLIO:
1. Optima Restore
   - Plan Type: Individual / Family Floater
   - Sum Insured Options: Rs. 3,00,000 / Rs. 5,00,000 / Rs. 10,00,000 / Rs. 15,00,000 / Rs. 25,00,000 / Rs. 50,00,000
   - Restore Benefit: 100% Sum Insured restored if fully utilized (for unrelated illness).
   - Room Rent: No sub-limit for SI >= Rs. 10,00,000. For lower SI: 1% of SI/day.
   - Co-payment: Nil for ages below 55. 10% for 55-64. 20% for 65+.
   - No Claim Bonus: 50% cumulative bonus for each claim-free year (max 100%).

2. Optima Senior
   - Entry Age: 60-75 years
   - Sum Insured: Rs. 3,00,000 / Rs. 5,00,000 / Rs. 10,00,000
   - Mandatory Co-payment: 20% (non-waivable).
   - Room Rent: Rs. 5,000/day for SI up to Rs. 5L. No limit for higher SI.
   - Domiciliary Hospitalization: Covered up to Rs. 50,000/year for SI >= Rs. 5L.

3. HDFC ERGO My:Health Suraksha
   - Plan Type: Individual
   - Sum Insured: Rs. 3,00,000 to Rs. 75,00,000
   - Silver / Gold / Platinum tiers with varying sub-limits
   - Gold & Platinum: No room rent sub-limit, no co-pay
   - Modern Treatment Coverage: Robotic surgery, stem cell therapy covered under Platinum

NETWORK: 12,000+ network hospitals.
Cashless Pre-Auth TAT: Target 1 hour (IRDAI compliant).
""",

    "icici_lombard_policy_schedule.txt": """INSURER POLICY SCHEDULE: ICICI LOMBARD GENERAL INSURANCE
Insurer: ICICI Lombard General Insurance Co. Ltd.
IRDAI Registration No.: 115 (General Insurance)
TPA: In-house (IL TakeCare)

PRODUCT PORTFOLIO:
1. ICICI Lombard Complete Health Insurance (CHI)
   - Plan Type: Individual / Family Floater
   - Sum Insured Options: Rs. 2,50,000 / Rs. 5,00,000 / Rs. 10,00,000 / Rs. 15,00,000 / Rs. 25,00,000 / Rs. 50,00,000
   - Room Rent: Single Private AC Room for SI >= Rs. 10,00,000. For lower SI: 1% of SI/day.
   - Co-payment: Nil for Individual (ages < 60). 10% mandatory for Senior (60+).
   - Ambulance: Rs. 3,000 per hospitalization.
   - Pre/Post Hospitalization: 60 days pre / 90 days post.

2. ICICI Lombard Health Booster (Top-Up)
   - Deductible Options: Rs. 3,00,000 / Rs. 5,00,000 / Rs. 10,00,000
   - Sum Insured: Rs. 10,00,000 / Rs. 25,00,000 / Rs. 50,00,000
   - No room rent sub-limit. No co-payment.
   - Waiting periods start fresh (not ported from base plan).

3. ICICI Lombard Group Health Insurance
   - Plan Type: Group (Corporate)
   - Sum Insured: Rs. 3,00,000 / Rs. 5,00,000 / Rs. 10,00,000 per employee
   - Initial waiting period: Waived
   - PED waiting period: Waived for groups with 250+ lives
   - Room Rent: Single occupancy room (no sub-limit) for SI >= Rs. 5L
   - Maternity: Optional add-on, Rs. 50,000 normal / Rs. 75,000 C-section

NETWORK: 10,500+ network hospitals.
Cashless Pre-Auth TAT: 45 minutes for emergencies, 4 hours for planned.
""",

    "niva_bupa_policy_schedule.txt": """INSURER POLICY SCHEDULE: NIVA BUPA HEALTH INSURANCE
Insurer: Niva Bupa Health Insurance Co. Ltd. (formerly Max Bupa)
IRDAI Registration No.: 145 (Standalone Health Insurance)
TPA: In-house claims processing

PRODUCT PORTFOLIO:
1. Niva Bupa ReAssure 2.0
   - Plan Type: Individual / Family Floater
   - Sum Insured Options: Rs. 3,00,000 / Rs. 5,00,000 / Rs. 10,00,000 / Rs. 20,00,000 / Rs. 50,00,000 / Rs. 1,00,00,000
   - Room Rent: No sub-limit for any Sum Insured tier.
   - Co-payment: Nil (no mandatory co-pay for any age group).
   - No Claim Bonus: 20% increase per claim-free year (max 100%).
   - Modern Treatment: Covers robotic surgery, HIFU, immunotherapy.

2. Niva Bupa Health Companion
   - Plan Type: Individual / Family Floater (base plan)
   - Sum Insured: Rs. 2,00,000 / Rs. 3,00,000 / Rs. 5,00,000
   - Room Rent: Rs. 5,000/day for SI up to Rs. 3L. 1% of SI for Rs. 5L.
   - Co-payment: Nil below 60. 20% for 60+.
   - Cataract: Rs. 40,000/eye sub-limit.
   - Dialysis: Rs. 2,000/session, max 24 sessions/year.

3. Niva Bupa Senior First
   - Entry Age: 61-75 (renewable lifelong)
   - Sum Insured: Rs. 2,00,000 / Rs. 5,00,000 / Rs. 10,00,000
   - Co-payment: 20% mandatory
   - PED covered after 36 months (reduced from standard 48)
   - Annual Health Check-up: Included

NETWORK: 8,500+ network hospitals.
Cashless Pre-Auth TAT: 1 hour for all cases.
SPECIAL: No sub-limit on room rent across all ReAssure plans — unique selling point.
""",

    "care_health_policy_schedule.txt": """INSURER POLICY SCHEDULE: CARE HEALTH INSURANCE
Insurer: Care Health Insurance Ltd. (formerly Religare Health Insurance)
IRDAI Registration No.: 148 (Standalone Health Insurance)
TPA: In-house

PRODUCT PORTFOLIO:
1. Care Supreme
   - Plan Type: Individual / Family Floater
   - Sum Insured: Rs. 5,00,000 / Rs. 10,00,000 / Rs. 20,00,000 / Rs. 50,00,000 / Rs. 1,00,00,000 / Rs. 3,00,00,000 / Rs. 6,00,00,000
   - Room Rent: No sub-limit for all SI tiers.
   - Co-payment: Nil.
   - Unlimited Restoration: Sum Insured restored unlimited times for unrelated illness.
   - Maternity Cover: Rs. 30,000 normal / Rs. 50,000 C-section (after 36-month wait).

2. Care Advantage
   - Plan Type: Individual / Family Floater (affordable tier)
   - Sum Insured: Rs. 3,00,000 / Rs. 4,00,000 / Rs. 5,00,000
   - Room Rent: 1% of SI per day
   - Co-payment: 5% mandatory for all age groups
   - Ambulance: Rs. 2,000 per event
   - Cataract: Rs. 40,000/eye, Knee: Rs. 1,50,000/knee

3. Care Freedom (Senior Plan)
   - Entry Age: 55-80 years
   - Sum Insured: Rs. 3,00,000 / Rs. 5,00,000 / Rs. 10,00,000
   - Co-payment: 25% mandatory
   - Pre-policy medical screening: Mandatory
   - PED: Covered after 48 months (standard), waived with 20% loading

NETWORK: 9,000+ network hospitals.
Cashless Pre-Auth TAT: Within 1 hour.
""",

    "bajaj_allianz_policy_schedule.txt": """INSURER POLICY SCHEDULE: BAJAJ ALLIANZ GENERAL INSURANCE
Insurer: Bajaj Allianz General Insurance Co. Ltd.
IRDAI Registration No.: 113 (General Insurance)
TPA: Health India Insurance TPA / In-house

PRODUCT PORTFOLIO:
1. Bajaj Allianz Health Guard
   - Plan Type: Individual / Family Floater
   - Sum Insured: Rs. 2,00,000 / Rs. 3,50,000 / Rs. 5,00,000 / Rs. 10,00,000 / Rs. 15,00,000 / Rs. 50,00,000
   - Silver / Gold / Platinum variants
   - Room Rent: Silver: Rs. 4,000/day; Gold: 1% of SI; Platinum: No sub-limit
   - Co-payment: Nil for Gold/Platinum. Silver: 10% for ages 46-55, 20% for 56+.
   - Organ Donor Cover: Expenses for organ donor's hospitalization up to Rs. 1,00,000.

2. Bajaj Allianz Star Package Policy
   - Plan Type: Individual (value plan)
   - Sum Insured: Rs. 1,00,000 / Rs. 2,00,000 / Rs. 3,00,000
   - Room Rent: Rs. 3,000/day
   - Mandatory 20% co-payment
   - Cataract: Rs. 25,000/eye
   - Ambulance: Rs. 1,500/event

3. Bajaj Allianz Group Health Insurance
   - Plan Type: Group (Corporate)
   - Sum Insured: Customizable per client (typical Rs. 3L-10L)
   - No waiting period (initial, specific disease, PED all waived)
   - Room Rent: Single occupancy (no sub-limit)
   - Co-payment: Nil for network. 20% for non-network.
   - Maternity: Optional, Rs. 40,000-75,000 based on group size
   - Domiciliary Treatment: Covered for groups with 500+ lives

NETWORK: 11,000+ network hospitals.
Cashless Pre-Auth TAT: 2 hours for planned, 1 hour for emergency.
""",

    "new_india_assurance_policy_schedule.txt": """INSURER POLICY SCHEDULE: NEW INDIA ASSURANCE
Insurer: The New India Assurance Co. Ltd. (Public Sector)
IRDAI Registration No.: 190 (General Insurance — Government)
TPA: TPA India / Medi Assist / Paramount Health Services

PRODUCT PORTFOLIO:
1. New India Cashless Mediclaim Policy (2012)
   - Plan Type: Individual / Family
   - Sum Insured: Rs. 1,00,000 / Rs. 2,00,000 / Rs. 3,00,000 / Rs. 5,00,000
   - Room Rent: 1% of SI per day
   - ICU: 2% of SI per day
   - Co-payment: Nil below 60. 10% for 60-70. 20% for 70-80.
   - Ambulance: Rs. 1,000 per hospitalization
   - Pre-hospitalization: 30 days; Post-hospitalization: 60 days

2. New India Senior Citizens Mediclaim Policy
   - Entry Age: 60-80 years (renewable lifelong up to 90)
   - Sum Insured: Rs. 1,00,000 / Rs. 1,50,000 / Rs. 2,00,000 / Rs. 3,00,000
   - Co-payment: 10% for ages 60-70. 20% for 70-80.
   - Room Rent: Rs. 3,000/day for SI up to Rs. 2L; Rs. 4,000/day for higher SI.
   - Cataract: Rs. 30,000 per eye
   - PED: Covered from inception with 50% co-pay for first 4 years.

3. New India Group Mediclaim Policy
   - Plan Type: Group (Government / PSU / Corporate)
   - Sum Insured: As per scheme (typically Rs. 3,00,000 - Rs. 7,50,000)
   - Waiting period: All waived
   - Room Rent: As per employer scheme (typically General/Semi-Private ward)
   - Co-payment: Nil for government employees. 10% for others.

NETWORK: 8,000+ network hospitals (extensive coverage in Tier 2/3 cities).
Cashless Pre-Auth TAT: 2-4 hours (government insurer TAT tends to be slower).
NOTE: As a public sector insurer, New India Assurance follows government-mandated
claim settlement guidelines with emphasis on social coverage.
""",

    "united_india_insurance_policy_schedule.txt": """INSURER POLICY SCHEDULE: UNITED INDIA INSURANCE
Insurer: United India Insurance Co. Ltd. (Public Sector)
IRDAI Registration No.: 191 (General Insurance — Government)
TPA: MDIndia Health Insurance TPA / Heritage Health TPA

PRODUCT PORTFOLIO:
1. United India Individual Mediclaim Policy
   - Plan Type: Individual / Family
   - Sum Insured: Rs. 1,00,000 / Rs. 2,00,000 / Rs. 3,00,000 / Rs. 5,00,000 / Rs. 10,00,000
   - Room Rent: 1% of SI per day (minimum Rs. 1,000)
   - ICU: 2% of SI per day
   - Co-payment: Nil for ages below 60. 10% for 60-70. 20% for 70+.
   - Ambulance: Rs. 1,500 per hospitalization
   - Day Care: 140+ listed day care procedures covered

2. United India Senior Citizens Policy
   - Entry Age: 61-80 years
   - Sum Insured: Rs. 1,00,000 / Rs. 2,00,000 / Rs. 3,00,000
   - Co-payment: 20% mandatory (non-waivable)
   - Room Rent: Rs. 3,000/day
   - Cataract: Rs. 30,000/eye
   - Knee Replacement: Rs. 1,30,000/knee (lower than IRDAI standard sub-limit)

3. United India Group Insurance Scheme
   - Plan Type: Group (Government employees, PSU, Corporate)
   - Sum Insured: Scheme-dependent (Rs. 2,00,000 - Rs. 5,00,000 typical)
   - All waiting periods waived
   - Room Rent: General ward / semi-private (scheme-dependent)
   - Co-payment: Per scheme rules
   - Government Schemes: Covers CGHS, ECHS, State Government Health Schemes

4. United India Critical Illness Policy
   - Covers 34 listed critical illnesses
   - Lump sum payment on first diagnosis
   - Sum Insured: Rs. 2,00,000 / Rs. 5,00,000 / Rs. 10,00,000
   - Survival period: 30 days post-diagnosis

NETWORK: 7,500+ network hospitals.
Cashless Pre-Auth TAT: 2-4 hours.
NOTE: Strong presence in Southern India (Tamil Nadu, Karnataka, Kerala).
Extensive coverage under government health schemes.
""",
}


def generate_corpus() -> dict[str, int]:
    """Generate the complete synthetic corpus.

    Creates all policy wording, benefit table, IRDAI circular, and
    insurer-specific policy documents in the appropriate subdirectories
    under retrieval/corpus/.

    Returns:
        Dict with counts: {"policy_wordings": N, "benefit_tables": N,
                          "irdai_circulars": N, "insurer_policies": N}
    """
    counts = {}

    # Policy Wordings
    wording_dir = os.path.join(CORPUS_DIR, "policy_wordings")
    os.makedirs(wording_dir, exist_ok=True)
    for filename, content in POLICY_WORDINGS.items():
        filepath = os.path.join(wording_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content.strip() + "\n")
    counts["policy_wordings"] = len(POLICY_WORDINGS)
    logger.info("Generated %d policy wording documents.", counts["policy_wordings"])

    # Benefit Tables
    benefit_dir = os.path.join(CORPUS_DIR, "benefit_tables")
    os.makedirs(benefit_dir, exist_ok=True)
    for filename, content in BENEFIT_TABLES.items():
        filepath = os.path.join(benefit_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content.strip() + "\n")
    counts["benefit_tables"] = len(BENEFIT_TABLES)
    logger.info("Generated %d benefit table documents.", counts["benefit_tables"])

    # IRDAI Circulars
    irdai_dir = os.path.join(CORPUS_DIR, "irdai_circulars")
    os.makedirs(irdai_dir, exist_ok=True)
    for filename, content in IRDAI_CIRCULARS.items():
        filepath = os.path.join(irdai_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content.strip() + "\n")
    counts["irdai_circulars"] = len(IRDAI_CIRCULARS)
    logger.info("Generated %d IRDAI circular documents.", counts["irdai_circulars"])

    # Insurer-Specific Policy Schedules
    insurer_dir = os.path.join(CORPUS_DIR, "insurer_policies")
    os.makedirs(insurer_dir, exist_ok=True)
    for filename, content in INSURER_POLICIES.items():
        filepath = os.path.join(insurer_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content.strip() + "\n")
    counts["insurer_policies"] = len(INSURER_POLICIES)
    logger.info("Generated %d insurer policy documents.", counts["insurer_policies"])

    total = sum(counts.values())
    logger.info("Corpus generation complete: %d total documents.", total)

    return counts


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    result = generate_corpus()
    print(f"\n✅ Corpus generated successfully!")
    print(f"   Policy wordings:    {result['policy_wordings']}")
    print(f"   Benefit tables:     {result['benefit_tables']}")
    print(f"   IRDAI circulars:    {result['irdai_circulars']}")
    print(f"   Insurer policies:   {result['insurer_policies']}")
    print(f"   Total documents:    {sum(result.values())}")
