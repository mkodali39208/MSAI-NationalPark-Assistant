# National Parks Chatbot

An intelligent chatbot that helps users explore and learn about U.S. National Parks through natural conversation. Built using RAG (Retrieval Augmented Generation) with 100% free-tier services.

## Features

* 🏞️ Information on 20+ major U.S. National Parks
* 💬 Natural language Q\&A interface
* 🧠 **Multi-turn conversation memory** - Ask follow-up questions naturally
* 📚 Sourced from official NPS data and documents
* 🔗 Citations to authoritative sources
* ⚡ Fast responses powered by Groq API
* 🆓 Completely free to run (free tier services)

## Architecture

```
User → Lovable.ai Frontend → Render Backend API (FastAPI)
                                     ↓
                    ┌────────────────┼────────────────┐
                    ↓                ↓                ↓
              Cohere API        Qdrant Cloud    Groq API
           (Embeddings)       (Vector Search)  (Llama 3.3 70B)
          embed-english-v3.0
             1024-dim
```



