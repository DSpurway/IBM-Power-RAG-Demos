# Sales Manual RAG on the shared Spyre LPAR - deployment proposal

> Status: PROPOSAL for Andrew (box owner) and Angela. Nothing has been deployed. Read-only inspection only so far (2026-11-25).
> Host: `spyre.aixncc.uk.ibm.com` (RHEL 9.8, Power11, 128 threads, 507 GB RAM, 8x Spyre). Account: `david` (rootless podman).
> This is a long-lived tool and demo, NOT a rebuildable recipe (that is the Techzone work in `Carbon-GenAI-Demos`).

## Principles

1. Do not touch anything Andrew, Angela or `ibm` run. No stop/restart/delete, no changes to root podman, the catalog, caddy or `/etc`.
2. Everything we run is rootless podman under `david`, in `/home/david`, on ports we have agreed with Andrew.
3. We are a CLIENT of the existing Spyre LLM service. We do not claim any Spyre card.
4. No rebuilds on this box. Anything that needs rebuilding or iterating is developed on the laptop or Techzone first.

## Observed baseline (read-only, 2026-11-25 12:23 UTC)

| Resource | Total | In use / free |
|---|---|---|
| RAM | 507 GB | 243 GB used, 263 GB available |
| CPU | 128 threads | load average about 17 |
| Disk | `/home` 325 GB, `/` 140 GB | `/home` 322 GB free; `/` 57 GB free (do not use `/`) |
| Spyre | 8 cards | assumed fully allocated: two `vllm-spyre` LLM containers (104 GB and 61 GB RAM) plus Angela's TP4 workers; owners to confirm |
| Listening | 22, 443, 9191 | our ports must avoid these and all existing container ports |

## What we propose to run (all rootless, user `david`)

| Component | Image / source | RAM | CPU | Disk | Notes |
|---|---|---|---|---|---|
| OpenSearch (our own instance) | `icr.io/ppc64le-oss/opensearch-ppc64le:3.3.0` (already used in this project) | 8 GB cap | 2-4 | about 10 GB | bound to 127.0.0.1 only |
| rag-backend (Flask, single worker) | built from this repo (ppc64le wheels) | 4-6 GB | 2-4 | about 8 GB image | embeddings in-process on CPU (speed not needed) |
| carbon-rag-ui (Next.js) | built from this repo | about 0.5 GB | 1 | about 1 GB | one external port |
| LLM | NONE - call the existing Granite-4.1-8b `vllm-spyre` service as an OpenAI-compatible client | 0 | 0 | 0 | needs Andrew's OK and an endpoint reachable from our containers |

Total new footprint: roughly 15 GB RAM, 4-8 cores at peak, about 25 GB disk. That is about 3% of RAM and well under 10% of CPU.

Rebuild/ingest load: ingesting 27 servers is CPU-only and bursty. We will run it single-threaded and off-peak, and `nice` it.

## Open questions

For Andrew:
1. Is a small rootless stack under `david` acceptable, and which ports (backend, UI) may we use? Can they be reached from IBM network/VPN?
2. May we call the existing Granite-4.1-8b Spyre endpoint (the "Digital Assistant" one, `llm-1241b938ce`), and what is its URL/model name/auth? Any request-rate or context-length limit? (Its chat-bot is configured with `LLM_MAX_MODEL_LEN=32768`; a different Granite instance, probably the summarize one, runs with `--max-model-len=8096`. Confirm which is which.)
3. Which of the 8 Spyre cards, if any, are free?
4. Any policy on `/home` quota, `linger`, or long-running user services?

For Angela:
1. Is a second client on the Granite endpoint (light, interactive RAG use) acceptable alongside her work?

## What we will NOT do

- No `ai-services application create/delete`, no catalog password reset, no changes to the other users' instances.
- No Selenium/Chromium on this box (no browser installed, no x86 tooling).
- No use of IBM Docs `/docs/api` (disallowed by `robots.txt`).

## Sales Manual acquisition (decision, 2026-11-25)

Evidence gathered today (laptop, real Chrome and Selenium headless Chrome):

| Test | Result |
|---|---|
| Plain `requests` from laptop and from this LPAR (any UA/headers) | 403, Akamai, even for `/docs/en/sitemap.xml` |
| Selenium headless Chrome, default `HeadlessChrome` user-agent | Blocked (403 page), 97 s |
| Selenium headless Chrome, spoofed Chrome user-agent | Works: 15 s, 1,361,479 characters, 2 tables, `div.ibmdocs-content-container` present |

Conclusion: the best scraper is `build_scraper_temp/enhanced_chromium_scraper.py` (user-agent spoof, `truste-consent-button`, correct `By.CLASS_NAME` selector), run from the x86 laptop, not Power. The LPAR hosts only the RAG side. Code Engine remains an unproven option (its IP range may also be blocked); the laptop route does not depend on it.

Proposed shape: scrape on the laptop to a versioned local corpus (one JSON/Markdown file per server, with the page's "Published:" date), then ingest from that corpus into the LPAR via `/ingest-scraped-content`. This decouples scraping from ingestion and makes re-ingest free.

## One-server test: E980 (9080-M9S), 2026-11-25

Laptop scrape via `laptop-scraper/scrape_to_corpus.py` (reuses `enhanced_chromium_scraper.py`, spoofed Chrome UA), checked by `laptop-scraper/check_corpus.py` (real `SalesManualChunker` + BM25, no OpenSearch/LLM).

- Scrape: 1,404,385 chars, 990 sections (986 with body text), 2 tables, published "14 July 2026", about 1 minute. Answers to spec questions (weight 86.2 kg, AIX levels, temperatures, 16 TB per node) are present in the text. Scraping is NOT the problem.
- Chunking: 1,021 chunks = 1 lifecycle_table + 956 feature_code + 64 content_section. 33 chunks exceed 3000 chars. The `Models` chunk is 104,954 chars: it swallows the H3 sub-sections (Physical specifications, Operating environment, Hardware/Software requirements, Features...). About 120K chars of the page do not appear in any chunk (1.28M of 1.40M).
- Queries: lifecycle ("when withdrawn?") answered by the lifecycle_table chunk at rank 1. Spec questions (max memory, dimensions/weight, operating systems, power) did not surface the right text, because the chunker splits on H2 titles only and labels sub-sections "Description".
- Minor: degree signs arrive as U+FFFD in the page text (e.g. "5\ufffdC"); check whether this is from the source or the scraper.
- Watson Assistant: not exercised. With no key/URL the service sets `enabled=False` and `query_classifier.py` falls back to regex. New key vars: `WATSON_ASSISTANT_API_KEY`, `WATSON_ASSISTANT_URL`, `WATSON_ASSISTANT_ID`.
- Next: split by H3 inside H2 sections with a hard size cap, re-run `check_corpus.py` on E980, then scrape all 27 servers. `laptop-scraper/corpus/*.json` is about 1.4 MB per server, so keep it out of git.

## Chunker v2 on the E980, 2026-11-25 (supersedes the "Next" bullet above)

Built in `laptop-scraper/` (the shared `rag-backend/sales_manual_chunker.py` is untouched): `ibm_docs_tree.py` (rendered page -> clean section tree from the nested `article.topic` elements), `chunk_tree.py` (section-aware chunker v2), `scrape_to_corpus.py` (saves `corpus/<mtm>.html.gz` + `.json`; `--reparse <mtm>` rebuilds the JSON offline), `check_corpus.py` (10 questions, BM25).

Per-section plan implemented (from the user, matching the page's "On this page" list): lifecycle table = 1 chunk; Abstract and Description split by size and at Description's bold sub-headings (Summary of features, Memory, RAS ...); Highlights 1 chunk; Technical description = chunk per sub-heading (Physical specifications, Operating environment, Hardware/Software requirements); Publications low priority; Feature descriptions = chunk per feature; SKIPPED: Models detail (80K chars of feature conversions), Features - No charge/Chargeable, Feature availability matrix, Feature exchanges, Accessories, Supplies, Trademarks, Section 508. Every chunk starts with its section path; hard cap 1500 chars.

Result: 1,372 chunks (1 lifecycle, 108 content, 1,263 feature), max 1,569 chars (v1: 1,021 chunks, max 104,954). 8/10 questions have the answer in the top 3 by BM25; the 2 misses hold the answer in the right chunk (Abstract; Technical description > Software requirements) but rank 25th/39th lexically. Real retrieval (embeddings + reranker) is the next test, on the LPAR.

Also fixed vs the old scraper: text no longer glued ("M9SSystem nodeWidth:"), hard-wrapped lines collapsed, U+FFFD degree signs gone (0 found), tables and nested lists rendered cleanly. Raw HTML is only 0.25 MB gzipped per server, so `*.html.gz` can be committed (the JSON is git-ignored).

Open decisions: (1) "Features - Chargeable" (55K chars, classification-style list) is skipped for now; (2) how chunks reach the backend: v1 `/ingest-scraped-content` chunks internally, so we need either a new `/ingest-chunks` endpoint or to port `chunk_tree.py` into rag-backend; (3) 26 more servers to scrape and check, since page layouts differ between generations (POWER9/10/11).

## Power11 check: Power S1112 (family 9242-01), 2026-11-25

Scraped with the same pipeline (`scrape_to_corpus.py https://www.ibm.com/docs/en/announcements/family-9242-01-power-s1112`). Corpus files are now named by family: `9080-03` (E980) and `9242-01` (S1112).

- Same 11 top-level sections as the E980, plus a top-level "Terms of use" (skipped). Case differs ("Technical Description"); handled. Operating environment has a 3rd/4th heading level (Electrical characteristics, Environment Requirements ...); handled by recursion. 451 chunks (1 lifecycle, 61 content, 389 feature), max 1,552 chars. 7/10 BM25 questions pass; the 3 misses are lexical artefacts (lifecycle goes through direct table lookup; memory answer is at rank 5; my test tokenizer separates `#0004` from `0004`).
- A page is a FAMILY and can cover several MTMs: S1112 = 9242-21B (rack) + 9242-21T (tower); E980 = 9080-M9S only. `parse_page` now returns `family`, `mtms` and `mtm`; chunk metadata carries `family`, `mtms`, `mtm`. DECISION NEEDED: collection key = family (`9242-01`), not MTM (v1 uses `RAG_DB_mtm_<mtm>`). Both MTMs of a family would map to the same collection.
- Feature chunks on family pages contain per-model blocks ("For 9242-21B" / "For 9242-21T"); v1 `_parse_feature_metadata` parses min/max once, so those numbers may reflect only the first model. Worth a refinement.
- Lifecycle table differs: 5 columns (no "Support level changed") and dates like "14 July 2026". The v1 backend table lookup only parses ISO dates, so the v2 chunker converts them to ISO (`2026-07-14`). Verified with the real `_parse_lifecycle_table` for E980 and S1112 (both MTMs; "-" = not yet withdrawn).
- Lifecycle bug fixed (2026-11-25): `TableLookupService._parse_lifecycle_table` now uses header-aware column detection and safe markdown splitting. Real E980 (6-col with empty 6th cell) correctly identifies Support Level Changed = 2027-12-31 and Service Discontinued = Not yet announced.
- Full 27-server corpus complete (2026-11-25): All 27 IBM Power Sales Manuals scraped into `laptop-scraper/corpus/` (`*.html.gz` and `*.json`), producing 21,854 clean chunks verified across POWER9, POWER10, and POWER11.
- Ingestion endpoint added: `/api/ingest-chunks` in `rag-backend/app.py` for direct batch embedding and bulk indexing.
- Non-breaking hyphens (U+2011, 29 on S1112) are normalised to "-".
- The old `rag-backend/sales_manual_chunker.py` is left in place for reference; TODO later: remove it once v2 is the only path, to avoid confusion.
- Decided: "Features - Chargeable" stays skipped.
