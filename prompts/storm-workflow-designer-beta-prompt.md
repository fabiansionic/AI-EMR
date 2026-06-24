# Prompt for STORM Workflow Designer Beta

Create a workflow diagram for an AI-based Korean EMR billing and review guide assistant.

The workflow should use the STORM agent/bucket context for:
- Agent ID: `7475416844727144448`
- Primary knowledge bucket ID: `7475416844727144449`
- Primary knowledge bucket name: `Fabian Onboarding AI EMR`

Design goal:
Build a visual workflow that receives de-identified unstructured EMR text, extracts clinically and billing-relevant facts, suggests KCD/EDI code candidates, retrieves relevant Korean medical/review context from the uploaded STORM knowledge bucket, analyzes deduction risk, and returns strict JSON for human review.

Important data context:
- Current primary RAG source: `data/storm_txt/knowledge-data/aihub_71875`
- This contains STORM-ready TXT converted from AIHub 71875 medical knowledge sources and QA data.
- `data/storm_txt/voice-data/aihub_566` is a future enrichment source for medical conversation/transcript language. Do not depend on it unless its TXT/JSON-derived text has been uploaded and retrieved.
- Do not use web search in this workflow. Use selected STORM knowledge buckets only.

Create these workflow stages as separate logical nodes where the Designer supports it:

1. `intake_privacy_gate`
   - Input: raw EMR text from the user.
   - Detect direct identifiers such as names, resident registration numbers, registration numbers, phone numbers, addresses, and other PHI/PII.
   - If identifiers are present, stop normal processing and return privacy failure JSON.
   - If safe, pass sanitized EMR text forward.

2. `emr_section_detector`
   - Detect available EMR sections: chief complaint, present illness/HPI, assessment, physical exam, test results, orders, medications, procedure/operation notes, and nursing notes.
   - Output detected sections and missing sections.

3. `clinical_entity_extractor`
   - Extract symptoms, diagnoses, anatomical site, laterality, severity, duration, prior conservative treatment, procedures, drugs, dose, route, frequency, dates, test/imaging findings, and physician orders.
   - Attach short exact EMR evidence snippets to every extracted item.

4. `coding_candidate_generator`
   - Generate KCD diagnosis-code candidates and EDI procedure/drug/test/material candidates.
   - Do not assign high confidence without direct EMR evidence.
   - Output recommended, uncertain, and needs-review candidates.
   - Include confidence score, supporting evidence, rationale, and uncertainty reason.

5. `rag_query_builder`
   - Build Korean retrieval queries from extracted facts, KCD/EDI candidates, drug names, procedure names, indication terms, conservative-treatment terms, dose/frequency terms, and deduction-risk terms.
   - Produce query groups for diagnosis support, procedure/fee criteria, drug indications, review/deduction cases, and benefit criteria.

6. `review_context_retriever`
   - Retrieve context from the selected STORM knowledge bucket only.
   - Prefer official or curated passages with source name, source type, effective date, related KCD/EDI metadata, and document provenance when available.
   - Include references/citations in downstream output.

7. `deduction_risk_reviewer`
   - Compare EMR evidence and candidate codes against retrieved context only.
   - Identify indication mismatch, missing prerequisite treatment, missing required tests, diagnosis-code mismatch, dose/frequency/duration limits, repeated-claim limits, unsupported drugs/procedures, and insufficient evidence.
   - Assign `HIGH`, `MEDIUM`, `LOW`, or `NEEDS_EVIDENCE`.
   - If retrieved context is absent or weak, mark `NEEDS_EVIDENCE` instead of inventing rules.

8. `documentation_gap_advisor`
   - Provide documentation guidance that could reduce review risk if clinically true.
   - Never suggest adding unsupported or false chart information.
   - Phrase guidance as "document only if clinically true."

9. `json_finalizer`
   - Return strict JSON only.
   - Required top-level fields:
     - `privacy_status`
     - `detected_sections`
     - `recommended_codes`
     - `uncertain_codes`
     - `deduction_warnings`
     - `retrieved_sources`
     - `human_review_required`
     - `human_review_reason`
     - `audit_trail`

Final JSON schema shape:

```json
{
  "privacy_status": "PASS | FAIL | NEEDS_REDACTION",
  "detected_sections": ["string"],
  "recommended_codes": [
    {
      "type": "KCD | EDI",
      "code": "string",
      "name": "string",
      "confidence_score": 0.0,
      "rationale": "string",
      "emr_evidence": ["string"]
    }
  ],
  "uncertain_codes": [
    {
      "type": "KCD | EDI",
      "code": "string",
      "name": "string",
      "confidence_score": 0.0,
      "uncertainty_reason": "string",
      "needed_evidence": ["string"]
    }
  ],
  "deduction_warnings": [
    {
      "risk_level": "HIGH | MEDIUM | LOW | NEEDS_EVIDENCE",
      "target_code": "string",
      "reason": "string",
      "current_emr_evidence": ["string"],
      "missing_evidence": ["string"],
      "actionable_guide": "string",
      "source_passage_ids": ["string"],
      "confidence_score": 0.0
    }
  ],
  "retrieved_sources": [
    {
      "passage_id": "string",
      "source_name": "string",
      "source_type": "MOHW | HIRA | MFDS | KCD_MASTER | EDI_MASTER | AIHUB_71875 | CURATED_CASE | OTHER",
      "effective_date": "YYYY-MM-DD or null",
      "related_codes": ["string"],
      "citation_metadata": "string"
    }
  ],
  "human_review_required": true,
  "human_review_reason": "string",
  "audit_trail": ["string"]
}
```

Safety and behavior constraints:
- This is review-support tooling, not autonomous medical, legal, or reimbursement decision-making.
- Ground deduction-risk findings only in retrieved STORM context.
- Do not invent KCD/EDI codes, review standards, notice numbers, effective dates, or deduction rules.
- Fail closed when privacy status fails or when review context is insufficient.
- Keep web search disabled.
- Include references when retrieved context is used.
