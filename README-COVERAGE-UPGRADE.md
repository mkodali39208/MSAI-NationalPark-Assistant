# National Parks Chatbot — Question Coverage Upgrade

This additive upgrade expands the repository's shallow homepage-only scraping for the evaluation questions about Yellowstone, Grand Canyon, Yosemite, and Zion.

## What it adds

- Targeted crawl of official NPS pages for fees, reservations, permits, visitor centers, roads, accessibility, campgrounds, bear safety, food storage, history, wilderness, weather, and dining.
- Optional structured NPS API enrichment from `feespasses`, `visitorcenters`, `campgrounds`, `alerts`, `roadevents`, `thingstodo`, `places`, `articles`, and `parks`.
- Section-aware, smaller chunks with park/page titles repeated in every chunk.
- Nested `metadata` in Qdrant payloads so LangChain can return `park_code`, title, source URL, and source type correctly.
- A coverage audit for all supplied evaluation questions.
- Guardrails for subjective restaurant questions and long-range weather prediction.

## Install into your repository

Copy the folders/files in this package into the matching locations in your existing `national-parks-chatbot` project. Existing files are not overwritten except when `tools/patch_existing_files.py` patches two files and creates backups.

Recommended project-root `.env`:

```env
NPS_API_KEY=your_nps_api_key
COHERE_API_KEY=...
GROQ_API_KEY=...
QDRANT_URL=...
QDRANT_API_KEY=...
```

The NPS key is optional for web crawling but strongly recommended for structured campground, visitor-center, fee, and road-event records.

## Run

From the project root, with the backend stopped:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass; .\.venv\Scripts\Activate.ps1
python tools\patch_existing_files.py
cd data_ingestion
python scrape_extended_nps.py
python build_extended_chunks.py
python create_embeddings.py
```

When `create_embeddings.py` asks whether to recreate the existing collection, enter `y`. This is required because every point must be re-uploaded with the new nested metadata.

Then run:

```powershell
python create_index.py
python audit_question_coverage.py
```

Reports are written to:

```text
data\processed\question_coverage_report.csv
data\processed\question_coverage_report.json
```

Restart the backend:

```powershell
cd ..\backend
python -m uvicorn main:app --reload
```

## Important limitations

- "Best restaurant" is subjective and changes over time. The bot should list official dining options and avoid asserting one objective winner.
- A static RAG collection cannot predict weather next month. The bot should provide official seasonal climate guidance and recommend checking a short-range forecast closer to travel. A live weather API is needed for current forecasts.
- Current road closures, visitor-center hours, fees, and reservation rules can change. Responses should cite and recommend verifying the official NPS page.
