"""
Client script to push local corpus chunks into the RAG backend via /api/ingest-chunks.

Usage:
  python ingest_corpus_to_backend.py --backend-url http://localhost:8081 [--family 9080-03] [--all]
"""
import argparse
import json
import pathlib
import sys
import requests

from chunk_tree import chunk_page

CORPUS = pathlib.Path(__file__).resolve().parent / "corpus"


def ingest_file(filepath: pathlib.Path, backend_url: str):
    data = json.loads(filepath.read_text(encoding="utf-8"))
    family = data.get("family") or "unknown"
    mtms = data.get("mtms") or [data.get("mtm")]
    title = data.get("page_title", "Untitled")
    url = data.get("url", "unknown")
    published = data.get("published", "")
    
    chunks, skipped = chunk_page(data)
    print(f"\n---> Uploading {title} ({family}, {len(chunks)} chunks)...")
    
    payload = {
        "family": family,
        "mtms": mtms,
        "server_name": title,
        "url": url,
        "published": published,
        "replace": True,  # chunk ids are positional; drop the old index so a re-chunk leaves nothing stale
        "chunks": chunks
    }
    
    endpoint = f"{backend_url.rstrip('/')}/api/ingest-chunks"
    resp = requests.post(endpoint, json=payload, timeout=300)
    
    if resp.status_code == 200:
        res = resp.json()
        print(f"     [SUCCESS] Indexed {res.get('indexed', 0)} chunks into {res.get('collection')}")
        print(f"     Distribution: {res.get('chunk_distribution')}")
        return True
    else:
        print(f"     [FAILED] HTTP {resp.status_code}: {resp.text[:300]}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Ingest local Sales Manual corpus into RAG backend")
    parser.add_argument("--backend-url", default="http://localhost:8081", help="RAG backend URL (default: http://localhost:8081)")
    parser.add_argument("--family", default=None, help="Specific family key (e.g. 9080-03)")
    parser.add_argument("--all", action="store_true", help="Ingest all 27 corpus files")
    args = parser.parse_args()

    files = sorted(CORPUS.glob("*.json"))
    if args.family:
        target_files = [f for f in files if args.family.lower() in f.stem.lower()]
    elif args.all:
        target_files = files
    else:
        print(f"Found {len(files)} corpus files. Specify --all to ingest all or --family <id>.")
        return

    print(f"Starting ingestion of {len(target_files)} Sales Manuals to {args.backend_url}...")
    success = 0
    fail = 0
    for i, f in enumerate(target_files, 1):
        print(f"\n[{i}/{len(target_files)}] Processing {f.name}")
        ok = ingest_file(f, args.backend_url)
        if ok:
            success += 1
        else:
            fail += 1

    print(f"\n=== Ingestion complete: {success} succeeded, {fail} failed ===")


if __name__ == "__main__":
    main()
