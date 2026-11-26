"""
Verify and summarize all 27 scraped Sales Manuals in the corpus.
"""
import glob
import json
import pathlib
import sys

from chunk_tree import chunk_page

CORPUS = pathlib.Path(__file__).resolve().parent / "corpus"
files = sorted(CORPUS.glob("*.json"))
print(f"Total corpus JSON files: {len(files)}\n")

total_chunks = 0
summary = []

for f in files:
    data = json.loads(f.read_text(encoding="utf-8"))
    family = data.get("family") or "unknown"
    mtms = data.get("mtms") or [data.get("mtm")]
    title = data.get("page_title", "")
    pub = data.get("published", "")
    
    chunks, skipped = chunk_page(data)
    total_chunks += len(chunks)
    
    types = {}
    for c in chunks:
        st = c["metadata"]["section_type"]
        types[st] = types.get(st, 0) + 1
        
    print(f"File: {f.name:<15} Family: {family:<10} MTMs: {', '.join(mtms):<25} Chunks: {len(chunks):<5} (Types: {types})")
    summary.append({
        "file": f.name,
        "family": family,
        "mtms": mtms,
        "title": title,
        "published": pub,
        "chunk_count": len(chunks),
        "types": types
    })

print(f"\n==================================================")
print(f"Grand Total: {len(files)} Sales Manuals, {total_chunks:,} clean chunks generated!")
print(f"==================================================")
