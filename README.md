# RAG Interview Backend

Backend take-home for **Palm Mind AI**: two REST APIs for document ingestion and conversational RAG, including LLM-driven interview booking.

Stack: **FastAPI**, **Qdrant**, **PostgreSQL**, **Redis**, **OpenAI-compatible embeddings/chat**. No FAISS, Chroma, UI, or LangChain `RetrievalQAChain`.

---

## Requirements coverage

| Requirement | Implementation |
| --- | --- |
| Upload `.pdf` / `.txt` | Multipart ingest endpoint with type and size validation |
| Extract text | `pypdf` for PDF; encoding-aware decode for TXT |
| Two selectable chunking strategies | `fixed_size` and `sentence_window` |
| Embeddings + vector store | OpenAI embeddings → **Qdrant** (cosine) |
| Metadata in SQL/NoSQL | **PostgreSQL** via SQLAlchemy async (`documents`, `document_chunks`, `interview_bookings`) |
| Custom RAG | Retrieve → prompt → generate in `RAGService` (no RetrievalQAChain) |
| Redis chat memory | Session-scoped message list with TTL |
| Multi-turn queries | History-aware query rewrite before retrieval |
| Interview booking via LLM | Structured extraction of name, email, date, time |
| Store booking info | Fernet-encrypted name/email at rest |
| Clean, typed, modular code | Layered packages, Pydantic v2, full annotations |

---

## Architecture

```
                    ┌─────────────────────────────────────┐
                    │              FastAPI                │
                    │         /api/v1/*  (async)          │
                    └──────────────┬──────────────────────┘
           ┌───────────────────────┼───────────────────────┐
           ▼                       ▼                       ▼
   IngestService              RAGService             BookingService
           │                       │                       │
           │              ┌────────┴────────┐              │
           ▼              ▼                 ▼              ▼
     text extract    query rewrite     Redis memory    Fernet PII
     chunk (×2)      Qdrant search     (chat + draft)  PostgreSQL
     embed           LLM generate
           │              │
           ▼              ▼
     Qdrant vectors   OpenAI / compatible API
     PostgreSQL meta
```

**Ingestion path**

1. Validate file (`.pdf` / `.txt`, size cap).
2. Extract text.
3. Chunk with the requested strategy.
4. Batch-embed chunks.
5. Upsert vectors to Qdrant with payload (`document_id`, filename, index, text).
6. Persist document and chunk metadata in PostgreSQL.

**Conversation path**

1. Load Redis history for `session_id`.
2. LLM classifies / extracts booking intent and slots.
3. If booking is in progress or complete, skip retrieval and collect or persist the booking.
4. Otherwise rewrite the follow-up into a standalone query, embed, retrieve top-k from Qdrant, and generate an answer with retrieved context plus history.
5. Append the turn to Redis.

Vector search and generation are wired explicitly. There is no LangChain QA chain.

---

## Chunking strategies

Selectable at ingest time (`chunking_strategy` form field).

| Strategy | Behavior |
| --- | --- |
| `fixed_size` | Character windows with overlap; prefers whitespace near the boundary so tokens are not split mid-word. |
| `sentence_window` | Sentence split, then a sliding window of *N* sentences with overlap. Better for discourse that should stay together. |

Window sizes live in environment config (`CHUNK_SIZE`, `CHUNK_OVERLAP`, `SENTENCE_WINDOW_SIZE`, `SENTENCE_WINDOW_OVERLAP`).

---

## Interview booking

The chat API is also the booking surface. The LLM returns structured fields; the service merges them into Redis draft state until all of **name**, **email**, **date (`YYYY-MM-DD`)**, and **time (`HH:MM`)** are valid.

On completion:

- Name and email are encrypted with Fernet (`BOOKING_ENCRYPTION_KEY`) before insert.
- Date/time are stored as normalized strings.
- The client receives `booking.state = confirmed` and a `booking_id`.

Invalid emails/dates/times are dropped so the model cannot persist garbage slots.

---

## Project layout

```
app/
  api/v1/          HTTP routes (ingest, chat, health)
  core/            Settings, logging, encryption, errors
  db/              SQLAlchemy models and async session
  schemas/         Request/response contracts
  services/        Extraction, chunking, embeddings, vector store,
                   RAG pipeline, Redis memory, booking
tests/             Unit tests (chunking, extraction, encryption)
samples/           Example document for ingest
docker-compose.yml PostgreSQL, Redis, Qdrant, optional API
```

Routers stay thin. Business logic sits in services. Persistence and vector I/O are isolated behind small clients so they can be swapped (e.g. another OpenAI-compatible base URL).

---

## API

Interactive spec: `http://127.0.0.1:8000/docs`

### `POST /api/v1/documents/ingest`

`multipart/form-data`

| Field | Type | Notes |
| --- | --- | --- |
| `file` | file | `.pdf` or `.txt` |
| `chunking_strategy` | string | `fixed_size` (default) or `sentence_window` |

Response:

```json
{
  "document_id": "uuid",
  "filename": "interview_notes.txt",
  "chunking_strategy": "fixed_size",
  "chunk_count": 3,
  "created_at": "2026-09-16T00:00:00Z"
}
```

### `GET /api/v1/documents`

Lists ingested document metadata (not full text).

### `POST /api/v1/chat`

```json
{
  "session_id": null,
  "message": "What should candidates prepare?"
}
```

Omit `session_id` to start a conversation; reuse the returned id for follow-ups.

```json
{
  "session_id": "uuid",
  "reply": "...",
  "sources": [
    {
      "document_id": "...",
      "filename": "interview_notes.txt",
      "chunk_index": 0,
      "score": 0.81,
      "preview": "..."
    }
  ],
  "booking": {
    "state": "idle",
    "missing_fields": [],
    "booking_id": null
  }
}
```

Booking example (same session):

```json
{
  "session_id": "uuid",
  "message": "Book an interview for Ada Lovelace, ada@example.com, 2026-09-20 at 14:30"
}
```

### `GET /api/v1/health`

Liveness probe.

---

## Local setup

**Prerequisites:** Python 3.12, Docker, an OpenAI API key (or any OpenAI-compatible endpoint).

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt

cp .env.example .env               # Windows: copy .env.example .env
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Set in `.env`:

- `OPENAI_API_KEY`
- `BOOKING_ENCRYPTION_KEY` (value from the command above)

Start infrastructure and the API:

```bash
docker compose up -d postgres redis qdrant
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Alternatively, run the full stack (API in Docker):

```bash
docker compose up --build
```

Schema is created on startup (`create_all`). Qdrant collection is ensured on boot.

### Smoke test

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/documents/ingest" \
  -F "file=@./samples/interview_notes.txt" \
  -F "chunking_strategy=fixed_size"

curl -X POST "http://127.0.0.1:8000/api/v1/chat" \
  -H "Content-Type: application/json" \
  -d '{"session_id": null, "message": "What should candidates prepare?"}'
```

### Tests

```bash
pytest -q
```

---

## Configuration

| Variable | Role |
| --- | --- |
| `OPENAI_API_KEY` / `OPENAI_BASE_URL` | Embeddings and chat |
| `LLM_MODEL` / `EMBEDDING_MODEL` | Model IDs |
| `QDRANT_URL` / `QDRANT_COLLECTION` | Vector index |
| `DATABASE_URL` | Async PostgreSQL (`postgresql+asyncpg://…`) |
| `REDIS_URL` / `CHAT_MEMORY_TTL_SECONDS` | Conversation memory |
| `BOOKING_ENCRYPTION_KEY` | Fernet key for booking PII |
| `MAX_UPLOAD_BYTES` | Ingest size limit |

---

## Design notes

- **Qdrant over FAISS/Chroma** to satisfy the constraint and keep retrieval as a network service with payload filters, not an in-process index.
- **PostgreSQL for metadata** so documents, chunk pointers, and bookings are queryable independently of the vector store.
- **Custom RAG** keeps retrieval, prompting, and memory as explicit steps—easier to test and reason about than a chain abstraction.
- **Redis** holds hot conversational state (messages + incomplete booking slots) with TTL; durable bookings go to SQL.
- **PII encryption** for name/email; date/time stay as normalized strings for scheduling queries.

---

## License

Assignment submission. Not licensed for production use without the author’s consent.
