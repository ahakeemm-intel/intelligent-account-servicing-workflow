# IASW — Intelligent Account Servicing Workflow
## Solution Design and Implementation Document

**Candidate:** Adnan  
**Date:** April 2026  
**Submission:** GitHub repository + this document

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Problem Understanding & Scope](#2-problem-understanding--scope)
3. [Solution Architecture](#3-solution-architecture)
4. [Agent Design & Prompt Engineering](#4-agent-design--prompt-engineering)
5. [Assumptions, Constraints & Known Limitations](#5-assumptions-constraints--known-limitations)

---

## 1. Executive Summary

Banking account change requests — name corrections, address updates, date of birth fixes — follow a Maker-Checker workflow that is slow, manual, and costly at scale. Staff manually key in data, a Maker reviews physical documents, and a Checker supervisor re-verifies before the core system is updated. A single request can take hours; errors slip through, and audit trails are incomplete.

The **Intelligent Account Servicing Workflow (IASW)** replaces the human Maker with an AI agent pipeline while preserving the human Checker as the immovable final decision authority. The AI handles the cognitive labour — OCR, cross-referencing, scoring, summarisation — and presents the Checker with a structured, confidence-scored review package. The Checker clicks Approve or Reject; only then does the system write to the core banking platform (RPS).

This prototype demonstrates a complete Legal Name Change flow: a staff member submits a request, uploads a marriage certificate, the AI pipeline extracts and scores the data, and the Checker UI presents a recommendation. The prototype is fully runnable locally with zero cloud API keys (Ollama + SQLite + PyMuPDF) and can be promoted to cloud-grade infrastructure (OpenAI + PostgreSQL + AWS Textract) by changing three environment variables.

---

## 2. Problem Understanding & Scope

### 2.1 The Core Problem

Financial institutions process thousands of account change requests daily. The current process has three structural weaknesses:

| Weakness | Impact |
|---|---|
| Manual data entry and document review | Slow throughput, human error |
| Inconsistent evidence standards across staff | Compliance risk |
| No machine-readable audit trail | Difficult post-hoc review |

The IASW task is to automate the Maker phase while keeping the Checker human — not as a convenience, but as a **regulatory and accountability requirement**.

### 2.2 HITL as a Hard Constraint

The most important design requirement is not a feature — it is a constraint: **the AI must never write to RPS autonomously**. This is enforced architecturally (see §3.4), not just by convention.

### 2.3 Scope of This Prototype

**In scope:**
- Legal Name Change flow, end-to-end
- Marriage Certificate as the supporting document
- Pre-seeded customer C001 (Priya Sharma → Priya Mehta)
- Full pipeline: intake → OCR → extraction → scoring → summary → Checker review → approve/reject → RPS mock write

**Out of scope (schema supports, not implemented):**
- Address, DOB, Contact change types
- Real FileNet, real RPS, real authentication
- Multi-document per request
- Adverse action notifications to customers

### 2.4 Change Type Matrix

| Change Type | Documents Required | AI Verification Task |
|---|---|---|
| **Legal Name** ✅ | Marriage Certificate, Deed Poll | Match bride_name → old name; married_name → new name |
| Address | Utility Bill, Lease, Govt ID | Extract address, verify against requested change |
| Date of Birth | Birth Certificate, Passport | Verify date format and document authenticity |
| Contact / Email | Digital Consent Form | Signature match |

---

## 3. Solution Architecture

### 3.1 Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         STAFF BROWSER                               │
│                                                                     │
│  ┌──────────────────┐    ┌──────────────────┐    ┌───────────────┐  │
│  │  Intake Form     │    │  Request Tracker  │    │ Checker UI    │  │
│  │  (page.tsx)      │    │  (requests/[id])  │    │ (checker/[id])│  │
│  └────────┬─────────┘    └────────┬──────────┘    └──────┬────────┘  │
└───────────┼──────────────────────┼────────────────────────┼──────────┘
            │ SYNC                 │ SYNC (poll)            │ SYNC
            ▼                      ▼                        ▼
┌───────────────────────────────────────────────────────────────────────┐
│                     FastAPI Backend  :8000                            │
│                                                                       │
│  POST /api/v1/requests                  (create change request)       │
│  POST /api/v1/requests/{id}/documents   (upload → 202 immediately)   │
│  GET  /api/v1/requests/{id}             (poll status)                 │
│  GET  /api/v1/checker/pending                                         │
│  GET  /api/v1/checker/requests/{id}                                   │
│  POST /api/v1/checker/requests/{id}/approve   ◄── HITL GATE          │
│  POST /api/v1/checker/requests/{id}/reject                            │
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │              ASYNC BACKGROUND THREAD                          │    │
│  │                                                              │    │
│  │  ┌────────────┐  ┌──────────────────┐  ┌─────────────────┐  │    │
│  │  │ Validation │→ │ Doc Processor    │→ │ Confidence      │  │    │
│  │  │ Agent      │  │ (OCR + LLM       │  │ Scorer          │  │    │
│  │  │            │  │  extraction +    │  │ (fuzzy + LLM    │  │    │
│  │  │ RPS lookup │  │  forgery check)  │  │  semantic)      │  │    │
│  │  └────────────┘  └──────────────────┘  └────────┬────────┘  │    │
│  │                                                  │           │    │
│  │                                        ┌─────────▼────────┐ │    │
│  │                                        │ Summary Generator│ │    │
│  │                                        │ (LLM → checker   │ │    │
│  │                                        │  summary + rec.) │ │    │
│  │                                        └─────────┬────────┘ │    │
│  │                                                  │           │    │
│  │                           DB write: AI_VERIFIED_PENDING_HUMAN│    │
│  └──────────────────────────────────────────────────────────────┘    │
│                                                                       │
│  ┌─────────────────┐  ┌───────────────────┐  ┌────────────────────┐ │
│  │  PostgreSQL /   │  │  FileNet Mock     │  │  Mock RPS          │ │
│  │  SQLite DB      │  │  (filenet_store/) │  │  (in-memory dict)  │ │
│  │  (4 tables)     │  │                   │  │  write gated by    │ │
│  └─────────────────┘  └───────────────────┘  │  checker_decision_ │ │
│                                               │  id                │ │
│                                               └────────────────────┘ │
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │  Observability: Loguru (always-on) + Langfuse (optional)     │    │
│  │  Every agent step, confidence score, and checker action logged│    │
│  └──────────────────────────────────────────────────────────────┘    │
└───────────────────────────────────────────────────────────────────────┘

──── SYNC boundary  (request/response, user-facing latency)
~~~~ ASYNC boundary (background thread, pipeline may take 10-60s)
```

### 3.2 Component Inventory

| Component | Implementation | Role |
|---|---|---|
| **Frontend** | Next.js 14 + Tailwind CSS | Intake form, status tracker, Checker dashboard + review UI |
| **Backend API** | FastAPI (Python 3.12) | REST API, dependency injection, CORS, lifespan |
| **Agent Orchestration** | LangGraph | Stateful directed graph; defines pipeline topology and conditional routing |
| **LLM** | Ollama (local) / OpenAI GPT-4o (cloud) | Field extraction, semantic scoring, forgery heuristics, summary generation |
| **OCR** | PyMuPDF direct text (primary) → Tesseract (fallback) → AWS Textract (cloud) | Text extraction from uploaded documents |
| **Database** | SQLite (local) / PostgreSQL (cloud/docker) | Pending Table and full audit tables |
| **Document Store** | Local filesystem (`filenet_store/`) | FileNet mock — stores archived originals with generated reference IDs |
| **Mock RPS** | In-memory Python dict | Core banking system stub; write path gated by `checker_decision_id` |
| **Observability** | Loguru (file + console) + optional Langfuse | Structured logs for every agent step, DB write, and human decision |

### 3.3 Synchronous vs. Asynchronous Boundaries

| Boundary | Type | Reason |
|---|---|---|
| Frontend → POST `/requests` | **Sync** | Returns request ID immediately; fast DB write |
| Frontend → POST `/documents` | **Sync → 202** | Returns document record immediately; pipeline is non-blocking |
| Agent pipeline execution | **Async background thread** | OCR + LLM calls can take 10–60 seconds; must not block the HTTP server |
| Frontend polling `GET /requests/{id}` | **Sync (repeated)** | Simple status polling; status changes from PROCESSING → AI_VERIFIED_PENDING_HUMAN when pipeline finishes |
| Checker approve/reject | **Sync** | Human-triggered; must return a definitive result including RPS mock response |

### 3.4 HITL Boundary Design

**What the AI can do autonomously:**

| Capability | Notes |
|---|---|
| Extract text from documents (OCR) | PyMuPDF / Tesseract / Textract |
| Parse structured fields (LLM) | Bride name, married name, dates, etc. |
| Cross-reference extracted fields against requested change | Fuzzy + semantic scoring |
| Generate forgery heuristic assessment | LLM reasoning on document content |
| Compute per-field confidence scores | Weighted combination of fuzzy + semantic + forgery flag |
| Generate natural language summary and recommendation | LLM-generated for the Checker |
| Archive documents to FileNet mock | Automatic on upload |
| Stage results to Pending Table | Automatic pipeline step |

**What the AI cannot do:**

| Prohibited Action | Enforcement |
|---|---|
| Write to RPS (core banking) | `write_customer_record()` requires `checker_decision_id` parameter |
| Approve or reject a request | Only exists as a human-triggered HTTP endpoint |
| Modify customer records without a recorded human decision | No code path exists in the agent graph |
| Escalate a FLAG to APPROVED automatically | No conditional edge in the graph leads to approval |

**Technical enforcement mechanism:**

```python
# rps_service.py — the ONLY write path to core banking
def write_customer_record(
    customer_id: str,
    change_type: str,
    new_value: dict,
    checker_decision_id: str,   # ← REQUIRED: validates a human decision exists
) -> dict:
```

The `checker_decision_id` is generated at the moment a Checker clicks Approve in the UI. It is created by `POST /api/v1/checker/requests/{id}/approve`, which creates a `checker_decisions` row in the database first — creating the permanent audit record — and only then calls `write_customer_record` with that ID. There is no code path from any agent node to this function.

### 3.5 Data Model

#### `change_requests` — the Pending Table

| Column | Type | Description |
|---|---|---|
| `id` | UUID (PK) | Request identifier |
| `customer_id` | VARCHAR(50) | e.g. `C001` |
| `change_type` | VARCHAR(20) | `LEGAL_NAME`, `ADDRESS`, `DOB`, `CONTACT` |
| `requested_old_value` | JSON | e.g. `{"name": "Priya Sharma"}` |
| `requested_new_value` | JSON | e.g. `{"name": "Priya Mehta"}` |
| `status` | VARCHAR(40) | `INITIATED` → `PROCESSING` → `AI_VERIFIED_PENDING_HUMAN` → `APPROVED`/`REJECTED` |
| `created_at` | DATETIME | Request submission time |
| `updated_at` | DATETIME | Last status change |

#### `documents`

| Column | Type | Description |
|---|---|---|
| `id` | UUID (PK) | Document identifier |
| `request_id` | UUID (FK) | Links to `change_requests` |
| `document_type` | VARCHAR(50) | e.g. `marriage_certificate` |
| `file_path` | VARCHAR(500) | Archived path in FileNet mock store |
| `original_filename` | VARCHAR(255) | Original upload filename |
| `filenet_reference_id` | VARCHAR(100) | Generated ref e.g. `FN-30DA9919-5FC844AC` |
| `uploaded_at` | DATETIME | Upload timestamp |

#### `verification_results`

| Column | Type | Description |
|---|---|---|
| `id` | UUID (PK) | |
| `request_id` | UUID (FK) | |
| `document_id` | UUID (FK) | |
| `extracted_fields` | JSON | Raw structured extraction e.g. `{"bride_name": "Priya Sharma", "married_name": "Priya Mehta"}` |
| `field_scores` | JSON | Per-field confidence e.g. `{"old_name_match": 0.97, "new_name_match": 0.95, "document_authenticity": 0.85}` |
| `overall_confidence` | FLOAT | Weighted average across all field scores |
| `forgery_check` | VARCHAR(10) | `PASS`, `FLAG`, or `FAIL` |
| `ai_summary` | TEXT | Human-readable summary for the Checker |
| `ai_recommendation` | VARCHAR(20) | `APPROVE`, `REJECT`, or `FLAG_FOR_REVIEW` |
| `verified_at` | DATETIME | Pipeline completion time |

#### `checker_decisions`

| Column | Type | Description |
|---|---|---|
| `id` | UUID (PK) | Decision identifier (also used as HITL gate key in RPS) |
| `request_id` | UUID (FK) | |
| `checker_id` | VARCHAR(100) | Staff identifier (e.g. `CHECKER_001`) |
| `decision` | VARCHAR(10) | `APPROVED` or `REJECTED` |
| `notes` | TEXT | Optional checker notes |
| `decided_at` | DATETIME | Decision timestamp |
| `rps_response` | JSON | Mock RPS write-call response (includes `old_value`, `new_value`, `written_at`) |

---

## 4. Agent Design & Prompt Engineering

### 4.1 Orchestration Framework Choice: LangGraph

**Chosen framework:** LangGraph (LangChain ecosystem)

LangGraph was selected over LangChain LCEL, CrewAI, and LlamaIndex for three reasons:

1. **Stateful directed graph** — LangGraph models the pipeline as a typed state machine with named nodes and explicit edges. Each agent node reads from and writes to a single `RequestState` TypedDict, making data flow auditable and testable in isolation. LCEL chains lack this explicit state; CrewAI is better suited for collaborative multi-agent loops than sequential verification pipelines.

2. **Conditional routing** — The `_should_continue_after_validation` conditional edge allows the pipeline to short-circuit to the summary generator if validation fails (e.g. customer not found), rather than crashing mid-pipeline. This clean error propagation is essential for a regulated system where every outcome — including failures — must produce a structured, logged result.

3. **`ainvoke` async support** — LangGraph's `ainvoke` interface allows the pipeline to run in a thread pool via `asyncio.to_thread`, keeping the FastAPI event loop unblocked even when OCR and LLM calls take tens of seconds.

**Trade-offs considered:**
- LangGraph is more verbose than LCEL for simple chains — acceptable here since the pipeline is not simple.
- CrewAI's agent-to-agent communication model would add unnecessary coordination overhead for a linear verification pipeline.
- LlamaIndex is strong for RAG and retrieval but has no native graph-state model for sequential processing pipelines.

### 4.2 LLM Choice: Ollama (local) / GPT-4o (cloud)

**Default:** Ollama with `llama3` — local, free, no API key required.  
**Cloud option:** OpenAI GPT-4o — switched by setting `LLM_PROVIDER=openai`.

The dual-provider approach was chosen because:
- The prototype must run fully offline (candidate requirement)
- In production, GPT-4o's 128k context window and superior instruction-following give more reliable JSON extraction and semantic reasoning
- LangChain's `ChatOllama` / `ChatOpenAI` share the same `invoke()` interface, so the switch is a single env var

**Trade-offs:**
- `llama3` (7B) produces less reliable JSON extraction than GPT-4o; the extraction nodes handle JSON parse failures gracefully with a raw-text fallback
- `llava` (vision model) for image-based OCR is available but `llama3` (text-only) is the default — adequate for digital PDFs where PyMuPDF extracts clean text directly
- Response variability in smaller local models means confidence scores may be less calibrated than with GPT-4o; the fuzzy string matching baseline (`rapidfuzz`) provides a deterministic floor

### 4.3 Agent Pipeline

```
START → validation_agent → [conditional] → document_processor → confidence_scorer → summary_generator → END
                                   ↓ (if validation fails)
                             summary_generator (error path)
```

#### Node 1: Validation Agent (`nodes/validation.py`)

| | |
|---|---|
| **Responsibility** | Validate intake fields against mock RPS before any document processing |
| **Input** | `RequestState`: `customer_id`, `change_type`, `old_value`, `new_value` |
| **Output** | `rps_record` (fetched customer), `validation_errors` list |
| **Logic** | 1. Look up customer in mock RPS; fail if not found. 2. For LEGAL_NAME: compare `old_value.name` to `rps_record.name` (case-insensitive). 3. Validate `change_type` is in supported set. |
| **Routing** | If `validation_errors` is non-empty → route to summary_generator (error summary). Else → proceed to document_processor. |

**Design note:** Validation runs before OCR to avoid wasting compute on documents for non-existent customers or mismatched old values. This mirrors the human Maker's first step.

#### Node 2: Document Processor (`nodes/document_processor.py`)

| | |
|---|---|
| **Responsibility** | OCR extraction, LLM-structured field parsing, forgery heuristic |
| **Input** | `document_path`, `change_type`, `ocr_raw_text` (empty) |
| **Output** | `ocr_raw_text`, `extracted_fields`, `forgery_result` |

**OCR strategy (layered):**
1. PyMuPDF direct text extraction — fast, zero dependencies, works for digital PDFs
2. Tesseract OCR — for scanned / image-based PDFs and image files
3. AWS Textract — production-grade, cloud only

**LLM extraction prompt (LEGAL_NAME):**

```
You are a document analysis assistant for a bank.
Extract the following fields from this marriage certificate / legal name change document text.
Return ONLY valid JSON with these exact keys:
{
  "bride_name": "<full name before marriage or old legal name>",
  "married_name": "<full name after marriage or new legal name>",
  "document_date": "<date on the document, YYYY-MM-DD or as found>",
  "issuing_authority": "<court, registrar, or authority name if present>",
  "document_number": "<certificate or reference number if present>"
}
If a field is not found, use null.
Document text: [OCR_TEXT]
```

**Design rationale:** Asking for `null` explicitly prevents the model from hallucinating values for absent fields. The `issuing_authority` and `document_number` fields contribute to authenticity scoring.

**Forgery detection prompt:**

```
You are a document fraud detection assistant for a regulated bank.
Analyse the following OCR text extracted from a document and assess authenticity.

Look for these red flags:
- Inconsistent date formats or impossible dates
- Misspelled official terms (e.g. "Registar" instead of "Registrar")
- Missing mandatory fields for the document type
- Unusual or suspicious formatting patterns
- Absence of official reference numbers

Return ONLY valid JSON:
{
  "result": "PASS" | "FLAG" | "FAIL",
  "reasons": ["<reason 1>", ...],
  "confidence": <0.0 to 1.0>
}
```

**Design rationale:** LLM-based forgery detection is a heuristic, not a forensic tool. The prompt deliberately asks for specific named red flags to constrain the model's reasoning to the domain. The `reasons` field is surfaced in the Checker UI, giving the human decision context.

#### Node 3: Confidence Scorer (`nodes/confidence_scorer.py`)

| | |
|---|---|
| **Responsibility** | Compute per-field match confidence between extracted data and requested change |
| **Input** | `extracted_fields`, `old_value`, `new_value`, `forgery_result` |
| **Output** | `field_scores` (dict), `overall_confidence` (float) |

**Scoring approach — three layers:**

1. **Fuzzy string similarity** (`rapidfuzz.fuzz.token_sort_ratio`): robust to word order differences, minor OCR errors, and middle name omissions. Token sort ratio is preferred over simple ratio because `"Priya Sharma"` and `"Sharma Priya"` should score high.

2. **LLM semantic scoring** (invoked only when fuzzy score < 0.90): handles cases fuzzy matching cannot — OCR character substitutions (e.g. `0` → `O`), culturally valid name variations (e.g. `Priya` vs `Priyanka`), or hyphenated surnames. The LLM returns a `{match: bool, confidence: float, reasoning: string}` JSON.

3. **Forgery-to-score conversion**: `PASS → 1.0`, `FLAG → 0.65`, `FAIL → 0.10`. This is a hard signal: a `FAIL` forgery result caps document authenticity at 10%, pulling the overall confidence below the FLAG threshold regardless of name match quality.

**Weighted average (LEGAL_NAME):**

| Field | Weight | Rationale |
|---|---|---|
| `old_name_match` (bride name ↔ old value) | 0.35 | Confirms document is about this person |
| `new_name_match` (married name ↔ new value) | 0.45 | The primary change being requested |
| `document_authenticity` (forgery score) | 0.20 | Hard constraint on document quality |

**Thresholds (configurable via env):**

| Range | Label | Effect on recommendation |
|---|---|---|
| ≥ 90% | PASS | AI recommends APPROVE |
| 60–89% | FLAG | AI recommends FLAG_FOR_REVIEW |
| < 60% | FAIL | AI recommends REJECT |

#### Node 4: Summary Generator (`nodes/summary_generator.py`)

| | |
|---|---|
| **Responsibility** | Generate a human-readable review summary and recommended action for the Checker |
| **Input** | All prior state: `extracted_fields`, `field_scores`, `overall_confidence`, `forgery_result`, `old_value`, `new_value` |
| **Output** | `ai_summary` (text), `ai_recommendation` (enum) |

**Prompt design:**

```
You are an AI assistant helping a banking compliance checker review an account change request.
Generate a concise, professional review summary for the checker based on the data below.
Include: what was found in the document, how well it matches the request, and a clear recommended action.

Change Request: [...]
Document Extraction Results: [JSON]
Confidence Scores: [JSON with % formatting]
Overall Confidence: 97%
Forgery Check: PASS

Return ONLY valid JSON:
{
  "summary": "<2-4 sentence professional summary>",
  "recommendation": "APPROVE" | "REJECT" | "FLAG_FOR_REVIEW",
  "recommendation_reason": "<one sentence>"
}
```

**Rule-based fallback:** If the LLM call fails (e.g., Ollama not running), the node generates a deterministic summary from the numeric scores using `_rule_based_summary()`. This ensures the Checker UI is never blank — even without LLM connectivity, a Checker can see the scores and make a decision.

**Recommendation override safety:** The node computes `fallback_rec` from thresholds before calling the LLM. If the LLM returns a recommendation that doesn't match the signal (e.g., LLM says APPROVE but forgery check = FAIL), the forgery result takes precedence — `FAIL` forgery always → `REJECT`, regardless of name match scores.

### 4.4 Example Output (Expected with Live Ollama)

For the demo scenario (C001, Priya Sharma → Priya Mehta, sample marriage certificate):

```json
{
  "extracted_fields": {
    "bride_name": "Priya Sharma",
    "married_name": "Priya Mehta",
    "document_date": "2024-07-14",
    "issuing_authority": "Bandra Sub-Registrar Office, Mumbai",
    "document_number": "MC/MH/2024/07/004892"
  },
  "field_scores": {
    "old_name_match": 0.97,
    "new_name_match": 0.95,
    "document_authenticity": 0.85
  },
  "overall_confidence": 0.944,
  "forgery_check": "PASS",
  "ai_summary": "Marriage Certificate verified. Bride name 'Priya Sharma' matches the current RPS record. Married name 'Priya Mehta' matches the requested new name. Document issued by Bandra Sub-Registrar Office, Mumbai on 14 July 2024 with reference number MC/MH/2024/07/004892. Confidence: 94%. Recommended: Approve.",
  "ai_recommendation": "APPROVE"
}
```

---

## 5. Assumptions, Constraints & Known Limitations

### 5.1 Assumptions

| Assumption | Justification |
|---|---|
| **Scope: Legal Name Change only** | The task explicitly recommends this as the minimum viable flow. The schema and service layer support all four change types. |
| **No authentication** | Checker is identified by a free-text `checker_id` field. In production, this integrates with bank SSO/LDAP. The design clearly separates the auth concern — `checker_id` is stored on every decision record, making it easy to add real identity later. |
| **Mock RPS is pre-seeded** | Customer C001 (Priya Sharma) is pre-loaded in memory at startup. In production, the Validation Agent would call an authenticated RPS lookup API. |
| **Single document per request** | The schema supports multiple documents (one-to-many relationship) but the pipeline processes only the most recently uploaded document. Multiple-document scenarios (e.g., Deed Poll + Gazette) are an extension. |
| **PDF is digital (not scanned)** | The sample marriage certificate is a digitally-generated PDF. The OCR layer is prepared for scanned images (Tesseract / Textract) but the demo path uses PyMuPDF direct extraction, which is faster and more reliable for this document type. |
| **Ollama model availability** | Assumes `ollama pull llama3` has been run before the demo. The system degrades gracefully if Ollama is unavailable — OCR succeeds, LLM extraction falls back to raw text, confidence scoring uses fuzzy matching only. |

### 5.2 Technical Constraints

| Constraint | Impact | Mitigation |
|---|---|---|
| **Synchronous LLM calls in LangGraph nodes** | LangGraph nodes are synchronous functions; calling `llm.invoke()` blocks the worker thread | Pipeline runs in `asyncio.to_thread`, keeping the FastAPI event loop free |
| **SQLite single-writer limitation** | Concurrent requests in SQLite can cause write-lock contention | The request route commits and releases before the background task starts; the background task uses its own session. For production: PostgreSQL (zero-latency concurrent writes). |
| **LLM JSON reliability** | Smaller local models (llama3 7B, mistral) sometimes produce malformed JSON | All LLM response parsers strip markdown fences, catch `json.JSONDecodeError`, and return a deterministic fallback. No unhandled exception can propagate from an LLM response. |
| **Forgery detection is heuristic** | LLM cannot detect pixel-level forgeries or metadata tampering | The forgery result is clearly labelled as a heuristic ("AI-assisted") in the Checker UI. The Checker remains responsible for the final verification. |
| **60-second Ollama timeout** | If the model is slow (CPU inference), requests will wait up to 60s | Configurable via code; background task has a 300s total timeout before it writes a `FLAG_FOR_REVIEW` result. |

### 5.3 Known Limitations

1. **No vector search / semantic retrieval**: No RAG or vector store is used. For the Legal Name Change flow, deterministic field extraction + fuzzy scoring is sufficient. A vector store would add value for evidence retrieval across historical decisions (e.g., "find all similar fraud-flagged documents").

2. **No real-time fraud network**: The forgery heuristic is document-local only. A production system would cross-reference document numbers, issuing authorities, and dates against known-fraud registries.

3. **Frontend polling (no websockets)**: The status tracker page polls `GET /requests/{id}` every 3 seconds. For production, websockets or server-sent events would give instant push updates.

4. **No retry mechanism for failed pipelines**: If the pipeline crashes (e.g., LLM timeout), the request status remains `PROCESSING` rather than `FAILED`. A production system would add a celery/background job with retry logic and dead-letter handling.

5. **No image forgery detection**: The system only analyses OCR text. A production system would pass the document image through a vision model (e.g., `llava`, GPT-4o vision) to detect visual anomalies — stamps, signatures, alignment, pixel artifacts.

### 5.4 Production Readiness Path

A summary of what changes for each layer when moving from prototype to production:

| Layer | Prototype | Production |
|---|---|---|
| Auth | `checker_id` free text | Bank SSO/LDAP JWT; `checker_id` validated against AD |
| LLM | Ollama llama3 (local) | GPT-4o or fine-tuned document model via Azure OpenAI |
| OCR | PyMuPDF (digital) / Tesseract (scanned) | AWS Textract or Google Document AI (SLA-backed) |
| Database | SQLite | PostgreSQL with Alembic migrations, connection pooling |
| Document Store | Local filesystem (`filenet_store/`) | FileNet / SharePoint / S3 via real API |
| Core Banking | In-memory dict | Authenticated RPS API with TLS mutual auth |
| Observability | Loguru file/console | Langfuse + Datadog APM + SIEM integration |
| Pipeline reliability | Background thread, single attempt | Celery + Redis, retry with exponential backoff, dead-letter queue |
| Scaling | Single uvicorn process | Kubernetes + horizontal pod autoscaling on queue depth |

---

## Appendix: Technical Stack Justification

| Layer | Choice | Justification |
|---|---|---|
| **Frontend** | Next.js 14 + Tailwind CSS | App Router provides clean file-based routing for the intake / checker separate surfaces; Tailwind enables rapid UI iteration without a component library dependency |
| **Backend** | FastAPI (Python 3.12) | Native async support for non-blocking I/O; automatic OpenAPI docs; Pydantic v2 models for validation; aligns with the Python ML/LLM ecosystem |
| **Orchestration** | LangGraph | Explicit typed state graph; conditional routing; `ainvoke` async; auditable node-by-node execution — see §4.1 for full justification |
| **LLM** | Ollama (llama3) local / OpenAI GPT-4o cloud | Dual-mode: zero-API-key local demo; production-grade cloud option — see §4.2 for full justification |
| **OCR** | PyMuPDF → Tesseract → Textract | Layered strategy prioritises speed and cost (free local) over accuracy (paid cloud); Textract used only when `OCR_PROVIDER=textract` |
| **Vector Store** | Not used | Out of scope for single-document, single-change-type prototype. Would add pgvector for historical evidence similarity in production. |
| **Database** | SQLite (local) / PostgreSQL (cloud) | Single env var switch (`DB_TYPE`); SQLAlchemy async abstracts the difference; SQLite enables zero-setup local development |
| **Document Store** | Local filesystem | Stand-in for FileNet; maintains the same interface (archive + reference ID) so the swap is one service class |
| **Observability** | Loguru (always-on) + Langfuse (optional) | Loguru provides structured file/console logs for all agent steps, checker decisions, and RPS writes with zero extra infrastructure; Langfuse adds LLM-specific tracing (token counts, latency, prompt versions) when `LANGFUSE_ENABLED=true` |
