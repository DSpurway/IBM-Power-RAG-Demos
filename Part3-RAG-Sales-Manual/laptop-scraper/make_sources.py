#!/usr/bin/env python3
"""Generate rag-backend/sources.json from the scraped corpus.

The corpus (laptop-scraper/corpus/<family>.json) is the single source of truth for
which IBM Sales Manual pages the assistant knows about, so the UI's Sources page
never keeps its own hand-written server list.

    python make_sources.py            # writes ../rag-backend/sources.json
    python make_sources.py --check    # exit 1 if sources.json is out of date

Add another documentation set later by adding another entry to SETS.
"""
import argparse
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CORPUS = os.path.join(HERE, "corpus")
OUT = os.path.join(HERE, "..", "rag-backend", "sources.json")

SETS = [
    {
        "id": "sales-manuals",
        "title": "IBM Power Sales Manuals",
        "description": "Official IBM announcement Sales Manuals, one page per server family.",
        "corpus_dir": CORPUS,
    },
]


def source_from_corpus(path):
    with open(path, encoding="utf-8") as f:
        j = json.load(f)
    family = os.path.basename(path)[: -len(".json")]
    name = j.get("server_name_hint") or re.sub(r"^Family \S+ ", "", j.get("page_title", family))
    return {
        "family": family,
        "name": name,
        "mtms": j.get("mtms") or ([j["mtm"]] if j.get("mtm") else []),
        "url": j["url"],
        "published": j.get("published"),
        "scraped_at": j.get("scraped_at"),
    }


def build():
    sets = []
    for s in SETS:
        sources = [source_from_corpus(p) for p in glob.glob(os.path.join(s["corpus_dir"], "*.json"))]
        sources.sort(key=lambda x: x["family"])
        sets.append({k: s[k] for k in ("id", "title", "description")} | {"sources": sources})
    return {"sets": sets}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    text = json.dumps(build(), indent=2, ensure_ascii=False) + "\n"
    if args.check:
        current = open(OUT, encoding="utf-8").read() if os.path.exists(OUT) else ""
        if current != text:
            print("sources.json is out of date - run make_sources.py", file=sys.stderr)
            return 1
        return 0
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    n = sum(len(s["sources"]) for s in json.loads(text)["sets"])
    print(f"wrote {os.path.normpath(OUT)} ({n} sources)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
