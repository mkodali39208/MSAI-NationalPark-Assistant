# 🏞️ National Parks Intelligent Chatbot

A cutting-edge AI-powered chatbot that helps users explore and learn about U.S. National Parks through natural, multi-turn conversations. Built entirely on free-tier cloud services using Retrieval Augmented Generation (RAG).
---

## ✨ Key Features

- 🏞️ **Comprehensive Coverage**: Information on 20+ major U.S. National Parks
- 💬 **Natural Language Q&A**: Ask questions in plain English
- 🧠 **Multi-turn Conversation Memory**: Ask follow-up questions naturally without repeating context
- 📚 **Authoritative Sources**: Data sourced from official NPS websites and documents
- 🔗 **Source Citations**: Every answer includes links to authoritative sources
- ⚡ **Fast Responses**: Powered by Groq API (Llama 3.3 70B)
- 🆓 **100% Free**: Entire stack runs on free-tier services ($0/month)
- 📱 **Responsive UI**: Works seamlessly on desktop and mobile devices

---

## 🏗️ Architecture

### High-Level Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Browser                             │
│                   (React + Vite Frontend)                        │
└────────────────────────────┬────────────────────────────────────┘
                             │
                    POST /api/chat
                             │
┌────────────────────────────▼────────────────────────────────────┐
│              FastAPI Backend (Render, Free Tier)                │
│              main.py + pipeline.py (~150MB RAM)                 │
└────────────────────────────┬────────────────────────────────────┘
                             │
          ┌──────────────────┼──────────────────┐
          ▼                  ▼                  ▼
     ┌─────────┐        ┌──────────┐      ┌───────────┐
     │  Cohere │        │ Qdrant   │      │   Groq    │
     │   API   │        │  Cloud   │      │   API     │
     │Embeddings       │ Vector DB│     │ LLM      │
     │(Free Tier)       │(Free Tier)     │(Free Tier)
     └─────────┘        └──────────┘      └───────────┘
```

### RAG Pipeline Flow (with Conversational Context)

```
1. User Query
   ↓
2. Query Preprocessing
   • Extract park context (which park are we discussing?)
   • Check conversation history
   ↓
3. Query Rewriting (if conversation history exists)
   • LLM resolves pronouns and references
   • Example: "What wildlife is there?" → "What wildlife is at Zion National Park?"
   ↓
4. Retrieval
   • Cohere embeds the rewritten query (1024-dim vectors)
   • Qdrant performs cosine similarity search
   • Returns top-k relevant document chunks
   ↓
5. Generation
   • Groq LLM generates contextual answer
   • Uses retrieved chunks as context
   • Includes conversation history for continuity
   ↓
6. Response Formatting
   • Answer text
   • Source citations
   • Metadata
   ↓
   User Response + Sources
```

### Key Design Decisions

**Simplified Architecture**:
- Native LangChain integrations (`CohereEmbeddings`, `QdrantVectorStore`, `ChatGroq`)
- Reduced codebase: 2 main files (`main.py` + `pipeline.py`)
- Removed wrapper classes for direct API integration
- Lazy loading of RAG pipeline for Render health checks (<2 second startup)

**Intelligent Context Management**:
- Smart park context detection (analyzes USER messages only, ignores assistant responses)
- Conversational query rewriting resolves pronouns before vector search
- Maintains multi-turn conversation memory
- Prevents context pollution from previous responses

**Performance Optimization**:
- API-based embeddings (Cohere) instead of local models → saves 300MB RAM
- Total memory footprint: ~150MB (fits in Render's 512MB free tier)
- Lazy loading ensures fast startup for port binding
- Streaming responses available for real-time feedback

---

## 💻 Tech Stack

### Frontend
- **Framework**: React 19.2.7
- **Build Tool**: Vite 8.1.1
- **Styling**: Vanilla CSS
- **Linting**: Oxlint 1.71.0
- **Runtime**: Node.js 18+

### Backend
- **Language**: Python 3.11+
- **Web Framework**: FastAPI 0.109.0+
- **Server**: Uvicorn 0.27.0+
- **Config Management**: python-dotenv 1.0.0

### AI/ML Pipeline
- **Orchestration**: LangGraph 0.2.0+ (StateGraph for RAG)
- **LLM Framework**: LangChain 0.3.0+
  - `langchain-cohere`: Cohere embeddings integration
  - `langchain-groq`: Groq LLM integration
  - `langchain-qdrant`: Qdrant vector database integration
- **Vector Database**: Qdrant Cloud 1.7.0+ (1GB free tier)

### AI Services (Free Tier)
- **LLM**: [Groq API](https://groq.com) - Llama 3.3 70B (30 requests/min free)
- **Embeddings**: [Cohere API](https://cohere.ai) - embed-english-v3.0, 1024-dim (100 calls/min free)
- **Vector DB**: [Qdrant Cloud](https://qdrant.tech) - 1GB free tier

### Deployment
- **Frontend**: Vercel / Netlify / GitHub Pages (optional)
- **Backend**: [Render](https://render.com) - Free tier (512MB RAM, 100 hours/month)
- **Database**: Qdrant Cloud (free tier)

---

## 📁 Project Structure

```
national-parks-chatbot/
│
├── frontend/                          # React + Vite frontend application
│   ├── public/
│   │   ├── favicon.svg                # Browser favicon
│   │   └── icons.svg                  # Icon assets
│   │
│   ├── src/
│   │   ├── App.jsx                    # Main React component (chat interface)
│   │   ├── App.css                    # Styling for chat UI
│   │   ├── index.css                  # Global styles
│   │   ├── main.jsx                   # React entry point
│   │   └── assets/                    # Additional assets
│   │
│   ├── index.html                     # HTML template
│   ├── package.json                   # Frontend dependencies
│   ├── vite.config.js                 # Vite build configuration
│   ├── .oxlintrc.json                 # Oxlint linting rules
│   ├── .gitignore                     # Git ignore for frontend
│   └── README.md                      # Frontend-specific documentation
│
├── backend/                           # FastAPI backend application
│   ├── main.py                        # FastAPI app + HTTP endpoints
│   │                                  #  - POST /api/chat (standard response)
│   │                                  #  - POST /api/chat/stream (SSE streaming)
│   │                                  #  - POST /api/search (vector search only)
│   │                                  #  - GET /api/parks (list parks)
│   │                                  #  - GET /health (health check)
│   │
│   ├── pipeline.py                    # LangGraph RAG pipeline
│   │                                  #  - extract_park() node
│   │                                  #  - rewrite_query() node
│   │                                  #  - retrieve() node
│   │                                  #  - generate() node
│   │                                  #  - no_results() fallback
│   │
│   ├── requirements.txt               # Python dependencies
│   ├── runtime.txt                    # Python version for Render
│   ├── ARCHITECTURE.md                # Detailed backend architecture
│   ├── .env                           # Environment variables (not in git)
│   ├── .python-version                # Python version specification
│   ├── .pip.conf                      # Pip configuration
│   └── __pycache__/                   # Python cache (ignored)
│
├── data_ingestion/                    # Data processing pipeline
│   ├── scrape_nps.py                  # Scrape NPS.gov for park info
│   ├── scrape_wikipedia.py            # Scrape Wikipedia for park data
│   ├── download_pdfs.py               # Download park brochures & documents
│   ├── process_pdfs.py                # Extract text from PDF files
│   ├── chunk_documents.py             # Split documents into chunks
│   ├── create_embeddings.py           # Generate embeddings & upload to Qdrant
│   ├── create_index.py                # Create Qdrant indices
│   ├── check_qdrant.py                # Verify Qdrant connection
│   ├── run_all_data_collection.py     # Orchestrate entire pipeline
│   ├── requirements.txt               # Data processing dependencies
│   └── .env                           # Environment variables
│
├── data/                              # Data storage
│   ├── raw/                           # Raw scraped & downloaded data
│   │   ├── pdfs/                      # Downloaded PDF files
│   │   ├── pdf_texts/                 # Extracted PDF text
│   │   ├── all_parks.json             # Complete park information
│   │   └── [park_code].json           # Individual park data (e.g., yell.json for Yellowstone)
│   │
│   ├── processed/                     # Processed & chunked data
│   │   ├── all_chunks.json            # Combined chunks from all parks
│   │   ├── [park_code]_chunks.json    # Park-specific chunks (e.g., yell_chunks.json)
│   │   └── chunking_stats.json        # Chunking statistics
│   │
│   └── metadata/                      # Park metadata
│       └── .gitkeep
│
├── render.yaml                        # Render deployment configuration
├── .gitignore                         # Git ignore rules (root level)
├── .env                               # Root environment variables (not in git)
└── README.md                          # Main documentation (original)
```

### Data Files by Park Code

The `data/raw/` and `data/processed/` directories contain files for each of 20+ national parks:

| Park Code | Park Name | Park Code | Park Name |
|-----------|-----------|-----------|-----------|
| yell | Yellowstone | grca | Grand Canyon |
| yose | Yosemite | zion | Zion |
| grsm | Great Smoky Mountains | glac | Glacier |
| olym | Olympic | romo | Rocky Mountain |
| cave | Carlsbad Caverns | kefj | Kenai Fjords |
| deva | Death Valley | evea | Everglades |
| grte | Grand Teton | badl | Badlands |
| brca | Bryce Canyon | cany | Canyonlands |
| crla | Crater Lake | arth | Arches |
| shen | Shenandoah | gumo | Guadalupe Mountains |
| meve | Mesa Verde | petr | Petrified Forest |
| redw | Redwood | thro | Theodore Roosevelt |
| jotr | Joshua Tree | seki | Sequoia & Kings Canyon |
| bisc | Biscayne | wica | Wind Cave |
| acad | Acadia | hale | Haleakala |

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.11+** (for backend)
- **Node.js 18+** (for frontend)
- **API Keys** (free tier):
  - [Groq API Key](https://groq.com) - for LLM
  - [Cohere API Key](https://cohere.ai) - for embeddings
  - [Qdrant Cloud URL + API Key](https://qdrant.tech) - for vector database

### Quick Start (Local Development)

#### 1. Clone the Repository

```bash
git clone https://github.com/mkodali39208/MSAI-NationalPark-Assistant.git
cd MSAI-NationalPark-Assistant
git checkout feature/v2  # Switch to latest branch
```

#### 2. Backend Setup

```bash
# Create and activate Python virtual environment
python -m venv .venv
.venv\Scripts\activate  # On Windows
# source .venv/bin/activate  # On macOS/Linux

# Navigate to backend
cd backend

# Install dependencies
pip install -r requirements.txt

# Create .env file with API credentials
cat > .env << EOF
GROQ_API_KEY=your_groq_api_key
COHERE_API_KEY=your_cohere_api_key
QDRANT_URL=your_qdrant_url
QDRANT_API_KEY=your_qdrant_api_key
EOF

# Start backend server
uvicorn main:app --reload --port 8000
```

Backend will be available at `http://localhost:8000`

#### 3. Frontend Setup

```bash
# Open new terminal, navigate to frontend
cd frontend

# Install dependencies
npm install

# Create .env file (if needed)
cat > .env << EOF
VITE_API_URL=http://localhost:8000
EOF

# Start development server
npm run dev
```

Frontend will be available at `http://localhost:5173`

#### 4. Test the Chatbot

- Open http://localhost:5173 in your browser
- Try asking: "Tell me about Yellowstone National Park"
- Ask follow-up questions: "What wildlife can I see there?"
- The chatbot will maintain conversation context!

---

### Building for Production

#### Frontend Build

```bash
cd frontend
npm run build      # Creates optimized dist/ folder
npm run preview    # Preview production build locally
```

#### Backend Deployment on Render

1. Push to GitHub (Render auto-deploys from GitHub)
2. Go to [Render Dashboard](https://dashboard.render.com)
3. Create new Web Service:
   - Connect GitHub repository
   - Set root directory: `backend`
   - Build command: `pip install --upgrade pip setuptools wheel && pip install --no-cache-dir -r requirements.txt`
   - Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - Set environment variables (GROQ_API_KEY, COHERE_API_KEY, QDRANT_URL, QDRANT_API_KEY)

4. Monitor deployment at https://dashboard.render.com

---

## 📊 Data Processing Pipeline

The `data_ingestion/` directory contains scripts for the entire data processing workflow:

### Pipeline Steps

```
1. scrape_nps.py
   └─→ Scrapes NPS.gov for park information
       └─→ Output: data/raw/[park_code].json

2. scrape_wikipedia.py
   └─→ Scrapes Wikipedia for additional park details
       └─→ Merged with NPS data

3. download_pdfs.py
   └─→ Downloads official park brochures and documents
       └─→ Output: data/raw/pdfs/

4. process_pdfs.py
   └─→ Extracts text from PDF files
       └─→ Output: data/raw/pdf_texts/

5. chunk_documents.py
   └─→ Splits documents into manageable chunks (512 tokens with overlap)
       └─→ Output: data/processed/[park_code]_chunks.json

6. create_embeddings.py
   └─→ Generates embeddings using Cohere API
   └─→ Uploads to Qdrant Cloud
       └─→ Creates indices for vector search

7. check_qdrant.py
   └─→ Verifies Qdrant connection and index status
```

### Running Data Ingestion

```bash
cd data_ingestion

# Install data processing dependencies
pip install -r requirements.txt

# Set up environment variables
cat > .env << EOF
GROQ_API_KEY=your_key
COHERE_API_KEY=your_key
QDRANT_URL=your_url
QDRANT_API_KEY=your_key
EOF

# Run full pipeline
python run_all_data_collection.py

# Or run individual steps
python scrape_nps.py
python download_pdfs.py
python process_pdfs.py
python chunk_documents.py
python create_embeddings.py
```

---

## 🔌 API Endpoints

### Base URL
- Local: `http://localhost:8000`
- Production: `https://national-parks-chatbot.onrender.com`

### Endpoints

#### 1. Health Check
```bash
GET /health
```
Returns system status and LLM configuration.

#### 2. Chat (Standard Response)
```bash
POST /api/chat
Content-Type: application/json

{
  "question": "Tell me about Yellowstone",
  "park_code": "yell",  # Optional
  "conversation_history": [  # Optional
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ]
}
```

Response:
```json
{
  "answer": "Yellowstone National Park is...",
  "sources": ["source1", "source2"],
  "park_code": "yell",
  "status": "success"
}
```

#### 3. Chat (Streaming Response)
```bash
POST /api/chat/stream
Content-Type: application/json

Same request format as /api/chat
```

Returns Server-Sent Events (SSE) with streaming answer.

#### 4. Vector Search (Direct)
```bash
POST /api/search
Content-Type: application/json

{
  "query": "wildlife in national parks",
  "park_code": "yell",  # Optional
  "top_k": 5  # Number of results
}
```

Returns relevant document chunks without LLM generation.

#### 5. Parks List
```bash
GET /api/parks
```

Returns list of available national parks.

---

## 🧠 How the RAG Pipeline Works

### State Graph (LangGraph)

The pipeline is orchestrated using LangGraph's StateGraph:

```python
from langgraph.graph import StateGraph

class ChatState(TypedDict):
    question: str
    park_code: Optional[str]
    conversation_history: List[Dict]
    retrieved_chunks: List[str]
    answer: str

graph = StateGraph(ChatState)
graph.add_node("extract_park", extract_park_node)
graph.add_node("rewrite_query", rewrite_query_node)
graph.add_node("retrieve", retrieve_node)
graph.add_node("generate", generate_node)
graph.add_node("no_results", no_results_node)

# Connect nodes with conditional edges
graph.add_edge("extract_park", "rewrite_query")
```

### Key Nodes

1. **extract_park**: Identifies which national park is being discussed
2. **rewrite_query**: Resolves pronouns and references using LLM
3. **retrieve**: Searches Qdrant for relevant chunks
4. **generate**: Uses Groq LLM to generate contextual answer
5. **no_results**: Fallback if no relevant chunks found

---

## 📈 Performance Metrics

### Memory Footprint
- **Frontend**: ~2-3MB (React app)
- **Backend**: ~150MB (including models and libraries)
- **Total**: ~150MB on Render free tier (512MB available)

### Latency
- **Embedding generation**: ~200-300ms (Cohere API)
- **Vector search**: ~50-100ms (Qdrant)
- **LLM generation**: ~1-2s (Groq API)
- **Total response time**: ~2-3 seconds

### Throughput
- **Cohere**: 100 calls/min (free tier)
- **Qdrant**: 1GB storage (free tier)
- **Groq**: 30 requests/min (free tier)

---

## 🛠️ Troubleshooting

### Common Issues

**1. Backend won't start**
```bash
# Check Python version
python --version  # Should be 3.11+

# Check if port 8000 is in use
lsof -i :8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows

# Reinstall dependencies
rm -rf .venv
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

**2. API key errors**
```bash
# Verify .env file exists and has correct keys
cat .env  # Display contents
# Make sure no quotes around values in .env
```

**3. Qdrant connection issues**
```bash
python data_ingestion/check_qdrant.py
# Should display collection info if connected
```

**4. Frontend can't connect to backend**
```bash
# Check backend is running
curl http://localhost:8000/health

# Update API_URL in frontend/src/App.jsx if needed
```

---

## 📝 Recent Updates

### February 2026 - Backend Simplification
- Reduced backend from 7 files to 2 (`main.py` + `pipeline.py`)
- Replaced custom wrapper classes with native LangChain integrations
- Removed `embed_query` node from LangGraph (handled internally)
- Fixed conversation context detection algorithm
- Improved memory footprint to ~150MB

### February 2026 - Conversation Context Improvement
- Now correctly prioritizes current question over history
- Filters to USER messages only (prevents context pollution)
- Processes messages in reverse order for accurate context

---

## 🤝 Contributing

Contributions are welcome! Here's how to contribute:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Areas for Contribution
- Add more national parks
- Improve UI/UX
- Add additional AI services (Claude, OpenAI, etc.)
- Implement caching layers
- Add authentication
- Improve error handling
- Write comprehensive tests

---

## 📜 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## 👏 Credits

- **NPS Data Source**: [National Park Service](https://www.nps.gov)
- **LLM**: [Groq API](https://groq.com) (Llama 3.3)
- **Embeddings**: [Cohere](https://cohere.ai)
- **Vector DB**: [Qdrant](https://qdrant.tech)
- **Framework**: [LangChain](https://langchain.com) & [LangGraph](https://langchain.com/langgraph)
- **Built with**: [React](https://react.dev), [Vite](https://vitejs.dev), [FastAPI](https://fastapi.tiangolo.com)

---

## 📧 Contact & Support

- **Author**: [MSAI Student]
- **GitHub**: https://github.com/mkodali39208/MSAI-NationalPark-Assistant
- **Issues**: https://github.com/mkodali39208/MSAI-NationalPark-Assistant/issues

---

## 🎯 Future Roadmap

- [ ] Add real-time collaboration features
- [ ] Integrate speech-to-text for voice queries
- [ ] Implement user authentication and chat history
- [ ] Add more detailed park comparisons
- [ ] Create mobile app (React Native)
- [ ] Implement advanced filters (by difficulty, season, etc.)
- [ ] Add trip planning features
- [ ] Multi-language support
- [ ] Integration with booking services

---

**Happy Exploring! 🏕️**
