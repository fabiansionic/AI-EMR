# AI-EMR

AI-EMR is a prototype workspace for an AI-assisted Korean EMR billing and review guide system. The target system analyzes de-identified, unstructured EMR text, extracts likely KCD diagnosis codes and EDI billing/procedure/drug codes, retrieves relevant review standards through RAG, and returns structured guidance about deduction risk and missing documentation.

The repository is organized around two data roles:

- `knowledge-data`: curated medical knowledge, review-support references, and QA material used as the main RAG knowledge base.
- `voice-data`: medical speech/transcript material intended to add realistic patient-care and medical-consultation language once AIHub safe-zone access exposes downloadable TXT/JSON files.

The system is review-support tooling. It should not make autonomous medical, legal, or reimbursement decisions.

## Data Layout

```text
data/
├── aihub/
│   ├── knowledge-data/
│   │   └── aihub_71875/
│   │       └── 09.필수의료_의학지식_데이터/
│   └── voice-data/
│       └── aihub_566/
├── storm/
│   ├── knowledge-data/
│   │   └── aihub_71875/
│   │       ├── manifest.jsonl
│   │       ├── qa/
│   │       └── sources/
│   └── voice-data/
│       └── aihub_566/
├── storm_txt/
│   ├── knowledge-data/
│   │   └── aihub_71875/
│   │       ├── manifest/
│   │       ├── qa/
│   │       └── sources/
│   └── voice-data/
│       └── aihub_566/
└── storm_md/
    └── aihub_71875/
```

`storm_txt/` is the active STORM ingestion format because STORM accepts `.txt` while Markdown is not a supported upload extension in the current parsing architecture. `storm_md/` is retained as an intermediate/archive for now, but it is not the preferred ingestion target.

## Dataset Inventory

| Dataset | Local group | Current status | Formats | Contribution to the agent |
| --- | --- | --- | --- | --- |
| AIHub 71875, 필수의료 의학지식 데이터 | `knowledge-data` | Downloaded and converted | Raw ZIP, JSONL, TXT | Main medical knowledge base: Korean/English medical references, guidelines, online medical sources, journals, textbooks, and department QA pairs. This is the primary RAG source for code rationale, review-standard retrieval, and clinical grounding. |
| AIHub 71487, 의료/법률 전문 서적 말뭉치 | `knowledge-data` | Listed in config, not currently present locally | Expected text/corpus files after approval | Future expansion source for medical/legal language and reimbursement-adjacent reasoning. |
| AIHub 566, 의료 분야 음성 데이터 | `voice-data` | Folder prepared; API/file list currently unavailable | Target: TXT and JSON only. Audio WAV/M4A intentionally skipped for now. | Future source of realistic patient-care speech, consultation transcripts, speaker/utterance labels, normalized text, speech acts, and morpheme annotations. Useful for making retrieval and extraction robust to conversational EMR-adjacent Korean. |

## AIHub 566 Voice-Data Plan

For RAG, download only transcript and label files when AIHub exposes file keys:

- Keep `.txt` transcripts as direct RAG text.
- Convert `.json` labels into readable `.txt` under `data/storm_txt/voice-data/aihub_566/`.
- Skip `.wav` and `.m4a` for this phase. The dataset already includes transcripts, and audio transcription would add time and compute cost without improving the initial text RAG corpus.

The public AIHub page describes dataset 566 as healthcare audio/text data with `TXT`, `WAV`, `M4A`, and JSON labels. It includes patient-care data, 119 emergency-center data, and call-center consultation data. The JSON labels are expected to contain metadata such as source filename, media/source type, date, medical subject, speaker information, sentence text, normalized text, speech act, and morpheme analysis.

Current limitation: dataset 566 is an online safe-zone dataset. The AIHub API and official `aihubshell` currently return no downloadable file tree for this workspace/API key, so TXT/JSON-only file keys are not available yet. The prepared voice folders are intentionally empty except for placeholders.

## Current STORM Sources

The active STORM-ready text tree is:

```text
data/storm_txt/knowledge-data/aihub_71875/
```

Important subgroups:

- `sources/kr_society_guidelines`
- `sources/kr_misc`
- `sources/kr_medical_textbooks`
- `sources/kr_journals`
- `sources/kr_online_medical_sites`
- `sources/en_international_guidelines`
- `sources/en_journals`
- `sources/en_online_medical_sites`
- `qa/training_*`
- `qa/validation_*`

The JSONL source tree is:

```text
data/storm/knowledge-data/aihub_71875/
```

These JSONL files preserve structured metadata and QA/source records. The TXT tree is what should be uploaded to STORM for RAG ingestion.

## Target Workflow

The intended assistant should:

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

The workflow diagram should be managed on the STORM platform. Use `storm-workflow.json` as the pushable order sheet, and keep `storm-create-workflow.json` as the same workflow shape for initial setup or recreation.

## AIHub Download

AIHub dataset downloads use the official `aihubshell` CLI. The script in `scripts/download_aihub.sh` installs that CLI locally under `tools/` and routes downloads by dataset:

- Dataset `566` -> `data/aihub/voice-data/aihub_566/`
- Other configured datasets -> `data/aihub/knowledge-data/aihub_<datasetkey>/`

There is also a native Python alternative at `scripts/aihub_direct.py`. It uses the same AIHub HTTPS endpoints as `aihubshell`, but does not require the AIHub shell script, Rosetta, GNU grep, or Linux-specific merge commands.

AIHub requirements:

- An AIHub account
- An issued AIHub API key in `.env`
- Download/access approval for each dataset from the dataset detail page
- Additional safe-zone approval for healthcare safe-zone datasets
- Enough free disk space for 2-3x the compressed dataset size during download

The target datasets are listed in `config/aihub_datasets.tsv`.

```bash
# Show configured datasets.
./scripts/download_aihub.sh info

# Install/update the official aihubshell downloader locally.
./scripts/download_aihub.sh install

# List AIHub file keys.
./scripts/download_aihub.sh list-files 71875
./scripts/download_aihub.sh list-files 566

# Download one knowledge dataset.
./scripts/download_aihub.sh download 71875

# Download selected file keys from one dataset.
./scripts/download_aihub.sh download 71875 12345,67890

# For dataset 566, download only TXT/JSON file keys once AIHub exposes them.
./scripts/download_aihub.sh download 566 TXT_JSON_FILEKEYS_HERE
```

Native Python alternative:

```bash
python3 scripts/aihub_direct.py list 71875
python3 scripts/aihub_direct.py download 71875
python3 scripts/aihub_direct.py download 566 TXT_JSON_FILEKEYS_HERE
```

The scripts auto-load `.env` from the repository root. Use either variable name:

```bash
AIHUB_API_KEY='your-api-key'
```

or:

```bash
AIHUB_APIKEY='your-api-key'
```

## Conversion

Convert raw AIHub 71875 ZIP files into structured JSONL:

```bash
python3 scripts/prepare_storm_jsonl.py
```

Convert Markdown shards to STORM-accepted TXT files:

```bash
python3 scripts/prepare_storm_text.py
```

Convert future AIHub 566 TXT/JSON files into STORM-ready TXT:

```bash
python3 scripts/prepare_voice_text.py
```

Upload TXT sources to STORM:

```bash
python3 scripts/upload_storm_text_sources.py
```

Run a small validation pass against the 71875 QA JSONL:

```bash
python3 scripts/run_storm_validation.py
```
