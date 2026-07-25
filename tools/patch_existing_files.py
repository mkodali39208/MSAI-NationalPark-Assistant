"""Patch the existing repository for metadata-safe LangChain retrieval.

Place this file in national-parks-chatbot/tools/ and run from the project root:
    python tools/patch_existing_files.py

The script creates .before_coverage_upgrade backups and is idempotent.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EMBEDDINGS_FILE = ROOT / "data_ingestion" / "create_embeddings.py"
PIPELINE_FILE = ROOT / "backend" / "pipeline.py"


def backup(path: Path) -> None:
    backup_path = path.with_suffix(path.suffix + ".before_coverage_upgrade")
    if not backup_path.exists():
        backup_path.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"Backup created: {backup_path}")


def patch_embeddings() -> None:
    path = EMBEDDINGS_FILE
    text = path.read_text(encoding="utf-8")
    backup(path)

    old = '''                "source_url": chunk["source_url"],\n                "chunk_id": chunk["id"]\n'''
    new = '''                "source_url": chunk["source_url"],\n                "source_type": chunk.get("source_type", "nps"),\n                "title": chunk.get("title", ""),\n                "chunk_id": chunk["id"],\n                # LangChain QdrantVectorStore reads document metadata from this nested object.\n                # Flat fields above are intentionally retained for fast Qdrant filtering.\n                "metadata": {\n                    "park_code": chunk["park_code"],\n                    "park_name": chunk["park_name"],\n                    "chunk_index": chunk["chunk_index"],\n                    "source_url": chunk["source_url"],\n                    "source_type": chunk.get("source_type", "nps"),\n                    "title": chunk.get("title", ""),\n                    "chunk_id": chunk["id"],\n                },\n'''
    if old in text:
        text = text.replace(old, new, 1)
        path.write_text(text, encoding="utf-8")
        print(f"Patched metadata payload: {path}")
    elif '"metadata": {' in text and '"source_type": chunk.get' in text:
        print(f"Already patched: {path}")
    else:
        raise RuntimeError(
            f"Could not locate expected payload block in {path}. Restore from Git or patch manually."
        )


def patch_pipeline() -> None:
    path = PIPELINE_FILE
    text = path.read_text(encoding="utf-8")
    backup(path)

    old_vectorstore = '''            embedding=_get_embeddings(),\n            content_payload_key="text",  # matches payload key used when building the index\n'''
    new_vectorstore = '''            embedding=_get_embeddings(),\n            content_payload_key="text",  # matches payload key used when building the index\n            metadata_payload_key="metadata",\n'''
    if old_vectorstore in text:
        text = text.replace(old_vectorstore, new_vectorstore, 1)
    elif 'metadata_payload_key="metadata"' not in text:
        raise RuntimeError(f"Could not locate QdrantVectorStore configuration in {path}.")

    old_prompt_end = '''- When answering follow-up questions, reference previous parts of the conversation naturally\n- If a user's question refers to "it" or "there", use conversation context to understand what they mean"""'''
    new_prompt_end = '''- When answering follow-up questions, reference previous parts of the conversation naturally\n- If a user's question refers to "it" or "there", use conversation context to understand what they mean\n- Use the retrieved context as the factual source; do not invent fees, permit quotas, hours, phone numbers, accessibility details, or safety instructions\n- For time-sensitive facts such as current closures, current hours, fees, reservations, and conditions, mention that visitors should verify the cited official NPS source before travel\n- Do not claim an objectively "best" restaurant. Describe official dining options found in context and explain that the best choice depends on preferences\n- Do not predict weather a month in advance. Provide seasonal climate expectations only when supported by context and recommend checking an official short-range forecast closer to the visit"""'''
    if old_prompt_end in text:
        text = text.replace(old_prompt_end, new_prompt_end, 1)

    path.write_text(text, encoding="utf-8")
    print(f"Patched vector metadata and response guardrails: {path}")


def main() -> None:
    if not EMBEDDINGS_FILE.exists() or not PIPELINE_FILE.exists():
        raise FileNotFoundError("Run this script from inside the national-parks-chatbot repository.")
    patch_embeddings()
    patch_pipeline()
    print("\nPatch complete. Recreate the Qdrant collection so every point contains nested metadata.")


if __name__ == "__main__":
    main()
