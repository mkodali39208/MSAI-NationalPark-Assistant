"""Audit the user's evaluation questions against the actual Qdrant collection.

Run from data_ingestion/ after rebuilding embeddings:
    python audit_question_coverage.py

Outputs data/processed/question_coverage_report.csv and .json.
"""
from __future__ import annotations

import csv
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import cohere
from dotenv import load_dotenv
from qdrant_client import QdrantClient, models

ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env")
load_dotenv(ROOT_DIR / "backend" / ".env", override=False)

COLLECTION = "national_parks"
MODEL = "embed-english-v3.0"
OUTPUT_CSV = ROOT_DIR / "data" / "processed" / "question_coverage_report.csv"
OUTPUT_JSON = ROOT_DIR / "data" / "processed" / "question_coverage_report.json"

QUESTION_CASES: List[Dict[str, Optional[str]]] = [
    {"park_code": "yell", "question": "How much does a 7-day vehicle pass cost to enter Yellowstone National Park?"},
    {"park_code": "yell", "question": "Do I need a reservation to enter Yellowstone National Park?"},
    {"park_code": "yell", "question": "Is entrance to Yellowstone free for children?"},
    {"park_code": "grca", "question": "What are the hours for the South Rim Visitor Center at Grand Canyon?"},
    {"park_code": "grca", "question": "Is the South Rim open all year at Grand Canyon?"},
    {"park_code": "grca", "question": "Who can I call for current road conditions and closures at Grand Canyon?"},
    {"park_code": "yose", "question": "Do I need a permit to day-hike Half Dome in Yosemite?"},
    {"park_code": "yose", "question": "How many day-hike permits are issued for Half Dome each day?"},
    {"park_code": "yose", "question": "Can backpackers get a Half Dome permit without entering the lottery?"},
    {"park_code": "yell", "question": "How far should I stay away from bears in Yellowstone?"},
    {"park_code": "yell", "question": "What should I do if a bear charges me in Yellowstone?"},
    {"park_code": "yell", "question": "Is it recommended to hike alone in bear country?"},
    {"park_code": "yell", "question": "What should I do if I encounter a bear in Yellowstone?"},
    {"park_code": "yell", "question": "Can I bring bear spray on an airplane?"},
    {"park_code": "zion", "question": "Does Watchman Campground in Zion require reservations?"},
    {"park_code": "zion", "question": "Are there RV hookups at Watchman Campground?"},
    {"park_code": "zion", "question": "What are the check-in and check-out times at Watchman Campground?"},
    {"park_code": "grca", "question": "Is the Grand Canyon Visitor Center wheelchair accessible?"},
    {"park_code": "grca", "question": "Is the Rim Trail at Grand Canyon accessible to wheelchair users?"},
    {"park_code": "zion", "question": "How many ADA-accessible campsites are at Watchman Campground?"},
    {"park_code": "grca", "question": "When was Grand Canyon designated a national park?"},
    {"park_code": "yell", "question": "What percentage of Yellowstone's entrance fee revenue stays in the park?"},
    {"park_code": "yose", "question": "What percentage of Yosemite is designated Wilderness?"},
    {"park_code": "yell", "question": "What should I do with food and scented items while camping in Yellowstone's backcountry?"},
    {"park_code": "yose", "question": "What is the best restaurant to eat at near Yosemite?"},
    {"park_code": "zion", "question": "Can you predict what the weather will be like at Zion National Park next month?"},
]


def clean_preview(text: str, length: int = 500) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text[:length]


def coverage_label(score: float, payload_text: str) -> str:
    # This is a triage label, not a factual correctness guarantee.
    if score >= 0.55 and len(payload_text) >= 120:
        return "strong_candidate"
    if score >= 0.38 and len(payload_text) >= 80:
        return "review_candidate"
    return "weak_or_missing"


def main() -> None:
    qdrant_url = os.getenv("QDRANT_URL", "").strip()
    qdrant_key = os.getenv("QDRANT_API_KEY", "").strip()
    cohere_key = os.getenv("COHERE_API_KEY", "").strip()
    if not all([qdrant_url, qdrant_key, cohere_key]):
        raise RuntimeError("QDRANT_URL, QDRANT_API_KEY, and COHERE_API_KEY are required.")

    qdrant = QdrantClient(url=qdrant_url, api_key=qdrant_key)
    co = cohere.ClientV2(cohere_key)

    questions = [case["question"] for case in QUESTION_CASES]
    embedded = co.embed(
        texts=questions,
        model=MODEL,
        input_type="search_query",
        embedding_types=["float"],
    ).embeddings.float_

    report: List[Dict[str, Any]] = []
    for index, (case, vector) in enumerate(zip(QUESTION_CASES, embedded), 1):
        park_code = case["park_code"]
        search_filter = None
        if park_code:
            search_filter = models.Filter(
                must=[
                    models.FieldCondition(
                        key="park_code",
                        match=models.MatchValue(value=park_code),
                    )
                ]
            )

        result = qdrant.query_points(
            collection_name=COLLECTION,
            query=vector,
            query_filter=search_filter,
            limit=5,
            with_payload=True,
        )
        points = result.points
        top = points[0] if points else None
        payload = (top.payload or {}) if top else {}
        text = str(payload.get("text", ""))
        score = float(top.score) if top else 0.0

        row = {
            "number": index,
            "park_code": park_code or "",
            "question": case["question"],
            "result_count": len(points),
            "top_score": round(score, 4),
            "coverage": coverage_label(score, text),
            "top_title": payload.get("title") or payload.get("metadata", {}).get("title", ""),
            "top_source_url": payload.get("source_url") or payload.get("metadata", {}).get("source_url", ""),
            "top_source_type": payload.get("source_type") or payload.get("metadata", {}).get("source_type", ""),
            "top_preview": clean_preview(text),
            "top_5": [
                {
                    "score": round(float(point.score), 4),
                    "park_code": (point.payload or {}).get("park_code", ""),
                    "title": (point.payload or {}).get("title", ""),
                    "source_url": (point.payload or {}).get("source_url", ""),
                    "preview": clean_preview((point.payload or {}).get("text", ""), 220),
                }
                for point in points
            ],
        }
        report.append(row)
        print(
            f"{index:02d}. {row['coverage']:<17} score={row['top_score']:.4f} "
            f"results={row['result_count']} | {case['question']}"
        )
        if row["top_title"]:
            print(f"    {row['top_title']} | {row['top_source_url']}")

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    csv_fields = [
        "number", "park_code", "question", "result_count", "top_score",
        "coverage", "top_title", "top_source_url", "top_source_type", "top_preview",
    ]
    with OUTPUT_CSV.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=csv_fields)
        writer.writeheader()
        for row in report:
            writer.writerow({key: row[key] for key in csv_fields})
    OUTPUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    counts: Dict[str, int] = {}
    for row in report:
        counts[row["coverage"]] = counts.get(row["coverage"], 0) + 1
    print(f"\nCoverage summary: {counts}")
    print(f"CSV report:  {OUTPUT_CSV}")
    print(f"JSON report: {OUTPUT_JSON}")
    print("Review the retrieved preview/source for factual completeness; similarity alone is not proof of correctness.")


if __name__ == "__main__":
    main()
