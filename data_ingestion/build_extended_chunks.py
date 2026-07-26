"""Convert extended NPS records into focused chunks and merge with all_chunks.json.

Run from data_ingestion/ after scrape_extended_nps.py:
    python build_extended_chunks.py
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Any, Dict, Iterable, List

ROOT_DIR = Path(__file__).resolve().parents[1]
INPUT_DIR = ROOT_DIR / "data" / "raw" / "extended_nps"
PROCESSED_DIR = ROOT_DIR / "data" / "processed"
CHUNKS_FILE = PROCESSED_DIR / "all_chunks.json"
BACKUP_FILE = PROCESSED_DIR / "all_chunks.before_extended.json"
STATS_FILE = PROCESSED_DIR / "extended_chunk_stats.json"

CHUNK_CHARS = 2200
OVERLAP_CHARS = 350
MIN_CHUNK_CHARS = 100
SOURCE_MARKER = "extended_nps"


def normalize(text: str) -> str:
    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def stable_id(*parts: str) -> str:
    digest = hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()[:16]
    return f"ext_{digest}"


def split_sections(text: str) -> List[str]:
    """Split at NPS headings while retaining the heading with its section."""
    text = normalize(text)
    if not text:
        return []
    sections: List[str] = []
    current: List[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("## ") and current:
            sections.append("\n".join(current).strip())
            current = [line]
        else:
            current.append(line)
    if current:
        sections.append("\n".join(current).strip())
    return sections


def sliding_chunks(text: str) -> List[str]:
    text = normalize(text)
    if len(text) <= CHUNK_CHARS:
        return [text] if len(text) >= MIN_CHUNK_CHARS else []

    chunks: List[str] = []
    start = 0
    while start < len(text):
        end = min(start + CHUNK_CHARS, len(text))
        if end < len(text):
            candidates = [
                text.rfind("\n\n", start + 1200, end),
                text.rfind("\n", start + 1200, end),
                text.rfind(". ", start + 1200, end),
                text.rfind("? ", start + 1200, end),
            ]
            best = max(candidates)
            if best > start:
                end = best + 1
        chunk = text[start:end].strip()
        if len(chunk) >= MIN_CHUNK_CHARS:
            chunks.append(chunk)
        if end >= len(text):
            break
        start = max(end - OVERLAP_CHARS, start + 1)
    return chunks


def record_to_chunks(record: Dict[str, Any], park_name: str) -> List[Dict[str, Any]]:
    park_code = record["park_code"]
    title = normalize(str(record.get("title", "NPS information")))
    source_url = str(record.get("url", f"https://www.nps.gov/{park_code}/index.htm"))
    source_type = str(record.get("source_type", "nps_extended"))
    content = normalize(str(record.get("content", "")))
    if len(content) < MIN_CHUNK_CHARS:
        return []

    # Prefix every chunk with park/page identity so exact short questions retrieve well.
    prefix = f"Park: {park_name}\nPage or record: {title}\nSource type: {source_type}\n"
    raw_sections = split_sections(content)
    units: List[str] = []
    for section in raw_sections:
        units.extend(sliding_chunks(section))

    chunks: List[Dict[str, Any]] = []
    for index, unit in enumerate(units):
        text = normalize(prefix + unit)
        chunk_id = stable_id(park_code, source_url, str(index), text[:120])
        metadata = {
            "park_code": park_code,
            "park_name": park_name,
            "source_url": source_url,
            "source_type": SOURCE_MARKER,
            "original_source_type": source_type,
            "title": title,
            "chunk_id": chunk_id,
            "chunk_index": index,
        }
        chunks.append(
            {
                "id": chunk_id,
                "park_code": park_code,
                "park_name": park_name,
                "chunk_index": index,
                "text": text,
                "token_count": max(1, len(text) // 4),
                "source_url": source_url,
                "source_type": SOURCE_MARKER,
                "title": title,
                "metadata": metadata,
            }
        )
    return chunks


def load_extended_records() -> List[Dict[str, Any]]:
    if not INPUT_DIR.exists():
        raise FileNotFoundError(
            f"{INPUT_DIR} does not exist. Run scrape_extended_nps.py first."
        )
    records: List[Dict[str, Any]] = []
    for path in sorted(INPUT_DIR.glob("*_extended.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        park_code = data["park_code"]
        park_name = data["park_name"]
        for record in data.get("web_pages", []) + data.get("api_records", []):
            record = dict(record)
            record["park_code"] = park_code
            record["park_name"] = park_name
            records.append(record)
    return records


def main() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    records = load_extended_records()
    if not records:
        raise RuntimeError("No extended records were found.")

    existing: List[Dict[str, Any]] = []
    if CHUNKS_FILE.exists():
        existing = json.loads(CHUNKS_FILE.read_text(encoding="utf-8"))
        if not BACKUP_FILE.exists():
            shutil.copy2(CHUNKS_FILE, BACKUP_FILE)

    base_chunks = [
        chunk for chunk in existing
        if chunk.get("source_type") != SOURCE_MARKER
        and chunk.get("metadata", {}).get("source_type") != SOURCE_MARKER
    ]

    extended_chunks: List[Dict[str, Any]] = []
    by_park: Dict[str, int] = {}
    by_source: Dict[str, int] = {}
    for record in records:
        chunks = record_to_chunks(record, record["park_name"])
        extended_chunks.extend(chunks)
        by_park[record["park_code"]] = by_park.get(record["park_code"], 0) + len(chunks)
        source_type = record.get("source_type", "unknown")
        by_source[source_type] = by_source.get(source_type, 0) + len(chunks)

    combined = base_chunks + extended_chunks
    CHUNKS_FILE.write_text(json.dumps(combined, indent=2, ensure_ascii=False), encoding="utf-8")

    stats = {
        "existing_chunks_before_merge": len(existing),
        "base_chunks_retained": len(base_chunks),
        "extended_records": len(records),
        "extended_chunks": len(extended_chunks),
        "total_chunks_after_merge": len(combined),
        "extended_chunks_by_park": by_park,
        "extended_chunks_by_original_source": by_source,
        "backup_file": str(BACKUP_FILE),
    }
    STATS_FILE.write_text(json.dumps(stats, indent=2), encoding="utf-8")

    print(json.dumps(stats, indent=2))
    print(f"\nUpdated: {CHUNKS_FILE}")
    print("Next: run patch_existing_files.py once, then recreate Qdrant embeddings.")


if __name__ == "__main__":
    main()
