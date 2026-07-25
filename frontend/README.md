# National Parks Chatbot Frontend

A responsive React + TypeScript frontend for the FastAPI backend in `mksamelson/national-parks-chatbot`.

## Included features

- Streaming answers through `POST /api/chat/stream`
- Automatic fallback to the standard `POST /api/chat` endpoint
- Multi-turn conversation history, limited to the backend's latest 20 messages
- Source links and retrieval scores
- Backend health indicator
- Suggested park questions
- Stop-generation and clear-chat controls
- Local browser persistence with `localStorage`
- Responsive desktop and mobile design
- No API secrets in the browser

## 1. Folder placement

Place this `frontend` folder beside your existing `backend` folder:

```text
national-parks-chatbot/
├── backend/
├── data/
├── data_ingestion/
└── frontend/
```

## 2. Requirements

Install Node.js 18 or newer. Verify it in PowerShell:

```powershell
node --version
npm --version
```

## 3. Configure the backend URL

From the `frontend` folder, create `.env` from the included example:

```powershell
Copy-Item .env.example .env
```

For local development, keep:

```env
VITE_API_URL=http://127.0.0.1:8000
```

Do not add Groq, Cohere, Qdrant, or NPS keys to the frontend. Those keys must remain in the backend environment only.

## 4. Install and run

```powershell
cd C:\Users\manik\original-NationalPark\national-parks-chatbot\frontend
npm install
npm run dev
```

Vite will open:

```text
http://localhost:5173
```

## 5. Run the backend in a separate terminal

```powershell
cd C:\Users\manik\original-NationalPark\national-parks-chatbot
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass; .\.venv\Scripts\Activate.ps1
cd backend
python -m uvicorn main:app --reload
```

Backend URL:

```text
http://127.0.0.1:8000
```

## 6. Production build

```powershell
npm run build
npm run preview
```

The deployable static files will be created in `frontend/dist`.

## 7. Connecting to a deployed Render backend

Change `frontend/.env` before building:

```env
VITE_API_URL=https://your-render-service.onrender.com
```

Then run:

```powershell
npm run build
```

For production, update the backend CORS configuration so `allow_origins` contains only your deployed frontend URL instead of `*`.

## Troubleshooting

### Backend offline banner

Confirm Uvicorn is running and open this URL in the browser:

```text
http://127.0.0.1:8000/health
```

### Request fails from the browser

Confirm `frontend/.env` exists, then restart `npm run dev`. Vite reads environment variables only when the development server starts.

### First answer is slower

The backend lazily initializes the RAG pipeline on its first chat request. Later requests should start faster.

### Clear browser history

Use the trash icon in the chatbot header. The conversation is stored only in browser `localStorage`.
