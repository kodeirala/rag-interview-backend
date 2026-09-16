# RAG Interview Backend

FastAPI backend that:

- Ingests `.pdf` / `.txt` files, chunks them, embeds them, and stores vectors in Qdrant
- Answers questions with multi-turn RAG (chat memory in Redis)
- Books interviews (name, email, date, time) and encrypts PII in PostgreSQL

No FAISS, Chroma, UI, or LangChain RetrievalQAChain.

## Run it

You need **Python 3.12**, **Docker Desktop**, and an **OpenAI API key**.

```powershell
cd c:\Users\koira\Projects\rag-interview-backend

uv python install 3.12
uv venv --python 3.12 .venv
.\.venv\Scripts\Activate.ps1
uv pip install -r requirements.txt

copy .env.example .env
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Edit `.env`:

- `OPENAI_API_KEY` = your key
- `BOOKING_ENCRYPTION_KEY` = the key printed above

Then start databases and the API:

```powershell
docker compose up -d postgres redis qdrant
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open http://127.0.0.1:8000/docs

## APIs

| Method | Path | What it does |
| --- | --- | --- |
| GET | `/api/v1/health` | Health check |
| POST | `/api/v1/documents/ingest` | Upload a `.pdf` or `.txt` (`chunking_strategy`: `fixed_size` or `sentence_window`) |
| GET | `/api/v1/documents` | List ingested files |
| POST | `/api/v1/chat` | Chat / RAG / book an interview |

Example ingest:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/v1/documents/ingest" `
  -F "file=@.\samples\interview_notes.txt" `
  -F "chunking_strategy=fixed_size"
```

Example chat (reuse `session_id` for follow-ups):

```json
{ "session_id": null, "message": "What should candidates prepare?" }
```

Book an interview in the same chat:

```json
{ "session_id": "paste-id", "message": "Book Ada Lovelace, ada@example.com, 2026-09-20 at 14:30" }
```

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```
