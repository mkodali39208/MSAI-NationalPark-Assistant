# Data Pipeline: From Raw Scrape to Searchable Vectors

This document traces how park data gets from public websites/APIs into the
Qdrant collection that `backend/pipeline.py` searches at query time. It
covers two pipelines that exist in this repo:

- **Baseline pipeline** — broad, shallow coverage of 30 parks (website + Wikipedia)
- **Extended coverage upgrade** — deep, targeted coverage of 4 parks (Yellowstone,
  Grand Canyon, Yosemite, Zion) added later to answer specific evaluation questions
  (fees, permits, bear safety, accessibility, etc.) — see `README-COVERAGE-UPGRADE.md`

Both pipelines write into the same `data/processed/all_chunks.json`, which
`create_embeddings.py` uploads to the single Qdrant collection `national_parks`.

---

## 1. Baseline Pipeline (30 parks)

Orchestrated end-to-end by `run_all_data_collection.py`, or run step-by-step:

```
scrape_nps.py ─┐
download_pdfs.py ─┼─► process_pdfs.py ─┐
scrape_wikipedia.py ┘                   ├─► chunk_documents.py ─► create_embeddings.py ─► create_index.py
                                         ┘
```

| Order | Script | Reads | Writes | Purpose |
|---|---|---|---|---|
| 1 | `scrape_nps.py` | NPS.gov website + NPS Data API (`NPS_API_KEY`) | `data/raw/{park}.json`, `data/raw/all_parks.json` | For each of 30 parks: scrape the park's `index.htm` page text, and (if an API key is set) pull `api_data`, `alerts`, `campgrounds` from the NPS API |
| 2 | `download_pdfs.py` | NPS.gov brochure/map URLs (pattern-guessed + scraped `planyourvisit` pages) | `data/raw/pdfs/*.pdf`, `downloaded_pdfs.json` | Downloads official brochure PDFs per park (up to 1 brochure + 5 extra docs each) |
| 3 | `scrape_wikipedia.py` | Wikipedia article pages (hardcoded title per park) | `data/raw/wikipedia/{park}_wikipedia.json`, `all_wikipedia.json`, `wikipedia_stats.json` | Scrapes the intro + body paragraphs of each park's Wikipedia article as supplementary text |
| 4 | `process_pdfs.py` | `data/raw/pdfs/*.pdf` | `data/raw/pdf_texts/*.txt` + `*_metadata.json` | Extracts text from downloaded PDFs (pdfplumber first, PyPDF2 fallback) |
| 5 | `chunk_documents.py` | `data/raw/*.json`, `data/raw/wikipedia/*`, `data/raw/pdf_texts/*` | `data/processed/{park}_chunks.json`, `all_chunks.json`, `chunking_stats.json` | Splits each source's text into ~800-token overlapping chunks, tagging each with `park_code`, `park_name`, `source_url`, `source_type`, and a nested `metadata` object |
| 6 | `create_embeddings.py` | `data/processed/all_chunks.json` | Qdrant collection `national_parks` | Embeds every chunk with Cohere (`embed-english-v3.0`, 1024-dim, rate-limited 50/batch) and upserts as Qdrant points (flat fields + nested `metadata`) |
| 7 | `create_index.py` | (Qdrant collection) | (Qdrant collection) | Creates a keyword payload index on `park_code` so the backend's filtered searches don't fall back to a full scan |

`check_qdrant.py` is a standalone diagnostic — run any time to verify env vars, collection existence, vector count, and the `park_code` index.

---

## 2. Extended Coverage Upgrade (4 parks, deep coverage)

Documented in `README-COVERAGE-UPGRADE.md`. This is **additive**: it doesn't
touch the 30-park baseline data, it patches two files and layers extra chunks
on top for the 4 parks that needed deeper answers.

```
tools/patch_existing_files.py   (one-time code patch, not data)
        │
        ▼
scrape_extended_nps.py ─► build_extended_chunks.py ─► create_embeddings.py (recreate=y) ─► create_index.py ─► audit_question_coverage.py
```

| Order | Script | Reads | Writes | Purpose |
|---|---|---|---|---|
| 0 | `tools/patch_existing_files.py` | `data_ingestion/create_embeddings.py`, `backend/pipeline.py` | Same files, in place (with `.before_coverage_upgrade` backups) | One-time code patch: adds the nested `metadata` payload block to `create_embeddings.py` and `metadata_payload_key="metadata"` to the `QdrantVectorStore` config in `pipeline.py`, plus the extra guardrail rules in `SYSTEM_PROMPT`. Idempotent — safe to re-run. |
| 1 | `scrape_extended_nps.py` | Curated NPS page paths + NPS API (`feespasses`, `visitorcenters`, `campgrounds`, `alerts`, `roadevents`, `thingstodo`, `places`, `articles`, `parks`) for `yell`, `grca`, `yose`, `zion` only | `data/raw/extended_nps/{park}_extended.json` | Crawls up to 45 targeted pages per park (fees, permits, visitor centers, roads, accessibility, bear safety, food storage, history, weather, etc.) plus structured API records |
| 2 | `build_extended_chunks.py` | `data/raw/extended_nps/*.json`, existing `data/processed/all_chunks.json` | `data/processed/all_chunks.json` (merged), `all_chunks.before_extended.json` (backup), `extended_chunk_stats.json` | Splits extended records into ~2200-char section-aware chunks (park/page title repeated in each chunk) and **merges** them into the existing chunk file |
| 3 | `create_embeddings.py` | `data/processed/all_chunks.json` | Qdrant collection `national_parks` | Same script as baseline step 6 — must be re-run with **recreate = y** so every point (old + new) is re-uploaded with the nested `metadata` schema |
| 4 | `create_index.py` | (Qdrant collection) | (Qdrant collection) | Same as baseline step 7 — re-create the `park_code` index after the collection was recreated |
| 5 | `audit_question_coverage.py` | 26 hardcoded evaluation questions (fees, permits, bear safety, accessibility, etc.), Qdrant collection | `data/processed/question_coverage_report.csv` / `.json` | Embeds each evaluation question, searches Qdrant filtered to its `park_code`, and reports the top matches — a coverage check, not part of the serving path |

---

## 3. Current State (observed 2026-07-25)

A few things worth knowing before running any step above:

- **`data/processed/all_chunks.json` locally has 4,489 chunks** (746 baseline
  Wikipedia chunks + 3,743 extended chunks for yell/grca/yose/zion), all with
  the nested `metadata` object the current `pipeline.py` expects.
- **The baseline NPS website scrape currently contributes 0 chunks**
  (`chunking_stats.json` → `"nps": 0`). Checking `data/raw/yell.json`, both
  `website_data.content` and `api_data` are empty — `scrape_nps.py` was run
  without an `NPS_API_KEY` and/or the site scrape returned nothing, so all
  746 baseline chunks are Wikipedia-only. Re-running `scrape_nps.py` with a
  valid `NPS_API_KEY` set should populate this.
- **The live Qdrant `national_parks` collection does not match the local
  processed data.** Querying it directly shows only 1,477 points with a
  **flat** payload (no `metadata` key), and it contains chunks tagged with
  park codes like `Bank Statement Robinhood`, `Form I-9 Paper Version`,
  `G-TAX FINAL DRAFT TY-2025-signed`, `Compound Interest Tables`, and
  `01 Intro 2025` — none of which are national parks. This looks like a
  shared/reused Qdrant Cloud cluster whose collection was never
  recreated/re-uploaded from this repo's current pipeline output, and which
  has unrelated (possibly personal) documents mixed in from other ingestion
  runs against the same cluster.
  - This explains the `Park mismatch: expected yell, got {''}` warnings seen
    in `backend` logs — the deployed collection predates the nested-`metadata`
    patch, so `QdrantVectorStore` can't read `park_code` from it.
  - **To fix:** re-run `create_embeddings.py` from `data_ingestion/` and
    answer **y** to recreate the collection, then `create_index.py`. This
    will replace the live collection with a clean upload of the current
    4,489-chunk `all_chunks.json` and remove the contaminating documents.

---

## 4. Directory Map

```
data/
├── raw/
│   ├── {park}.json              ← scrape_nps.py (website + API data per park)
│   ├── all_parks.json           ← scrape_nps.py (combined)
│   ├── pdfs/                    ← download_pdfs.py (brochure PDFs)
│   ├── pdf_texts/               ← process_pdfs.py (extracted text)
│   ├── wikipedia/               ← scrape_wikipedia.py
│   └── extended_nps/            ← scrape_extended_nps.py (yell/grca/yose/zion only)
├── processed/
│   ├── {park}_chunks.json       ← chunk_documents.py (per park, baseline only)
│   ├── all_chunks.json          ← chunk_documents.py, then merged by build_extended_chunks.py
│   ├── all_chunks.before_extended.json  ← backup made by build_extended_chunks.py
│   ├── chunking_stats.json      ← chunk_documents.py
│   ├── extended_chunk_stats.json        ← build_extended_chunks.py
│   └── question_coverage_report.{csv,json}  ← audit_question_coverage.py
└── metadata/                    ← reserved, currently unused
```

`data/processed/all_chunks.json` is the single source of truth that
`create_embeddings.py` uploads — everything upstream of it is raw material;
everything downstream of it is Qdrant/serving.
