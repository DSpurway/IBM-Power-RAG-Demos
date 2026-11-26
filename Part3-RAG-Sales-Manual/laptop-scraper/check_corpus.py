"""
Offline content-quality check for one scraped server (no OpenSearch, embeddings or LLM).
Chunks the corpus tree with chunk_tree.py and answers sample questions with a lexical (BM25) retriever.
For each question a key string that MUST be in the retrieved text is given; we report the rank where it first appears.

Usage: python check_corpus.py corpus/9080-m9s.json
"""
import json
import pathlib
import re
import sys
from collections import Counter

from rank_bm25 import BM25Okapi

from chunk_tree import MAX_CHARS, chunk_page

page = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
chunks, skipped = chunk_page(page)

print(f"{page['page_title']} | published {page['published']}")
print(f"chunks: {len(chunks)}  by type: {dict(Counter(c['metadata']['section_type'] for c in chunks))}")
print(f"by top section: {dict(Counter(c['metadata']['section_path'].split(' > ')[0] for c in chunks if c['metadata']['section_type']=='content_section'))}")
lens = sorted(len(c["text"]) for c in chunks)
print(f"chunk chars: min {lens[0]}, median {lens[len(lens)//2]}, max {lens[-1]} (cap {MAX_CHARS}; >cap+200: {sum(1 for n in lens if n > MAX_CHARS+200)})")
print("skipped:")
for p, n, why in skipped:
    print(f"   {n:>8,} chars  {p}")

tok = lambda t: re.findall(r"[a-z0-9\-\+\.#]+", t.lower())  # noqa: E731
bm = BM25Okapi([tok(c["text"]) for c in chunks])

QUERIES_BY_FAMILY = {
    "9080-03": [  # Power E980
        ("When was the E980 withdrawn from marketing?", "2022-10-31"),
        ("What is the maximum memory per system node?", "16 TB"),
        ("What is the maximum number of POWER9 cores?", "192 POWER9 cores"),
        ("Which AIX versions are required to install AIX on the E980?", "AIX Version 7.3"),
        ("What is the weight of the E980 system node?", "86.2 kg"),
        ("What is the recommended operating temperature range?", "recommended operating"),
        ("What minimum HMC level is needed?", "9.2.95"),
        ("What does feature EN2A provide?", "(#EN2A)"),
        ("Does the E980 support Active Memory Mirroring?", "Active Memory Mirroring"),
        ("What RAS features protect the memory subsystem?", "Memory subsystem RAS"),
    ],
    "9242-01": [  # Power S1112 (Power11)
        ("When will the Power S1112 be available?", "2026-07-24"),
        ("What is the weight of the S1112 tower model?", "24.5 kg"),
        ("What is the maximum power consumption?", "550 W"),
        ("Which AIX 7.3 technology level is required?", "7300-04"),
        ("How much memory can the S1112 support?", "512"),
        ("What processor core counts are offered?", "4 and 10 cores"),
        ("Is there a tower model as well as a rack model?", "21T"),
        ("What does feature code 0004 do?", "(#0004)"),
        ("Does the S1112 support Active Memory Mirroring?", "Active Memory Mirroring"),
        ("What are the service clearances?", "Service clearances"),
    ],
}
QUERIES = QUERIES_BY_FAMILY.get(page.get("family"), [])
print(f"family {page.get('family')} mtms {page.get('mtms')} mtm {page.get('mtm')}")
found = 0
for q, must in QUERIES:
    sc = bm.get_scores(tok(q))
    top = sorted(range(len(chunks)), key=lambda i: -sc[i])[:5]
    rank = next((r for r, i in enumerate(top, 1) if must.lower() in chunks[i]["text"].lower()), None)
    found += 1 if rank and rank <= 3 else 0
    t1 = chunks[top[0]]["metadata"]
    print(f"\n{'PASS' if rank and rank<=3 else 'MISS'} rank={rank}  Q: {q}\n   must contain {must!r}; top1 = [{t1['section_type']}] {t1['section_path']} ({len(chunks[top[0]]['text'])} chars)")
print(f"\n{found}/{len(QUERIES)} questions have the answer text in the top 3")
