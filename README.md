# AI-EMR

AI-EMR is a prototype workspace for an AI-assisted Korean EMR billing and review guide system. The target system analyzes de-identified, unstructured EMR text, extracts likely KCD diagnosis codes and EDI billing/procedure/drug codes, retrieves relevant review standards through RAG, and returns structured guidance about deduction risk and missing documentation.

This repository currently contains AIHub data download/preparation scripts, STORM-ready Markdown source files, and draft STORM workflow artifacts.

## Project Goal

The intended assistant should:

- Accept de-identified EMR text such as chief complaint, present illness, physician orders, procedure records, operation notes, and nursing notes.
- Extract billing-relevant clinical facts with direct EMR evidence snippets.
- Suggest candidate KCD and EDI codes with confidence scores.
- Retrieve relevant Korean review standards and medical references through STORM/RAG.
- Analyze deduction risk only from retrieved context.
- Return strict JSON with recommended codes, uncertain codes, deduction warnings, retrieved sources, and human-review flags.

The system is review-support tooling. It should not make autonomous medical, legal, or reimbursement decisions.

## Repository Layout

```text
.
├── README.md
├── config/
│   ├── aihub_datasets.tsv
│   └── storm.json
├── data/
│   └── storm_md/
│       └── aihub_71875/
│           └── sources/
│               ├── en_international_guidelines/
│               ├── en_journals/
│               ├── en_online_medical_sites/
│               ├── kr_journals/
│               ├── kr_medical_textbooks/
│               ├── kr_misc/
│               ├── kr_online_medical_sites/
│               └── kr_society_guidelines/
├── scripts/
│   ├── aihub_direct.py
│   ├── download_aihub.sh
│   ├── prepare_storm_jsonl.py
│   ├── prepare_storm_markdown.py
│   ├── prepare_storm_text.py
│   ├── run_storm_validation.py
│   ├── upload_storm_markdown_sources.py
│   ├── upload_storm_sources.py
│   └── upload_storm_text_sources.py
├── storm-create-workflow.json
└── storm-workflow.json
```

## Current Markdown Sources

The STORM Markdown source tree is under:

```text
data/storm_md/aihub_71875/sources/
```

Current source groups include:

- `kr_society_guidelines`
- `kr_misc`
- `kr_medical_textbooks`
- `kr_journals`
- `kr_online_medical_sites`
- `en_international_guidelines`
- `en_journals`
- `en_online_medical_sites`

Files from the current IDE tabs:

| File | Status |
| --- | --- |
| `data/storm_md/aihub_71875/sources/kr_society_guidelines/kr_society_guidelines_part-0002.md` | Found |
| `data/storm_md/aihub_71875/sources/kr_misc/kr_misc_part-0008.md` | Not found |
| `data/storm_md/aihub_71875/sources/kr_misc/kr_misc_part-0004.md` | Found |
| `data/storm_md/aihub_71875/sources/kr_medical_textbooks/kr_medical_textbooks_part-0001.md` | Found |
| `data/storm_md/aihub_71875/sources/kr_journals/kr_journals_part-0002.md` | Found |

At the time of this README update, `kr_misc` contains `kr_misc_part-0001.md` through `kr_misc_part-0005.md`; `kr_misc_part-0008.md` is not present at that path.

## Target Workflow

The recommended STORM workflow should be staged like this:

1. `privacy_and_input_gate`
   Validate de-identification, detect EMR sections, and fail closed if direct identifiers are present.

2. `emr_entity_extractor`
   Extract symptoms, diagnoses, anatomical sites, laterality, duration, prior treatment, procedures, drugs, tests, and orders with evidence snippets.

3. `coding_candidate_generator`
   Generate KCD and EDI candidates with confidence scores, rationale, uncertainty reasons, and supporting EMR evidence.

4. `rag_query_builder`
   Build Korean retrieval queries from candidate codes, clinical terms, procedure names, drug names, and review-risk concepts.

5. `review_standard_retriever`
   Retrieve relevant context from STORM buckets, preferring official or curated sources with effective dates and related-code metadata.

6. `deduction_risk_reviewer`
   Compare EMR evidence and candidate codes against retrieved standards. Identify indication mismatch, missing prerequisite treatment, unsupported diagnosis-code combinations, dose/frequency limits, and other review risks.

7. `documentation_gap_advisor`
   Suggest EMR documentation improvements only when clinically true. The workflow must not encourage fabrication.

8. `json_finalizer`
   Return strict JSON with recommended codes, uncertain codes, deduction warnings, retrieved sources, human-review requirements, and an audit trail.

## Expected JSON Output

```json
{
  "privacy_status": "PASS",
  "recommended_codes": [
    {
      "type": "KCD",
      "code": "M22.46",
      "name": "슬개골의 연화증, 아래다리",
      "confidence_score": 0.82,
      "rationale": "EMR evidence supports right knee pain and cartilage weakness.",
      "emr_evidence": ["오른쪽 무릎 통증", "연골 약화 소견"]
    }
  ],
  "uncertain_codes": [],
  "deduction_warnings": [
    {
      "risk_level": "HIGH",
      "target_code": "EDI_XXXXXX",
      "reason": "Retrieved review context indicates missing prerequisite conservative-treatment documentation.",
      "current_emr_evidence": ["오른쪽 무릎 통증"],
      "missing_evidence": ["4주 이상 보존적 치료 후 호전 없음"],
      "actionable_guide": "If clinically true, document the duration and outcome of conservative treatment.",
      "source_passage_ids": ["passage-001"],
      "confidence_score": 0.76
    }
  ],
  "retrieved_sources": [
    {
      "passage_id": "passage-001",
      "source_name": "HIRA review guideline",
      "source_type": "HIRA",
      "effective_date": null,
      "related_codes": ["M22.46", "EDI_XXXXXX"],
      "citation_metadata": "source metadata from STORM bucket"
    }
  ],
  "human_review_required": true,
  "human_review_reason": "High deduction risk or insufficient official review evidence.",
  "audit_trail": [
    "Validated de-identification.",
    "Extracted entities from EMR.",
    "Retrieved review context.",
    "Generated evidence-grounded risk analysis."
  ]
}
```

## AIHub Download

AIHub dataset downloads use the official `aihubshell` CLI. The script in `scripts/download_aihub.sh` installs that CLI locally under `tools/` and saves downloaded datasets under `data/aihub/`.

There is also a native Python alternative at `scripts/aihub_direct.py`. It uses the same AIHub HTTPS endpoints as `aihubshell`, but does not require the AIHub shell script, Rosetta, GNU grep, or Linux-specific merge commands.

AIHub requirements:

- An AIHub account
- An issued AIHub API key
- Download/access approval for each dataset from the dataset detail page
- Enough free disk space for 2-3x the compressed dataset size during download
- Linux/WSL is recommended by AIHub. On macOS, `aihubshell` may require GNU command-line tools because the stock BSD `grep` does not support `grep -P`.

The target datasets are listed in `config/aihub_datasets.tsv`.

```bash
# Show configured datasets.
./scripts/download_aihub.sh info

# Install/update the official aihubshell downloader locally.
./scripts/download_aihub.sh install

# List AIHub file keys for each configured dataset.
./scripts/download_aihub.sh list-files

# Download all configured datasets into data/aihub/.
./scripts/download_aihub.sh download

# Download one dataset.
./scripts/download_aihub.sh download 71487

# Download selected file keys from one dataset.
./scripts/download_aihub.sh download 71487 12345,67890
```

Native Python alternative:

```bash
python3 scripts/aihub_direct.py list 71875
python3 scripts/aihub_direct.py download 71875
python3 scripts/aihub_direct.py download 71875 556391
```

The script auto-loads `.env` from the repository root. Use either variable name:

```bash
AIHUB_API_KEY='your-api-key'
```

or:

```bash
AIHUB_APIKEY='your-api-key'
```

On macOS, run downloads from a Linux machine/container, WSL, or a shell where GNU grep is first on `PATH`.

Dataset `566` is marked by AIHub as online safe-zone data, so local API download may be unavailable until the safe-zone access flow is approved.

## STORM Notes

The local STORM CLI can manage agents, buckets, documents, prompts, workflows/order sheets, DSL validation, and deployments. Based on local CLI help, STORM can support this project by:

- Uploading prepared source documents into buckets.
- Retrieving RAG context with `storm context`.
- Managing prompt recipes with `storm prompt`.
- Linting and pushing workflow/order-sheet JSON with `storm workflow`.
- Compiling or validating TypeScript DSL workflows with `storm dsl`.
- Refining local order sheets with `storm arbiter refine`.

STORM does not appear to automatically parse Korean HWP/PDF notices, maintain official Korean medical master data, guarantee source freshness, or validate medical/reimbursement correctness by itself. Those responsibilities need upstream ingestion, metadata policy, workflow prompts, validation, and human review.

Example validation commands:

```bash
storm workflow lint storm-workflow.json
storm workflow lint storm-create-workflow.json
```

Example deployment flow:

```bash
storm workflow diff <agent-id> storm-workflow.json
storm workflow push <agent-id> storm-workflow.json
storm deploy <agent-id> --env dev --memo "AI-EMR billing and review workflow"
```

## Safety And Review Policy

- Use de-identified EMR data only.
- Ground deduction-risk findings in retrieved source context.
- Mark low-confidence or unsupported findings as insufficient evidence.
- Require human review for high-risk, ambiguous, unsupported, or policy-sensitive claims.
- Do not generate documentation guidance that implies adding clinically false information.
