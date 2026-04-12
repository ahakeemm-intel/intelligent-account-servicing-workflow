# IASW — Intelligent Account Servicing Workflow

An agentic AI prototype that automates document verification for banking account change requests, with a strict **Human-in-the-Loop (HITL)** Checker gate before any core banking write.

---

## Quick Start (Local)

### Prerequisites

| Tool | Install |
|---|---|
| Python 3.12 | `apt install python3.12` |
| Ollama (local LLM) | [ollama.ai](https://ollama.ai) → `ollama pull llama3` |
| Node.js 18+ | [nodejs.org](https://nodejs.org) |

### 1. Clone and set up environment

```bash
git clone <repo-url>
cd agentPrototype
cp .env.example .env          # defaults: sqlite + ollama + tesseract
```

### 2. Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Backend starts at **http://localhost:8000**  
Interactive API docs: **http://localhost:8000/docs**

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend starts at **http://localhost:3000**

### 4. Pull Ollama model (first run only)

```bash
ollama pull llama3      # text tasks
ollama pull llava       # vision / image OCR (optional)
```

---

## Run with Docker (PostgreSQL + full stack)

```bash
# Set your LLM provider in .env (default: ollama — set OLLAMA_BASE_URL if you're running Ollama on the host)
docker compose up --build
```

Services:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- PostgreSQL: localhost:5432

---

## Demo: Legal Name Change Flow

This demonstrates the full end-to-end flow described in the task:

```bash
# 1. Create a change request
curl -X POST http://localhost:8000/api/v1/requests \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "C001",
    "change_type": "LEGAL_NAME",
    "requested_old_value": {"name": "Priya Sharma"},
    "requested_new_value": {"name": "Priya Mehta"}
  }'

# Save the returned "id" as REQUEST_ID

# 2. Upload marriage certificate (AI pipeline triggers automatically)
curl -X POST "http://localhost:8000/api/v1/requests/${REQUEST_ID}/documents" \
  -F "document_type=marriage_certificate" \
  -F "file=@sample_docs/marriage_certificate.pdf"
# Returns 202 immediately. Pipeline runs in background.

# 3. Poll status
curl "http://localhost:8000/api/v1/requests/${REQUEST_ID}"
# status: PROCESSING → AI_VERIFIED_PENDING_HUMAN

# 4. List requests awaiting Checker review
curl "http://localhost:8000/api/v1/checker/pending"

# 5. Review detail (AI summary, confidence scores, FileNet ref)
curl "http://localhost:8000/api/v1/checker/requests/${REQUEST_ID}"

# 6a. Checker APPROVES → triggers mock RPS write
curl -X POST "http://localhost:8000/api/v1/checker/requests/${REQUEST_ID}/approve" \
  -H "Content-Type: application/json" \
  -d '{"checker_id": "CHECKER_001", "decision": "APPROVED", "notes": "Verified and approved."}'

# 6b. Or Checker REJECTS → no RPS write
curl -X POST "http://localhost:8000/api/v1/checker/requests/${REQUEST_ID}/reject" \
  -H "Content-Type: application/json" \
  -d '{"checker_id": "CHECKER_001", "decision": "REJECTED", "notes": "Document unclear."}'
```

Open the UI at **http://localhost:3000** for the full browser experience.

---

## Configuration

All configuration via `.env` (copy from `.env.example`):

| Variable | Default | Options |
|---|---|---|
| `LLM_PROVIDER` | `ollama` | `ollama`, `openai` |
| `OLLAMA_MODEL` | `llama3` | any Ollama model |
| `OPENAI_API_KEY` | — | required if `LLM_PROVIDER=openai` |
| `OCR_PROVIDER` | `tesseract` | `tesseract`, `textract` |
| `DB_TYPE` | `sqlite` | `sqlite`, `postgres` |
| `LANGFUSE_ENABLED` | `false` | `true` to enable LLM tracing |

---

## Project Structure

```
agentPrototype/
├── .env.example                  # Environment variable template
├── docker-compose.yml            # Full stack (postgres + backend + frontend)
├── sample_docs/
│   ├── marriage_certificate.pdf  # Test document (Priya Sharma → Priya Mehta)
│   └── gen_cert.py               # Script to regenerate the PDF
├── backend/
│   ├── requirements.txt
│   ├── Dockerfile
│   └── app/
│       ├── main.py               # FastAPI app factory
│       ├── core/
│       │   ├── config.py         # Pydantic settings (all env vars)
│       │   ├── database.py       # SQLAlchemy (SQLite or PostgreSQL)
│       │   └── logging.py        # Loguru structured logging
│       ├── models/
│       │   ├── db_models.py      # SQLAlchemy ORM (4 tables)
│       │   └── schemas.py        # Pydantic request/response schemas
│       ├── api/routes/
│       │   ├── requests.py       # POST /api/v1/requests
│       │   ├── documents.py      # POST /api/v1/requests/{id}/documents
│       │   ├── checker.py        # Checker review, approve, reject
│       │   └── health.py         # GET /health
│       ├── services/
│       │   ├── rps_service.py    # Mock core banking system (RPS)
│       │   ├── filenet_service.py# Mock document management (FileNet)
│       │   ├── ocr_service.py    # OCR: PyMuPDF (local) or Textract (cloud)
│       │   └── llm_service.py    # LLM: Ollama (local) or OpenAI (cloud)
│       └── agents/
│           ├── graph.py          # LangGraph pipeline (compile + run)
│           ├── state.py          # Pipeline state TypedDict
│           └── nodes/
│               ├── validation.py          # Validate intake vs RPS
│               ├── document_processor.py  # OCR + LLM extraction + forgery
│               ├── confidence_scorer.py   # Fuzzy + semantic scoring
│               └── summary_generator.py   # Human-readable summary
├── frontend/
│   └── src/app/
│       ├── page.tsx              # Intake form
│       ├── requests/[id]/page.tsx# Request status tracker
│       ├── checker/page.tsx      # Checker dashboard (pending list)
│       └── checker/[id]/page.tsx # Checker review + approve/reject
└── docs/
    └── SOLUTION_DESIGN.md        # Full design document
```

---

## Architecture

```
Staff Browser
     │
     ▼
[Next.js Frontend :3000]
     │ POST /api/v1/requests
     │ POST /api/v1/requests/{id}/documents
     │ GET  /api/v1/checker/pending
     │ GET  /api/v1/checker/requests/{id}
     │ POST /api/v1/checker/requests/{id}/approve   ← HITL gate
     │ POST /api/v1/checker/requests/{id}/reject
     ▼
[FastAPI Backend :8000]
     │
     ├── ChangeRequest created → status: INITIATED
     │
     ├── Document uploaded → FileNet mock (filenet_store/)
     │                    → status: PROCESSING
     │
     ├── [Background Thread] LangGraph Pipeline
     │         START
     │           ↓
     │     validation_agent
     │       (RPS lookup, field match)
     │           ↓
     │     document_processor
     │       (PyMuPDF/Textract OCR → LLM extraction → forgery check)
     │           ↓
     │     confidence_scorer
     │       (fuzzy string match + LLM semantic scoring)
     │           ↓
     │     summary_generator
     │       (LLM → human-readable summary + recommendation)
     │         END
     │
     ├── Verification result saved → status: AI_VERIFIED_PENDING_HUMAN
     │
     └── Checker approves
               │
               ├── checker_decisions record created (HITL audit trail)
               ├── rps_service.write_customer_record(checker_decision_id=...)
               └── status: APPROVED
                   (RPS write NEVER called without a checker_decision_id)
```

---

## HITL (Human-in-the-Loop) Guarantee

The AI agent **cannot** write to the core banking system (RPS). The `write_customer_record()` function:
1. Requires a `checker_decision_id` parameter
2. Only called from the `/approve` endpoint  
3. No code path exists from the agent pipeline to RPS

Every approved change is permanently linked to a human decision record in `checker_decisions`.

---

## Pre-seeded Test Data

Customer **C001** is pre-loaded in the mock RPS:

```json
{
  "customer_id": "C001",
  "name": "Priya Sharma",
  "date_of_birth": "1990-03-15",
  "address": "42 Marine Drive, Mumbai, MH 400002"
}
```

Test the scenario: `C001`, Old name: `Priya Sharma`, New name: `Priya Mehta`, upload `sample_docs/marriage_certificate.pdf`.

---

## Health Check

```bash
curl http://localhost:8000/health
# {"status":"ok","db_type":"sqlite","llm_provider":"ollama","ocr_provider":"tesseract"}
```
