# National Parks Chatbot

An intelligent chatbot that helps users explore and learn about U.S. National Parks through natural conversation. Built using RAG (Retrieval Augmented Generation), with a switchable LLM backend (cloud Groq or local Ollama).

## Features

- 🏞️ Information on 20+ major U.S. National Parks
- 💬 Natural language Q&A interface
- 🧠 **Multi-turn conversation memory** - Ask follow-up questions naturally
- 📚 Sourced from official NPS data and documents
- 🔗 Citations to authoritative sources
- ⚡ Fast responses powered by Groq API
- 🔀 **Switchable LLM backend** — Groq (cloud) or Ollama (local), toggled with one env var
- 🆓 Runs entirely on free-tier / local services

## Architecture

```
User → React Frontend (Vite) → FastAPI Backend
                                     │
                    ┌────────────────┼────────────────┐
                    ▼                ▼                ▼
              Cohere API        Qdrant Cloud      LLM_PROVIDER
           (Embeddings)       (Vector Search)     switch
          embed-english-v3.0                      ┌────┴────┐
             1024-dim                              ▼         ▼
                                                  Groq     Ollama
                                              (cloud API) (local server)
```

### RAG Pipeline Flow (with Conversational Understanding):
1. **User Query** → FastAPI endpoint
2. **Query Rewriting** → If conversation history exists, LLM rewrites query to resolve pronouns/references
   - Example: "what wildlife is there?" → "what wildlife is at Zion National Park?"
3. **Retrieval** → Cohere embeds the query and Qdrant finds top-k similar documents (cosine similarity) in a single step
4. **Generation** → The configured LLM (Groq or local Ollama) generates an answer with retrieved context + conversation history
5. **Response** → Answer + sources returned to frontend

### Key Design Decisions:
- **Native LangChain integrations** → `CohereEmbeddings`, `QdrantVectorStore`, `ChatGroq`, and `ChatOllama` replace custom wrapper classes, keeping the backend to 2 files (`main.py` + `pipeline.py`)
- **Provider-agnostic LLM factory** → `_get_llm()` in `pipeline.py` builds either `ChatGroq` or `ChatOllama` based on the `LLM_PROVIDER` env var; the rest of the graph doesn't know which one is active
- **Smart park context detection** → Automatically filters search to the park being discussed by analyzing USER messages only (ignores assistant responses to prevent context pollution)
- **Conversational query rewriting** → Resolves pronouns before vector search for accurate context retrieval
- **API-based embeddings** (Cohere) instead of local models → saves 300MB RAM
- **Lazy loading** of RAG pipeline → <2 second startup for Render port binding
- **Memory footprint** → ~150MB with Groq (fits in Render's 512MB free tier); higher if running Ollama's local model alongside the backend

### Recent Updates:
- **July 2026**: Added local LLM support via Ollama
  - `LLM_PROVIDER` env var (`groq` or `ollama`) switches the backend's LLM with no code changes
  - New `GROQ_MODEL`, `OLLAMA_BASE_URL`, `OLLAMA_MODEL` env vars for per-provider configuration
- **February 2026**: Simplified backend from 7 files to 2 files
  - Replaced custom `embeddings.py`, `vector_db.py`, and `llm.py` wrapper classes with native `langchain-cohere`, `langchain-qdrant`, and `langchain-groq` integrations
  - Merged `rag.py` into `pipeline.py` — all pipeline logic in one place
  - Removed `embed_query` node from LangGraph graph; embedding is now handled internally by `QdrantVectorStore`
  - Deleted stale backup files (`main_bk.py`, `rag_bk.py`)
- **February 2026**: Fixed conversation context detection algorithm
  - Now correctly prioritizes current question over history
  - Filters to USER messages only (assistant responses no longer pollute context)
  - Processes messages in reverse order (newest first) for accurate context

## Tech Stack

- **Frontend**: React + TypeScript + Vite (`frontend/`)
- **Backend**: Python FastAPI (`backend/`), deployable to Render's 512MB RAM free tier
- **Pipeline**: LangGraph (orchestration) + LangChain (prompts, integrations)
- **Vector Database**: Qdrant Cloud (1GB free tier) via `langchain-qdrant`
- **LLM**: Groq API (Llama 3.3 70B, 30 req/min free) via `langchain-groq`, **or** a local Ollama model via `langchain-ollama` — set with `LLM_PROVIDER`
- **Embeddings**: Cohere API (embed-english-v3.0, 1024-dim, 100 calls/min free) via `langchain-cohere`
- **Data Sources**: NPS.gov, NPS API, park brochures, Wikipedia

## Project Structure

```
national-parks-chatbot/
├── backend/
│   ├── main.py              # FastAPI application + endpoints
│   ├── pipeline.py          # LangGraph RAG pipeline (embeddings, retrieval, generation)
│   ├── ARCHITECTURE.md      # How a request flows through main.py + pipeline.py
│   ├── requirements.txt     # Backend dependencies
│   └── runtime.txt          # Python version for Render
├── frontend/
│   ├── src/                 # React + TypeScript chat UI (Vite)
│   ├── .env.example         # VITE_API_URL template
│   └── package.json
├── data_ingestion/
│   ├── ARCHITECTURE.md      # Full scrape → chunk → embed pipeline, script by script
│   ├── scrape_nps.py        # NPS website + API scraper
│   ├── scrape_wikipedia.py  # Wikipedia scraper (supplementary)
│   ├── process_pdfs.py      # PDF text extraction
│   ├── chunk_documents.py   # Document chunking
│   ├── create_embeddings.py # Generate & upload embeddings to Qdrant
│   ├── create_index.py      # Create the park_code payload index in Qdrant
│   ├── check_qdrant.py      # Diagnostic: verify Qdrant setup/collection health
│   └── requirements.txt     # Data processing dependencies
├── data/
│   ├── raw/                 # Scraped and downloaded data
│   ├── processed/           # Cleaned and chunked data (all_chunks.json)
│   └── metadata/            # Park metadata
├── tools/
│   └── patch_existing_files.py  # One-time patch script for the coverage upgrade (see README-COVERAGE-UPGRADE.md)
├── render.yaml              # Render deployment config
├── .env                     # Shared secrets for backend + data_ingestion (not committed)
├── .gitignore
└── README.md                # This file
```

---

## Quickstart: Run on a New Machine (after `git clone` / `git pull`)

This is the fast path for joining an **existing** project where the Qdrant vector database is already populated — you're just standing up the backend and frontend locally. If you need to set up brand-new API keys or rebuild the vector database from scratch, see [Full Setup From Scratch](#full-setup-from-scratch-new-api-keys--rebuilding-the-vector-db) below instead.

### Prerequisites

- Python 3.11+ (tested working on 3.13 as well)
- Node.js 18+ and npm
- Git
- (Optional) [Ollama](https://ollama.com) — only needed if you want to run the LLM locally instead of via Groq

### 1. Clone / pull the repo

```bash
git clone https://github.com/mksamelson/national-parks-chatbot.git
cd national-parks-chatbot
```

### 2. Get the `.env` file

The backend and data-ingestion scripts read one shared `.env` file at the **project root** (not inside `backend/`). It is not committed to git, so get it from a teammate/secure channel, or create it yourself:

```bash
# Project root
COHERE_API_KEY=your_cohere_api_key

LLM_PROVIDER=groq                     # "groq" (cloud) or "ollama" (local)
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=llama-3.3-70b-versatile

OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1

QDRANT_URL=https://your-cluster.qdrant.io
QDRANT_API_KEY=your_qdrant_api_key

NPS_API_KEY=your_nps_api_key          # only needed for data_ingestion scripts
```

`python-dotenv` walks up from `backend/main.py`'s location to find this file, so it's picked up correctly whether you run `uvicorn` from the repo root or from inside `backend/`.

### 3. Run the backend

```bash
# From the project root
python -m venv .venv

# Activate the venv:
#   Windows PowerShell:  .\.venv\Scripts\Activate.ps1
#   Windows Git Bash:    source .venv/Scripts/activate
#   macOS / Linux:       source .venv/bin/activate

pip install -r backend/requirements.txt

cd backend
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Verify it's up:

```bash
curl http://127.0.0.1:8000/health
# {"status":"healthy","message":"All systems operational","version":"1.0.0"}
```

> **Port 8000 already in use?** Something else on your machine may be bound to it. Run on another port instead (`--port 8010`) and point the frontend at it in step 4.

### 4. Run the frontend

```bash
cd frontend
npm install
cp .env.example .env
# Edit .env if your backend isn't on the default port:
#   VITE_API_URL=http://127.0.0.1:8000
npm run dev
```

Vite prints a local URL (default `http://localhost:5173`). Open it in a browser.

> **Vite dev server unreachable at `127.0.0.1`?** Vite's dev server can bind to the IPv6 loopback (`[::1]`) rather than IPv4. Use `http://localhost:5173` in the browser/curl, not `http://127.0.0.1:5173`.

### 5. (Optional) Switch the LLM to local Ollama

If Groq is unavailable (rate-limited, network-blocked, or you just want a fully local/offline setup):

```bash
ollama pull llama3.1:8b     # one-time download, ~4.7GB
ollama serve                 # usually already running as a background service
```

Then in the root `.env`, set:

```bash
LLM_PROVIDER=ollama
OLLAMA_MODEL=llama3.1:8b
```

Restart the backend (`uvicorn`) to pick up the change — no code changes needed.

### 6. Rebuilding the vector database (only if needed)

The Qdrant collection is cloud-hosted and shared — you normally don't need to touch it just to run the app. If you do need to rebuild it (new data, corrupted collection, dimension mismatch), see [`data_ingestion/ARCHITECTURE.md`](data_ingestion/ARCHITECTURE.md) for the full scrape → chunk → embed pipeline, or run the quick diagnostic:

```bash
cd data_ingestion
pip install -r requirements.txt
python check_qdrant.py
```

---

## Full Setup From Scratch (new API keys / rebuilding the vector DB)

Use this path if you're standing up an entirely new deployment rather than joining an existing one.

### 1. Set Up Free Accounts

1. **Cohere API**: https://dashboard.cohere.com
   - Get your API key (for embeddings)
   - Free tier: 100 API calls/minute

2. **Groq API**: https://console.groq.com
   - Get your API key (for LLM)
   - Free tier: 30 requests/minute
   - (Or skip this and use local Ollama instead — see Quickstart step 5)

3. **Qdrant Cloud**: https://cloud.qdrant.io
   - Create a free cluster
   - Get your cluster URL and API key
   - Free tier: 1GB storage

4. **Render**: https://render.com (optional, for backend deployment)
   - Free tier: 512MB RAM, 750 hours/month

5. **NPS Data API**: https://www.nps.gov/subjects/developer/get-started.htm (optional, for data collection)

### 2. Data Collection

```bash
cd data_ingestion
pip install -r requirements.txt

# Set NPS API key (optional but recommended)
export NPS_API_KEY=your_key_here

# Run data collection
python scrape_nps.py
python scrape_wikipedia.py
python process_pdfs.py       # only if you also ran download_pdfs.py
python chunk_documents.py
```

Or run the whole thing interactively with `python run_all_data_collection.py`. See [`data_ingestion/ARCHITECTURE.md`](data_ingestion/ARCHITECTURE.md) for what each script does and in what order.

### 3. Create the Vector Database

```bash
# Requires COHERE_API_KEY, QDRANT_URL, QDRANT_API_KEY set (via .env or exported)
python create_embeddings.py   # ~10 minutes due to Cohere free-tier rate limiting
python create_index.py        # creates the park_code payload index for filtered search
```

### 4. Run the backend and frontend

Same as the Quickstart above (steps 3–4).

### 5. Deploy Backend to Render

1. Push code to GitHub
2. Connect GitHub repo to Render
3. Set environment variables in Render dashboard
4. Deploy — `render.yaml` configures everything automatically

### 6. Deploy the Frontend

Build with `npm run build` in `frontend/` and host the `dist/` output anywhere that serves static files (Render Static Site, Netlify, Vercel, etc.), pointing `VITE_API_URL` at your deployed backend.

## Environment Variables

One `.env` file at the **project root** is shared by `backend/` and `data_ingestion/`:

```bash
# Cohere API (for embeddings)
COHERE_API_KEY=your_cohere_api_key

# LLM provider switch: "groq" (cloud, default) or "ollama" (local, no API key)
LLM_PROVIDER=groq

# Groq API (used when LLM_PROVIDER=groq)
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=llama-3.3-70b-versatile

# Ollama (used when LLM_PROVIDER=ollama) — requires `ollama serve` running locally
# and the model pulled via `ollama pull <model>`
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1

# Qdrant Cloud (for vector database)
QDRANT_URL=https://your-cluster.qdrant.io
QDRANT_API_KEY=your_qdrant_api_key

# NPS API (optional, for data collection only)
NPS_API_KEY=your_nps_api_key
```

`frontend/` has its own separate `.env` (copy from `frontend/.env.example`):

```bash
VITE_API_URL=http://127.0.0.1:8000
```

## API Endpoints

### Chat Endpoint (with Conversation Memory)

`POST /api/chat` - Main chat endpoint with optional conversation history

**Basic request (single question):**
```json
{
  "question": "What wildlife can I see in Yellowstone?",
  "top_k": 5
}
```

**Multi-turn conversation (with history):**
```json
{
  "question": "What about grizzly bears?",
  "top_k": 5,
  "conversation_history": [
    {"role": "user", "content": "What wildlife can I see in Yellowstone?"},
    {"role": "assistant", "content": "Yellowstone is home to diverse wildlife including grizzly bears, wolves, bison, elk..."}
  ]
}
```

**Parameters:**
- `question` (required): User question about national parks
- `top_k` (optional): Number of context chunks to retrieve (1-10, default: 5)
- `park_code` (optional): Filter results to specific park (e.g., "yell" for Yellowstone)
- `conversation_history` (optional): Array of previous messages (max 20 messages)

**Conversation History Format:**
- Each message: `{"role": "user" | "assistant", "content": "string"}`
- Maximum 20 messages (10 exchanges) to stay within token limits
- Optional — leave empty or omit for single-turn questions
- Backend is stateless; client manages conversation state

**How Conversational Context Works:**

The system uses two techniques to maintain conversation context:

1. **Park Context Detection** — Automatically detects which park you're discussing and filters search results to only that park
2. **Query Rewriting** — Rewrites ambiguous questions to resolve pronouns and references

**Example conversation:**
1. User: "Tell me about Glacier National Park"
   - System detects: "Glacier" → filters all future searches to Glacier only
2. User: "What wildlife will I see there?"
   - **Park filter:** Glacier (auto-detected)
   - **Query rewritten:** "What wildlife can I see at Glacier National Park?"
   - **Search:** Only Glacier documents retrieved
3. User: "Are they dangerous?"
   - **Park filter:** Still Glacier
   - **Query rewritten:** "Are the animals at Glacier National Park dangerous?"

**Key benefit:** Once you mention a park, all follow-up questions automatically focus on that park until you mention a different park.

### Streaming Chat Endpoint

`POST /api/chat/stream` - Returns tokens as Server-Sent Events (SSE)

Request body is identical to `/api/chat`. The frontend receives tokens progressively as the LLM generates them.

SSE event format:
```
data: {"type": "token",  "content": "<text>"}
data: {"type": "done",   "sources": [...], "num_sources": N}
data: {"type": "error",  "message": "<msg>"}
data: [DONE]
```

### Search Endpoint

`POST /api/search` - Direct vector search (no LLM generation)
```json
{
  "query": "hiking trails",
  "top_k": 10,
  "park_code": "yose"
}
```

### Health Check

`GET /` or `GET /health` - Server health status

## Troubleshooting

### Local Run Issues

**Port already in use (`[WinError 10048]` / `Address already in use`):**
- Cause: Another process already has that port bound
- Solution: Run uvicorn/vite on a different port and update the corresponding `.env` (`VITE_API_URL` in `frontend/.env`)

**Frontend can't reach backend, but the backend is running:**
- Cause: Vite's dev server can bind to the IPv6 loopback (`[::1]`) instead of `127.0.0.1`
- Solution: Use `http://localhost:5173` rather than `http://127.0.0.1:5173`

**Groq returns `403 Access denied. Please check your network settings.`:**
- Cause: This is a network-level block on Groq's side (confirmed by the fact that even an invalid API key or an unauthenticated request gets the identical 403) — not a bad API key
- Solution: Try from a different network, or switch to a local model: set `LLM_PROVIDER=ollama` in `.env` (see Quickstart step 5) and restart the backend

### Render Deployment Issues

**Port scan timeout:**
- Cause: App takes too long to bind to port
- Solution: Already implemented — lazy loading ensures <2 second startup

**Memory exceeded on Render:**
- Cause: Using local embedding models
- Solution: Already implemented — using Cohere API instead (no local model loaded)

**Vector dimension mismatch:**
- Error: "expected dim: 1024, got 384"
- Solution: Ensure using `embed-english-v3.0` (1024-dim), not `embed-english-light-v3.0` (384-dim)
- Re-run `create_embeddings.py` if needed

**API key errors:**
- Error: "Illegal header value"
- Solution: API keys are auto-stripped of whitespace, but verify `.env` file has no extra newlines

**Cohere rate limit:**
- Error: "trial token rate limit exceeded"
- Solution: `create_embeddings.py` includes rate limiting (50 chunks/batch, 15 sec delays)

### Qdrant Issues

**Check database status:**
```bash
cd data_ingestion
python check_qdrant.py
```

**Verify embeddings:**
- Expected: ~2,000+ vectors in collection
- Dimension: 1024
- If dimension wrong, must recreate collection
- If the collection was created before the `metadata`-nested payload schema was added, `park_code` filtering will silently fail — re-run `create_embeddings.py` and recreate the collection, then `create_index.py`

## Development

### Code Formatting

```bash
black backend/ data_ingestion/
```

## Cost Breakdown

All cloud services are on free tiers; Ollama is fully local and free with no rate limits:

- **Cohere API**: 100 calls/min free, unlimited total calls
- **Groq API**: 30 req/min, 14,400 tokens/min free
- **Ollama** (alternative to Groq): $0, runs on your own hardware, no rate limits, no network dependency
- **Qdrant Cloud**: 1GB free (stores ~2,000 chunks @ 1024-dim)
- **Render**: 512MB RAM, 750 hours/month free (Groq-backed app uses ~150MB)
- **Total Monthly Cost**: $0

### Why Free Tier Works:
- Cohere API eliminates need for local embedding models (saves ~300MB RAM)
- Lazy loading enables <2 second startup (critical for Render port binding)
- Memory-optimized architecture fits in 512MB (vs 400-500MB for local models)
- Rate limits are sufficient for typical usage patterns

## Data Sources

- [National Park Service Official Website](https://www.nps.gov)
- [NPS Data API](https://www.nps.gov/subjects/developer/api-documentation.htm)
- [NPS Publications](https://www.nps.gov/subjects/publications/)
- Wikipedia (supplementary)

See [`data_ingestion/ARCHITECTURE.md`](data_ingestion/ARCHITECTURE.md) for exactly how each source flows from scrape → chunk → embed.

## License

MIT License

## Acknowledgments

- National Park Service for providing open data
- Groq for free LLM API access
- Ollama for local LLM inference
- Qdrant for free vector database hosting
- Anthropic Claude for assisting with development

---

Built with ❤️ for national park enthusiasts
