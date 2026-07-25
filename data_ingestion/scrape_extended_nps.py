"""Collect high-value NPS content for the chatbot question set.

This script is additive: it does not overwrite the existing per-park JSON files.
It writes detailed web pages and NPS API records to data/raw/extended_nps/.

Run from data_ingestion/:
    python scrape_extended_nps.py
"""
from __future__ import annotations

import json
import os
import re
import time
from collections import deque
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env")
load_dotenv(ROOT_DIR / "backend" / ".env", override=False)

OUTPUT_DIR = ROOT_DIR / "data" / "raw" / "extended_nps"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

NPS_API_KEY = os.getenv("NPS_API_KEY", "").strip()
API_BASE = "https://developer.nps.gov/api/v1"
REQUEST_DELAY_SECONDS = 0.35
MAX_WEB_PAGES_PER_PARK = 45
MAX_API_RECORDS_PER_ENDPOINT = 200

HEADERS = {
    "User-Agent": (
        "NationalParksChatbotAcademicProject/1.0 "
        "(educational RAG data collection; respectful crawl rate)"
    )
}

PARKS: Dict[str, str] = {
    "yell": "Yellowstone National Park",
    "grca": "Grand Canyon National Park",
    "yose": "Yosemite National Park",
    "zion": "Zion National Park",
}

# Curated paths are attempted directly. Missing/renamed pages are skipped safely.
CURATED_PATHS: Dict[str, List[str]] = {
    "yell": [
        "/index.htm",
        "/planyourvisit/index.htm",
        "/planyourvisit/fees.htm",
        "/planyourvisit/conditions.htm",
        "/planyourvisit/parkroads.htm",
        "/planyourvisit/safety.htm",
        "/planyourvisit/bearsafety.htm",
        "/planyourvisit/bearenc.htm",
        "/planyourvisit/backcountryhiking.htm",
        "/planyourvisit/camping-in-bear-country.htm",
        "/planyourvisit/backcountry-food-storage.htm",
        "/planyourvisit/weather.htm",
        "/learn/historyculture/index.htm",
    ],
    "grca": [
        "/index.htm",
        "/planyourvisit/index.htm",
        "/planyourvisit/visitorcenters.htm",
        "/planyourvisit/hours.htm",
        "/planyourvisit/conditions.htm",
        "/planyourvisit/roadclosures.htm",
        "/planyourvisit/accessibility.htm",
        "/planyourvisit/south-rim.htm",
        "/planyourvisit/trail-accessibility.htm",
        "/learn/historyculture/index.htm",
        "/learn/historyculture/park-history.htm",
    ],
    "yose": [
        "/index.htm",
        "/planyourvisit/index.htm",
        "/planyourvisit/halfdome.htm",
        "/planyourvisit/hdpermits.htm",
        "/planyourvisit/hdwildpermits.htm",
        "/planyourvisit/wildfaq.htm",
        "/planyourvisit/wildpermits.htm",
        "/planyourvisit/wpres.htm",
        "/planyourvisit/permitsandreservations.htm",
        "/planyourvisit/wilderness.htm",
        "/planyourvisit/eatingsleeping.htm",
        "/planyourvisit/food.htm",
        "/planyourvisit/weather.htm",
    ],
    "zion": [
        "/index.htm",
        "/planyourvisit/index.htm",
        "/planyourvisit/watchman-campground.htm",
        "/planyourvisit/campgrounds-in-zion.htm",
        "/planyourvisit/camping-in-zion.htm",
        "/planyourvisit/accessibility.htm",
        "/planyourvisit/weather-and-climate.htm",
        "/planyourvisit/weather.htm",
    ],
}

# Pages discovered from NPS links are followed only when these topics appear in
# the link text or URL. These correspond to the user's evaluation questions.
DISCOVERY_KEYWORDS = {
    "fee", "pass", "entrance", "reservation", "permit", "half dome",
    "visitor center", "hours", "road", "condition", "closure", "phone",
    "accessibility", "accessible", "wheelchair", "ada", "campground",
    "watchman", "hookup", "check-in", "check-out", "bear", "wildlife",
    "safety", "food storage", "scented", "backcountry", "wilderness",
    "history", "designated", "weather", "climate", "dining", "restaurant",
}

API_ENDPOINTS = [
    "parks",
    "feespasses",
    "visitorcenters",
    "campgrounds",
    "alerts",
    "roadevents",
    "thingstodo",
    "places",
    "articles",
]

SKIP_FIELD_NAMES = {
    "images", "image", "multimedia", "geometry", "latlong", "latitude",
    "longitude", "id", "lastindexeddate",
}


def normalize_space(text: str) -> str:
    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def canonicalize_url(url: str) -> str:
    parsed = urlparse(url)
    clean = parsed._replace(query="", fragment="")
    value = urlunparse(clean)
    return value.replace("http://", "https://", 1)


def is_same_park_page(url: str, park_code: str) -> bool:
    parsed = urlparse(url)
    if parsed.netloc not in {"www.nps.gov", "home.nps.gov"}:
        return False
    path = parsed.path.lower()
    if f"/{park_code}/" not in path:
        return False
    if not (path.endswith(".htm") or path.endswith(".html") or path.endswith("/")):
        return False
    excluded = ("/multimedia/", "/photosmultimedia/", "/learn/photosmultimedia/")
    return not any(part in path for part in excluded)


def link_is_relevant(anchor_text: str, href: str) -> bool:
    haystack = f"{anchor_text} {href}".lower().replace("-", " ")
    return any(keyword in haystack for keyword in DISCOVERY_KEYWORDS)


def extract_page(url: str, park_code: str, session: requests.Session) -> Optional[Dict[str, Any]]:
    try:
        response = session.get(url, timeout=25, allow_redirects=True)
        if response.status_code == 404:
            return None
        response.raise_for_status()
    except requests.RequestException as exc:
        print(f"  skip {url}: {exc}")
        return None

    content_type = response.headers.get("content-type", "")
    if "text/html" not in content_type:
        return None

    final_url = canonicalize_url(response.url)
    soup = BeautifulSoup(response.content, "lxml")
    main = (
        soup.find("div", id="main-content")
        or soup.find("main")
        or soup.find("article")
    )
    if not main:
        return None

    for tag in main(["script", "style", "noscript", "svg", "form", "button"]):
        tag.decompose()
    for selector in [
        "nav", "footer", ".breadcrumb", ".usa-breadcrumb", ".social-links",
        ".related-content", ".nps-footer", ".modal", ".carousel",
    ]:
        for tag in main.select(selector):
            tag.decompose()

    lines: List[str] = []
    seen_lines: Set[str] = set()
    for element in main.find_all(["h1", "h2", "h3", "h4", "p", "li", "dt", "dd", "th", "td"]):
        text = normalize_space(element.get_text(" ", strip=True))
        if not text or len(text) < 2:
            continue
        # Preserve headings to make FAQ/section chunks more searchable.
        if element.name in {"h1", "h2", "h3", "h4"}:
            text = f"## {text}"
        if text not in seen_lines:
            lines.append(text)
            seen_lines.add(text)

    page_text = normalize_space("\n".join(lines))
    if len(page_text) < 120:
        return None

    title = ""
    h1 = main.find("h1")
    if h1:
        title = normalize_space(h1.get_text(" ", strip=True))
    if not title and soup.title:
        title = normalize_space(soup.title.get_text(" ", strip=True))

    discovered: List[str] = []
    for anchor in main.find_all("a", href=True):
        href = anchor.get("href", "").strip()
        anchor_text = normalize_space(anchor.get_text(" ", strip=True))
        absolute = canonicalize_url(urljoin(final_url, href))
        if is_same_park_page(absolute, park_code) and link_is_relevant(anchor_text, absolute):
            discovered.append(absolute)

    return {
        "park_code": park_code,
        "title": title,
        "url": final_url,
        "content": page_text,
        "source_type": "nps_web",
        "discovered_links": sorted(set(discovered)),
    }


def crawl_park(park_code: str, session: requests.Session) -> List[Dict[str, Any]]:
    base = f"https://www.nps.gov/{park_code}"
    queue: deque[Tuple[str, int]] = deque()
    for path in CURATED_PATHS[park_code]:
        queue.append((canonicalize_url(urljoin(base + "/", path.lstrip("/"))), 0))

    visited: Set[str] = set()
    pages: List[Dict[str, Any]] = []

    while queue and len(pages) < MAX_WEB_PAGES_PER_PARK:
        url, depth = queue.popleft()
        url = canonicalize_url(url)
        if url in visited:
            continue
        visited.add(url)

        page = extract_page(url, park_code, session)
        time.sleep(REQUEST_DELAY_SECONDS)
        if not page:
            continue

        discovered = page.pop("discovered_links", [])
        pages.append(page)
        print(f"  web {len(pages):02d}: {page['title'][:72]}")

        if depth < 2:
            for link in discovered:
                if link not in visited:
                    queue.append((link, depth + 1))

    return pages


def humanize_key(key: str) -> str:
    key = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", key)
    key = key.replace("_", " ").replace("-", " ")
    return " ".join(word.capitalize() for word in key.split())


def flatten_record(value: Any, prefix: str = "", depth: int = 0) -> List[str]:
    if depth > 6 or value is None:
        return []
    lines: List[str] = []

    if isinstance(value, dict):
        for key, item in value.items():
            if key.lower() in SKIP_FIELD_NAMES or item in (None, "", [], {}):
                continue
            label = humanize_key(key)
            child_prefix = f"{prefix} {label}".strip()
            if isinstance(item, (dict, list)):
                lines.extend(flatten_record(item, child_prefix, depth + 1))
            else:
                lines.append(f"{child_prefix}: {item}")
    elif isinstance(value, list):
        for index, item in enumerate(value, 1):
            item_prefix = prefix if len(value) == 1 else f"{prefix} {index}".strip()
            lines.extend(flatten_record(item, item_prefix, depth + 1))
    else:
        lines.append(f"{prefix}: {value}" if prefix else str(value))
    return lines


def fetch_api_endpoint(
    park_code: str,
    endpoint: str,
    session: requests.Session,
) -> List[Dict[str, Any]]:
    if not NPS_API_KEY:
        return []

    params = {
        "parkCode": park_code,
        "api_key": NPS_API_KEY,
        "limit": MAX_API_RECORDS_PER_ENDPOINT,
        "start": 0,
    }
    try:
        response = session.get(f"{API_BASE}/{endpoint}", params=params, timeout=30)
        response.raise_for_status()
        records = response.json().get("data", [])
    except (requests.RequestException, ValueError) as exc:
        print(f"  API {endpoint}: {exc}")
        return []

    results: List[Dict[str, Any]] = []
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            continue
        title = (
            record.get("name")
            or record.get("title")
            or record.get("fullName")
            or f"{endpoint} record {index + 1}"
        )
        url = (
            record.get("url")
            or record.get("directionsUrl")
            or record.get("reservationUrl")
            or f"https://www.nps.gov/{park_code}/index.htm"
        )
        text_lines = [
            f"Park: {PARKS[park_code]}",
            f"Record Type: {humanize_key(endpoint)}",
            f"Title: {title}",
        ]
        text_lines.extend(flatten_record(record))
        text = normalize_space("\n".join(text_lines))
        if len(text) >= 80:
            results.append(
                {
                    "park_code": park_code,
                    "title": str(title),
                    "url": str(url),
                    "content": text,
                    "source_type": f"nps_api_{endpoint}",
                    "api_endpoint": endpoint,
                }
            )
    return results


def scrape_all() -> None:
    session = requests.Session()
    session.headers.update(HEADERS)

    if not NPS_API_KEY:
        print("NPS_API_KEY is not set. Web-page collection will still run.")
        print("Add NPS_API_KEY to the project-root .env for structured API enrichment.\n")

    grand_total = 0
    for park_code, park_name in PARKS.items():
        print(f"\n{'=' * 72}\nCollecting {park_name} ({park_code})\n{'=' * 72}")
        web_pages = crawl_park(park_code, session)

        api_records: List[Dict[str, Any]] = []
        for endpoint in API_ENDPOINTS:
            records = fetch_api_endpoint(park_code, endpoint, session)
            if records:
                print(f"  API {endpoint}: {len(records)} records")
                api_records.extend(records)
            time.sleep(REQUEST_DELAY_SECONDS)

        payload = {
            "park_code": park_code,
            "park_name": park_name,
            "web_pages": web_pages,
            "api_records": api_records,
            "stats": {
                "web_pages": len(web_pages),
                "api_records": len(api_records),
                "total_records": len(web_pages) + len(api_records),
            },
        }
        output_file = OUTPUT_DIR / f"{park_code}_extended.json"
        output_file.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        grand_total += payload["stats"]["total_records"]
        print(f"Saved {output_file}")

    print(f"\nCompleted extended collection: {grand_total} records")
    print(f"Output directory: {OUTPUT_DIR}")


if __name__ == "__main__":
    scrape_all()
