# Ollama RHEL/Power Checkpoint

## Current State (29 Sep 2026 — end of session)

Fresh TechZone RHEL 10.2 VM is fully running and healthy with linger enabled.
All 4 containers are up and healthy, `granite4:latest` is loaded in Ollama.

**Important:** The scraper (Code Engine app `ibm-docs-scraper-enhanced`) is currently broken — it cannot render IBM Docs Sales Manual pages. The 25 servers with boilerplate content still need re-ingesting. The scraper **was working earlier this week** before commit `73e6ef2` introduced the DOM selector bug. The current failure is a **different, unresolved issue** — see "Current Scraper Failure" section below.

| Service | Image | Target Port | Status |
|---|---|---|---|
| opensearch-service | icr.io/ppc64le-oss/opensearch-ppc64le:3.3.0 | 9200 | Up (healthy) |
| ollama-service | icr.io/ppc64le-oss/ollama-ppc64le:v0.17.6 | 11434 | Up (healthy, `granite4:latest` loaded) |
| rag-backend | localhost/rag-backend:latest | 8081 | Up (healthy, **SCRAPER_URL now set correctly**) |
| carbon-rag-ui | localhost/carbon-rag-ui:latest | 3001 | Up (serving HTTP 200) |

## Live URLs

- **Carbon UI:** [http://pvm1-jm07pj3k.p1206.pok-systems.techzone.ibm.com:3001](http://pvm1-jm07pj3k.p1206.pok-systems.techzone.ibm.com:3001)
- **RAG Backend API:** [http://pvm1-jm07pj3k.p1206.pok-systems.techzone.ibm.com:8081](http://pvm1-jm07pj3k.p1206.pok-systems.techzone.ibm.com:8081)
- **Ollama API:** [http://pvm1-jm07pj3k.p1206.pok-systems.techzone.ibm.com:11434](http://pvm1-jm07pj3k.p1206.pok-systems.techzone.ibm.com:11434)
- **OpenSearch:** [http://pvm1-jm07pj3k.p1206.pok-systems.techzone.ibm.com:9200](http://pvm1-jm07pj3k.p1206.pok-systems.techzone.ibm.com:9200)

## TechZone VM

- **Request ID:** `6aba42692d240453565e1d9e`
- **Hostname:** `pvm1-jm07pj3k.p1206.pok-systems.techzone.ibm.com`
- **OS:** RHEL 10.2 (Coughlan), ppc64le
- **RAM:** 48GB, **Disk:** 90GB
- **SSH user:** `U9XTAN2`
- **SSH key:** `C:\Users\029878866\Downloads\rag_key_p1206.pem`

```bash
ssh -o ControlMaster=no -i "C:\Users\029878866\Downloads\rag_key_p1206.pem" -o StrictHostKeyChecking=no U9XTAN2@pvm1-jm07pj3k.p1206.pok-systems.techzone.ibm.com "your command here"
```

## OpenSearch Index State

| MTM | Server | Docs | Content |
|---|---|---|---|
| 9080-M9S | E980 | 1022 | ✅ Real content (ingested 14:11 UTC today) |
| 9080-HEX | E1080 | 1 | ❌ Boilerplate (needs re-ingest) |
| 9043-MRX | E1050 | 1 | ❌ Boilerplate (needs re-ingest) |
| 9080-HEU | E1180 | 1 | ❌ Boilerplate (needs re-ingest) |
| 9043-MRU | E1150 | 1 | ❌ Boilerplate (needs re-ingest) |
| 9824-42A | S1124 | 1 | ❌ Boilerplate (needs re-ingest) |
| 9824-22A | S1122 | 1 | ❌ Boilerplate (needs re-ingest) |
| 9028-21N | S1112 | 1 | ❌ Boilerplate (needs re-ingest) |
| 9105-42A | S1024 | 1 | ❌ Boilerplate (needs re-ingest) |
| 9105-22A | S1022 | 1 | ❌ Boilerplate (needs re-ingest) |
| 9105-41B | S1014 | 1 | ❌ Boilerplate (needs re-ingest) |
| 9028-21B | S1012 | 1 | ❌ Boilerplate (needs re-ingest) |
| 9786-42H | L1024 | 1 | ❌ Boilerplate (needs re-ingest) |
| 9786-22H | L1022 | 1 | ❌ Boilerplate (needs re-ingest) |
| 9040-MR9 | E950 | 1 | ❌ Boilerplate (needs re-ingest) |
| 9009-42A | S924 | 1 | ❌ Boilerplate (needs re-ingest) |
| 9009-42G | S924-G | 1 | ❌ Boilerplate (needs re-ingest) |
| 9009-22A | S922 | 1 | ❌ Boilerplate (needs re-ingest) |
| 9009-22G | S922-G | 1 | ❌ Boilerplate (needs re-ingest) |
| 9009-41A | S914 | 1 | ❌ Boilerplate (needs re-ingest) |
| 9009-41G | S914-G | 1 | ❌ Boilerplate (needs re-ingest) |
| 9223-42S | H924 | 1 | ❌ Boilerplate (needs re-ingest) |
| 9223-22S | H922 | 1 | ❌ Boilerplate (needs re-ingest) |
| 9183-22X | IC922 | 1 | ❌ Boilerplate (needs re-ingest) |
| 9008-22L | L922 | 1 | ❌ Boilerplate (needs re-ingest) |
| 9006-22P | LC922 | 1 | ❌ Boilerplate (needs re-ingest) |
| 9006-12P | LC921 | 1 | ❌ Boilerplate (needs re-ingest) |
| rag_power_announcements | — | 8 | ❌ 0 real chunks (scraper was broken) |

## Scraper Bug History

### Original bug (commit `73e6ef2`)
Broad DOM selectors (`article`, `main`, `body`) caused the scraper to capture the IBM 403 error page instead of real content. This put 1-doc boilerplate into 25 of 26 indexes.

### Current state of `build_scraper_temp/enhanced_chromium_scraper.py`
Multiple iterations were deployed today trying to fix the scraper. The current deployed version:
- Clicks `id="truste-consent-button"` (TrustArc "Accept All") ✅ — this is working per logs
- Waits up to 120s for `ibmdocs-content-container` to appear in the DOM
- Falls back to text signal "Product life cycle dates" / "Sales manual"
- Returns HTTP 500 with `html_length ~138KB` if neither found

### Current Scraper Failure — What We Know

**Symptom:** IBM Docs pages load their SPA shell (warmup.html, ~138KB) but the content API call never completes — the spinner stays forever in headless Chrome.

**Browser console logs captured from Code Engine Chromium:**
```
[SEVERE] https://www.ibm.com/docs/en/announcements/power-system-s924-9009-42g
         Failed to load resource: the server responded with a status of 403 ()
[SEVERE] Refused to set unsafe header "origin"
```

**Root cause hypothesis:** The IBM Docs SPA makes an internal API call to fetch content. That API call returns 403 in the Code Engine environment. This could be due to:
1. **User-Agent** — headless Chrome sends a `HeadlessChrome` UA string that IBM detects and blocks (most likely — a UA spoof fix was deployed as the last build `ibm-docs-scraper-enhanced-run-260929-190105603` but not yet tested)
2. **Missing headers** — `Origin`, `Referer`, or a session token that a real browser sends
3. **Something else that changed** since the scraper last worked (earlier this week)

**Key fact:** This scraper worked earlier this week. IBM Docs pages are publicly accessible. The fix is almost certainly a small configuration change, not a structural problem.

**Last build deployed:** `ibm-docs-scraper-enhanced-run-260929-190105603`
**Change in that build:** Added `--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 ...` to Chromium options.
**Not yet tested** — session ended before verification.

## rag-backend Container Start Command

The `rag-backend` container must be started with `SCRAPER_URL` set. If it ever gets restarted (e.g. after a VM reboot), use this script:

```bash
bash /tmp/restart_backend.sh
```

The script is at `/tmp/restart_backend.sh` on the VM. If it has been lost, the key flags are:
- `--network podman_rag-net` (the compose network — NOT `podman`)
- `-e SCRAPER_URL=https://ibm-docs-scraper-enhanced.29bw00k1vhg4.eu-gb.codeengine.appdomain.cloud`

## Next Steps (Step 1 is the immediate action)

1. **Test the User-Agent fix** — the last deployed build added a real browser UA string. Test it from the local machine:
   ```bash
   python call_classes.py   # currently calls /classes with wait=30
   ```
   OR switch it back to `/scrape` to do a full test. Check for the 403 in console logs — if it's gone, the content should render.

2. **If UA fix didn't work — compare with the version that did work.** The scraper worked earlier this week. Check git log to find the last working commit before `73e6ef2` and compare `create_driver()` and the wait logic carefully for any other differences (e.g. window size, additional Chrome flags, different wait timeouts that happened to be long enough).
   ```bash
   git log --oneline build_scraper_temp/enhanced_chromium_scraper.py
   git diff <working-commit> HEAD -- build_scraper_temp/enhanced_chromium_scraper.py
   ```

3. **Once scraper is verified working** — force re-ingest all 25 broken servers:
   ```bash
   curl -s -X POST http://localhost:8081/api/start-bulk-ingestion \
     -H 'Content-Type: application/json' -d '{"force": true}'
   ```
   Monitor with: `curl -s http://localhost:8081/api/bulk-ingestion-status`

4. **Verify spot-check** after first server completes — use `/tmp/verify_content.py` to confirm doc count > 1 and content is real.

5. **Trigger announcement ingestion** — once Sales Manuals are clean, ingest the 200 announcements.

## Starting a New Task

Paste this into the first message of the new task:

---

Continuing Part3-RAG-Sales-Manual on TechZone RHEL 10.2 VM.

**VM:** `pvm1-jm07pj3k.p1206.pok-systems.techzone.ibm.com`
**User:** `U9XTAN2`
**Key:** `C:\Users\029878866\Downloads\rag_key_p1206.pem`
**UI URL:** `http://pvm1-jm07pj3k.p1206.pok-systems.techzone.ibm.com:3001`

**Current Status:**
- All 4 containers UP & healthy. `rag-backend` has `SCRAPER_URL` set correctly.
- E980 (9080-M9S): ✅ 1022 real chunks in OpenSearch.
- Other 25 servers: ❌ 1 boilerplate chunk each — need force re-ingest.
- Code Engine scraper: ❌ Currently returning HTTP 500 — SPA content API returning 403 in headless Chrome. Last fix attempt (UA spoof) deployed but **not yet tested**.
- Announcements: scan works (200 found), ingestion needs scraper to be working first.

**Immediate Next Step:**
1. Run `python call_classes.py` (on local machine, not VM) to test the UA-spoof build.
2. Check console logs — if no 403, switch to `/scrape` and verify full content extraction.
3. If still failing, diff against last known-working git commit of the scraper.
4. Once scraper verified, trigger bulk re-ingest with `force: true`.

See `CHECKPOINT_OLLAMA_RHEL.md` for full context, root cause analysis, and commands.

---


---

## UPDATE 2026-11-25 - Pivot: shared Spyre LPAR (Techzone unavailable)

Read [`SPYRE_LPAR_PLAN.md`](SPYRE_LPAR_PLAN.md) first. Summary:
- New target: `spyre.aixncc.uk.ibm.com` (owner Andrew; shared with Angela and `ibm`). SSH works as `david` (passwordless sudo, but DO NOT use it to touch others' services). Credentials are NOT stored here; they are in the user's 1Password.
- It already runs IBM AI Services / Launchpad (ai-services CLI v0.4.0, root podman, catalog UI :9191). Do not rebuild or redeploy any of it. Spyre cards assumed fully allocated; we are a client of the existing Granite-4.1-8b vllm-spyre service.
- Long-lived tool/demo, not a rebuildable recipe. Get Andrew's OK on the plan BEFORE deploying anything.
- Scraper decision & status: Code Engine scraper (`ibm-docs-scraper-enhanced`) is DEPLOYED and VERIFIED WORKING on IBM Cloud (2026-11-25). User-agent spoofing resolved the 403 error; live test returned 2.8 MB rendered HTML and 989 sections for S924. Code Engine will be used for periodic automated lifecycle scans and update tracking.
- DONE 2026-11-25:
  1. ✅ Fixed lifecycle table parsing bug in `table_lookup_service.py`: header-aware column detection, safe markdown pipe splitting preserving empty cells, and clear distinction between End of Standard Support (`support_level_changed`) and End of Extended Support (`discontinued`).
  2. ✅ Scraped all 27 IBM Power Sales Manuals into `laptop-scraper/corpus/` (`*.html.gz` and clean `*.json` trees) across POWER9, POWER10, and POWER11. Verified all 27 with `verify_corpus.py` (21,854 section-aware chunks generated).
  3. ✅ Ported `ibm_docs_tree.py` and `chunk_tree.py` directly into `rag-backend/`, with self-contained feature metadata parsing and SHA-256 content hashing.
  4. ✅ Added `/api/ingest-chunks` and updated `/ingest-scraped-content` in `rag-backend/app.py` with hash comparison skip logic and bulk indexing.
  5. ✅ Deployed and tested Code Engine scraper (`ibm-docs-scraper-enhanced`) on IBM Cloud — HTTP 200, full 2.8MB DOM extraction confirmed.

- NEXT STEPS:
  1. Collections & Family routing: Ensure family-based collections (`rag_family_<id>`) and MTM mapping in `query_classifier.py` and `app.py`.
  2. Align `carbon-rag-ui` with Carbon AI Chat patterns (Option 1: keep specialized lifecycle/feature cards with polished Carbon AI chat bubbles).
  3. Explore official AI Services / Launchpad reranker on Spyre LPAR (Step 6).
  4. Deploy our rootless OpenSearch + rag-backend + UI stack to Spyre LPAR once approvals are in place.
- Local tooling (not in repo): Selenium venv at `%TEMP%\bob\selvenv` (selenium, flask, bs4, requests, langchain-text-splitters, rank-bm25); recreate with `python -m venv` + `pip install` of those if the temp folder is cleared. SSH helper scripts were in `%TEMP%\bob\` (they read the password from an env var; password now in the user's 1Password, not here).
- Context-window self-check rule was disabled by the user (`~/.bob/rules/context-window-management.md.disabled`); rely on the UI meter.

## UPDATE 2026-11-26 - UI direction and LPAR state

- The outage hit before any UI work was saved. Verified on the LPAR as `david`: nothing of ours is deployed (no containers, images or listeners). The only UI activity found was `npm install` in `carbon-rag-ui` on 25 Nov 17:22.
- Techzone is still unavailable. Target is the persistent Spyre LPAR only (not OCP, not a repeatable recipe). The Techzone/OCP sections above are historical.
- Decision: replace the Next.js UI with one built on the Launchpad `chatbot-ui` template (Vite, React 19, `@carbon/ai-chat`). See [`UI_LAUNCHPAD_PLAN.md`](UI_LAUNCHPAD_PLAN.md) for the UI intent, template analysis, design and open decisions. No UI code written yet.
- Decisions agreed 2026-11-26: convert `/api/generate` responses client-side (not the stock chatbot-ui); chat first, read-only Sources page second; rebuild IN PLACE in `carbon-rag-ui/` (no new folder; no one else uses it); name "IBM Power Sales Manual Assistant"; sources = links back to the original IBM Sales Manual pages (URLs come from the corpus; the UI's hard-coded S1112 entry (`9028-21N`, `power-s1112-server`) was a mistake; the S1112 is `9242-21B`/`9242-21T`, and `9028-21B` is the S1012. The corpus is correct.)
- NEXT: scaffold the Vite/React 19/`@carbon/ai-chat` app in `carbon-rag-ui/` (see `UI_LAUNCHPAD_PLAN.md`). In parallel the user asks Andrew the short list in that file (ports, Granite endpoint, linger, quota) before anything is deployed to the LPAR.
- LLM decision (2026-11-26): use the shared Granite 4 on Spyre, already agreed with Andrew. Still to get from him: URL/model/auth, network route from our rootless containers (the Spyre containers publish no host ports), limits; and whether we may also use the box's `embedding-*` / `reranker-*` services.
- Andrew's answers 2026-11-26: Spyre Granite as client = YES (details in the Catalog UI service listing, no rate limits known); `enable-linger` = YES; `/home` quota/policy = NONE; ports = **8400 (UI) and 8401 (backend)**, any 84xx OK, IBM network/VPN only, verified free (firewalld is running; opening 8400 externally may need Andrew). LLM: use the Spyre "Digital Assistant" (`llm-1241b938ce`), NOT the CPU-only `al-assistant`; only its LLM, not its knowledge base. The user wants to use the reranker too (it runs on CPU vLLM, like the embedding service; only the `llm-*` containers use Spyre). See `UI_LAUNCHPAD_PLAN.md`. Still need from the user: LLM URL/model/auth/context from the Catalog UI.
- LLM VERIFIED 2026-11-26 (no need for the Catalog UI): Spyre Digital Assistant = `llm-1241b938ce`, `http://10.89.0.72:8000` (alias `llm-1241b938ce:8000`), model `ibm-granite/granite-4.1-8b-fp8`, context 32768, no API key, reachable from `david` without sudo. IPs are podman-assigned and may change; resolve at start. The 8096 instance is the CPU `al-assistant`. Firewall: no open ports; when the UI runs, `sudo firewall-cmd --permanent --add-port=8400/tcp` + reload (user agreed). Details in `UI_LAUNCHPAD_PLAN.md`.
- Uncommitted work from 25 Nov (rag-backend `app.py`, `table_lookup_service.py`, `chunk_tree.py`, `ibm_docs_tree.py`, `laptop-scraper/`) still needs committing and pushing.
- Local tooling: `paramiko` installed in `%TEMP%\bob\selvenv`; `sshrun.py` reads the password from env var `SPW` (set per command, never stored).

## UPDATE 2026-11-26 (evening) - UI built, backend routing fixed; nothing deployed yet

Supersedes "No UI code written yet", "NEXT: scaffold" and "Uncommitted work" in the section above. All of this is committed and pushed to `origin/main` (latest `e9b8e0e`).

**Done**
- `carbon-rag-ui/` rebuilt in place as the "IBM Power Sales Manual Assistant" (Vite, React 19, `@carbon/react`, `@carbon/ai-chat`). Chat converts `/api/generate` responses in the browser: clarification buttons, lifecycle table, features accordion, source tile linking to the IBM page, "Show context used". Verified in Chrome against a mock backend (`npm run mock`). `npm run lint`, `npm test` (7 tests) and `npm run build` pass. The legacy `watsonx_assistant` tag is hidden in the UI.
- Sources page (`#/sources`, read-only Carbon DataTable, filterable) and Chat | Sources header nav. Chat stays mounted, so the conversation survives switching tabs.
- Backend: `GET /api/sources` serves `rag-backend/sources.json` (27 families), which is generated from the corpus by `laptop-scraper/make_sources.py` (`--check` verifies it is current). Chunk counts come from OpenSearch, best-effort.
- Backend: query paths now use `rag_family_*` collections (what `/api/ingest-chunks` writes). `server_mtm_mapper.py` builds model/MTM/family maps from `sources.json`; S1112 is now correct (`9242-21B`/`9242-21T`, one family collection). `test_server_mtm_mapper.py` passes (4 tests). `list_collections` no longer has a hand-written MTM list.
- Backend `Dockerfile` now copies `sources.json`, `ibm_docs_tree.py`, `chunk_tree.py` (the last two were missing for `/ingest-scraped-content`).
- The old Next.js UI, the `harry-potter-rag` page and the old API proxy routes are gone from the working tree; they remain in git history before commit `4948f99`.

**Update from the user (end of session):** the watsonx Assistant instance still exists, but an API key for it was deleted, so Watson would need a new key (`WATSON_ASSISTANT_API_KEY/URL/ID`; never write the key into the repo). The user has a concern about that deleted key and wants to pick this up in the next session, together with the decision below.

**Open decision (ask the user first)** - how the backend identifies the server in a question. `query_classifier.get_query_intent` only extracts server/MTM/lifecycle field through Watson Assistant (cloud, optional, never configured on the LPAR). Without it the classifier returns no entities and always asks "which server?", even for "When is the E980 withdrawn?". Options: (a) local extractor driven by `sources.json` plus keywords (recommended; no cloud dependency), (b) configure Watson (`WATSON_ASSISTANT_API_KEY/URL/ID`, needs outbound internet), (c) use the Spyre Granite LLM to extract JSON, validated against `sources.json`, (d) defer. Until this is solved, end-to-end questions on the LPAR will mostly come back as clarification prompts.

**Next steps (in order)**
1. Get the decision above and implement it in `query_classifier.py` (test with the real wording: "When is the E980 withdrawn?", "S1112 lifecycle", "activation features for the S1022").
2. Packaging: `carbon-rag-ui/Containerfile` + `nginx.conf.tmpl` (build static assets on the laptop, copy into multi-arch `ubi9/nginx-126`; no npm on the LPAR). nginx on 8400 serves the UI and proxies `/api/` and `/health` to the backend on 8401. Update `podman/deploy.sh` and `podman/manage.sh`: they still build `carbon-rag-ui` from the deleted Next.js Dockerfile and expect it on :3000. The OCP scripts (`deploy-ui.sh`, `deploy-ocp.sh`, `deploy-fresh-cluster.sh`) also still reference the old UI; they are not usable now (no Techzone), leave or archive.
3. LPAR (as `david`, rootless podman; see `UI_LAUNCHPAD_PLAN.md` for the verified LLM endpoint, ports and safety rules): find the reranker's real port/API; set `LLM_BASE_URL` (resolve with `sudo podman inspect llm-1241b938ce-llm`; the 10.89.x.x address can change); deploy OpenSearch (`icr.io/ppc64le-oss/opensearch-ppc64le:3.3.0`), rag-backend and the UI; `loginctl enable-linger david`; `sudo firewall-cmd --permanent --add-port=8400/tcp` + reload; ingest the corpus with `laptop-scraper/ingest_corpus_to_backend.py`. Touch nothing of Andrew's or Angela's.
4. Legacy: the bulk-ingestion server list in `app.py` (`start_bulk_ingestion`) still has the wrong S1112 (`9028-21N`, `power-s1112-server`). It is the old Code Engine scraper path, so fix or remove it rather than use it.
5. Ask the user whether to keep the committed `laptop-scraper/corpus/*.html.gz` (4.5 MB of IBM page content) if the GitHub repo is public.

**Starting a new task** - paste: "Continue the IBM Power Sales Manual Assistant work. Read `Part3-RAG-Sales-Manual/CHECKPOINT_OLLAMA_RHEL.md` (section 'UPDATE 2026-11-26 (evening)') and `UI_LAUNCHPAD_PLAN.md`. Chat UI, Sources page and family routing are done and pushed. First ask me the open decision about how the backend identifies the server in a question, then packaging and the LPAR deployment." The LPAR password is not stored anywhere; ask for it when needed (env var `SPW` for `%TEMP%\bob\sshrun.py`, venv `%TEMP%\bob\selvenv`).


## UPDATE 2026-11-26 (late) - watsonx Assistant retired; LLM intent extraction added

- **Watson is gone for good.** The assistant the backend used was lost when its API key/instance was cleaned up in the IBM Cloud account. The replacement key (service "IBM Power Seller Demos by David") belongs to a different, Plus Trial instance in a frozen account: valid key, but no usable assistant. Decision: do not rebuild it; do not move to Orchestrate for this (cloud dependency, same failure mode). The Watson code stays as an optional legacy path.
- **New `rag-backend/intent_extractor.py`** (wired into `QueryClassifier.get_query_intent`): (1) exact server model / MTM tokens from `sources.json` (`S924` vs `S924-G`, `LC922` vs `L922`, `9242-21T`); (2) optional LLM (OpenAI-compatible `/v1/chat/completions`, enabled by `LLM_BASE_URL`, model `LLM_MODEL` default `ibm-granite/granite-4.1-8b-fp8`) returns JSON for server / query type / lifecycle field, validated against `sources.json`. An exact server token in the question beats the LLM; a clear lifecycle question ("When is the E980 withdrawn?") skips the LLM; any LLM failure falls back to the deterministic result. Allowed query types from the LLM: `table_lookup`, `activation_lookup`, `rag`.
- Tests: `rag-backend/test_intent_extractor.py` (LLM mocked) + `test_server_mtm_mapper.py`, 19 pass. NOT yet tested against the real Spyre Granite (needs the LPAR).
- `LLM_BASE_URL`/`LLM_MODEL` added to `Dockerfile` (module copied), `podman/podman-compose.yml`, `podman/env.example`, `restart_backend.sh` (now reads `.env`, gitignored).
- **Secrets:** the dead Watson key and instance/assistant IDs were scrubbed from the working tree (5 docs, `test_watson_assistant.py` now reads env vars, `restart_backend.sh`). They are STILL IN GIT HISTORY (commits `70c9859`, `3d94b9a`, pushed to `DSpurway/IBM-Power-RAG-Demos`). The key is deleted so it cannot be used; rewriting history is the user's decision. The replacement key was pasted in chat: delete it in IBM Cloud if the instance is not wanted.
- Still hard-coded in `app.py` responses: `ai_services_used: ['watsonx_assistant']` and `processing_method: 'nlp_intent_detection'`. The UI hides the tag; change to the intent `source` when convenient.
- **Next:** (1) user to confirm the commit; (2) on the LPAR set `LLM_BASE_URL` (resolve `llm-1241b938ce` IP) and try real wording ("When did we stop supporting the S924?", "S1112 lifecycle", "activation features for the S1022"); check latency of the extraction call; (3) then packaging and LPAR deployment as in the previous section.

### Follow-up (same day): stricter shortcut + A/G clarification
- LLM is skipped only when: exact server token + lifecycle regex hit + exactly ONE kind of date keyword (`QueryClassifier.LIFECYCLE_KEYWORDS`, `_single_lifecycle_field`). Two dates, typos or other wording go to the LLM; with no LLM and two dates the user is asked which date.
- Bare "S924" (also S922, S914) now asks A or G (`intent_extractor.variant_options`, `app.py` generic `mtm_clarification_needed` block, any question type). "S924-G", "S924 G" or an MTM does not ask. S1112 (two MTMs, one model) does not ask: the table lookup lists both.
- Clarifications used to lose earlier choices (UI re-sends the original question with ONE param), which would loop A/G -> date -> A/G. Backend now returns `resolved` with each clarification; UI (`responseMapper.js`, `ChatBlocks.jsx`, `customSendMessage.jsx`) re-sends them with the next choice. UI needs a rebuild/redeploy for this.
- Tests: 25 backend (`python -m unittest test_intent_extractor test_server_mtm_mapper`), 8 UI (`node --test src/responseMapper.test.js`).


## UPDATE 2026-11-27 - DEPLOYED on the Spyre LPAR (UI + backend + OpenSearch, Watson-free)

**Live:** `http://spyre.aixncc.uk.ibm.com:8400/` (IBM network). Backend is `127.0.0.1:8401` on the LPAR only; OpenSearch has no published port. Verified in Chrome: suggested prompt "When is the IBM Power E980 withdrawn from marketing?" returns the lifecycle list via "Direct table lookup (no LLM)".

**What runs (rootless podman as `david`, all prefixed `sa-`, network `sales-assistant-net`)**
- `sa-opensearch` (`icr.io/ppc64le-oss/opensearch-ppc64le:3.3.0`, 2 GB heap, volume `sa-opensearch-data`), `sa-rag-backend` (`localhost/sa-rag-backend`, built on the LPAR, HF cache volume `sa-hf-cache`), `sa-ui` (`localhost/sa-ui`, nginx serving the Vite build, proxies `/api/` + `/health`). `--restart always`; `loginctl enable-linger david` done; `podman-restart.service` enabled; firewall port 8400/tcp open.
- All 27 families ingested from the laptop through `:8400` (`laptop-scraper/ingest_corpus_to_backend.py --backend-url http://spyre.aixncc.uk.ibm.com:8400 --all`, run with the selenium venv; about 10 min).
- Everything is driven by `podman/deploy-lpar.sh` (`preflight|build [be|ui]|up|status|logs|down`) staged in `~/sales-assistant/` with `rag-backend/` and `carbon-rag-ui/` (Containerfile, nginx.conf.tmpl, `build/`). `LLM_BASE_URL` is resolved from `sudo podman inspect llm-1241b938ce-llm` on each `up` (currently `http://10.89.0.72:8000`); override in `~/sales-assistant/.env`.
- Laptop helpers live in the git-ignored `Part3-RAG-Sales-Manual/.lpar/` (`lpar.py`: `run|script|put` over SSH, password only via env var `SPW`; uses system python/paramiko). Redeploy loop: edit, `put` changed files to `~/sales-assistant/...`, run `deploy-lpar.sh build be && deploy-lpar.sh up` (the pip layer is cached, about 1 min). A UI change needs `npm run build`, then upload `build/` + rebuild `ui`.

**Code changes made for the LPAR (all in this commit)**
- `/api/generate`, the feature-code answer, activation descriptions and `/health` now use `LLM_BASE_URL`/`LLM_MODEL` (OpenAI-compatible) when set. Before this they only knew llama.cpp/Ollama, so the LPAR would have had no LLM for answers. Default model param is `openai` when `LLM_BASE_URL` is set.
- `table_lookup_service._generate_index_name` now hashes like `app.py` (`rag_<md5(collection)>`). It used the plain name, missed the index, and fell back to `rag_*` over all indices; this only looked fine with one family loaded.
- `intent_extractor` prompt: `activation_lookup` only for "activation"/Capacity on Demand; "maximum memory" etc. go to `rag`.
- Backend `Dockerfile`: apt over https (plain http to deb.debian.org fails from rootless containers here) and `sentence-transformers<6` (6.x needs transformers 5; the image has 4.57).
- UI image uses `docker.io/library/nginx:stable`: the LPAR's `/etc/containers/policy.json` only allows `docker.io/library`, `icr.io`, `quay.io/podman`, `registry.redhat.io` (so `registry.access.redhat.com/ubi9/nginx-126` is rejected). Do not edit that policy; it is Andrew's.

**Measured**
- Lifecycle answers: about 0.2 s (table lookup, no LLM). Clarifications (S924, S1112): about 3.5 s (intent LLM call). Activation lists: 4 s. RAG answers: 25-35 s, almost all LLM decode: a direct call to the shared Spyre Granite gives about 8 tokens/s (155 tokens in 19 s). Streaming the answer in the UI would help perceived latency.
- `vm.max_map_count` is 65530 on the LPAR (OpenSearch wants 262144); it runs fine with `discovery.type=single-node`. Raise it only if OpenSearch complains (system-wide, needs sudo).

**Open issues / next steps (in order)**
1. **RAG retrieval quality** (biggest remaining problem): "What is the maximum memory of the E980?" and "Which operating systems does the S1022 support?" get "context does not contain..." because hybrid search + rerank (local `cross-encoder/ms-marco-MiniLM-L-6-v2`, top-3 scores often negative) does not surface the right chunk. Dimensions/weight works. Look at the chunks returned for these, query rewrite (strip server name), top_k, and the section-aware chunks; consider the Launchpad reranker (port/API still unknown).
2. Streaming of RAG answers to the UI; or lower `n_predict`.
3. Still hard-coded `ai_services_used: ['watsonx_assistant']` / `processing_method: 'nlp_intent_detection'` in `app.py` (UI hides the tag).
4. `podman/deploy.sh` / `manage.sh` / OCP scripts still reference the old Next.js UI (not used now).
5. Ask the user: push to GitHub (commit is local until confirmed), keep `laptop-scraper/corpus/*.html.gz`, and whether to delete the replacement Watson key in IBM Cloud. Repo history still contains the dead Watson key (see section above).
6. `git` line endings: `deploy-lpar.sh` must be LF on the LPAR; the upload step runs `sed -i 's/\r$//'`.

**Starting a new task** - paste: "Continue the IBM Power Sales Manual Assistant work. Read `Part3-RAG-Sales-Manual/CHECKPOINT_OLLAMA_RHEL.md` (section 'UPDATE 2026-11-27'). The stack is deployed on the Spyre LPAR at http://spyre.aixncc.uk.ibm.com:8400/. Next: improve RAG retrieval quality for specification questions (maximum memory, operating systems), then streaming." Ask me for the LPAR password; use env var `SPW` with `.lpar/lpar.py`.


## UPDATE 2026-11-27 (later) - RAG retrieval investigation; fix WRITTEN, NOT yet tested or deployed

**Root causes found (measured on the LPAR with `.lpar/eval.py`, 6 questions with known-right chunks)**
1. The RAG candidate pool was tiny: `k=3`, so 6 hybrid hits were reranked down to 3. The right chunk was often not in the 6.
2. About 92% of a family's chunks are `feature_code` chunks (E980: 1263 of 1372). They crowd out narrative `content_section` chunks (Abstract, Highlights, Operating environment, Software requirements).
3. Question wording vs manual wording: "power" matches the product name everywhere (BM25 noise), "OS" is not "software requirements", etc. A keyword rewrite of the question fixes this.
Scores (right chunk reached the LLM): current 2/6; pool of 30 3/6; union of pools + rerank on the question 4/6; same but rerank on the rewrite 5/6; top-3 of each wording merged 6/6. Ground truth used: E980 "up to 64 TB memory" (Abstract / System nodes / Highlights), "Operating environment" (4,130 watts, 4.2 kVA), "Physical specifications", S1022 two "Technical description > Software requirements" chunks (AIX/VIOS and Linux/IBM i), E980 "192 POWER9", "32 CDIMM slots". Timing: pool build 0.5 s + rerank about 2.5 s per wording (CPU).

**Code written (UNCOMMITTED, NOT yet run or deployed)**
- `rag-backend/intent_extractor.py`: LLM prompt now also returns `search_query` (4-12 manual keywords, no server name; "electrical power consumption watts kVA operating environment" when "power" means electrical); `validate_llm_result` returns it (cleaned, None if missing/too short); `max_tokens` 150 -> 200.
- `rag-backend/query_classifier.py`: `get_query_intent` passes `search_query` through (None without LLM).
- `rag-backend/app.py`: new `_rag_candidates()` (per query: hybrid over all chunks `RAG_POOL_K`=30 plus hybrid restricted to `metadata.section_type.keyword = content_section` `RAG_CONTENT_K`=20, merged by id); RAG path searches the stripped question + the rewrite, then reranks the pool against the question AND the rewrite, keeps `RAG_TOP_K`=3 from each, merged (at most 6 chunks) into the LLM context. Dense kNN fallback only if no candidates. The old hybrid/dense try/except block was replaced.
- `rag-backend/test_intent_extractor.py`: new test `test_search_query_is_cleaned_and_optional` (inserted at line 57; needs a blank line before the `def` for style).

**Next steps (in order)**
1. Run `python -m py_compile app.py query_classifier.py intent_extractor.py` and `python -m unittest test_intent_extractor test_server_mtm_mapper test_lifecycle_support_level` in `rag-backend/` (the last command was cancelled before it ran). Fix anything it shows.
2. Deploy: `.lpar/lpar.py put` the 4 changed files to `/home/david/sales-assistant/rag-backend/`, then run `.lpar/rebuild-up.sh` (about 1 min). Password via env var `SPW`.
3. Test with `python .lpar/ask.py` and check the backend log lines "RAG search rewrite", "RAG candidate pool", "Reranked to N chunks". Questions: max memory (E980), power use (E980), S1022 operating systems, cores, dimensions. CHECK that the real Granite produces a good `search_query` (the eval used hand-written rewrites). If it is poor, tune the prompt in `intent_extractor._build_messages`. Latency should rise by about 5 s (two reranks); drop `RAG_POOL_K` if too slow.
4. Then: commit (the user said GitHub sync is NOT important for this work, so a local commit is enough), and consider streaming answers to the UI (LLM decode is about 8 tok/s).
5. Eval harness: `.lpar/eval.py` (+ `eval.sh`, `diag.py`, `disc.py`; git-ignored). Upload with `lpar.py put`, run with `lpar.py script .lpar/eval.sh`. It writes results to `/tmp/eval.out` inside the backend container.

**Starting a new task** - paste: "Continue the IBM Power Sales Manual Assistant work. Read `Part3-RAG-Sales-Manual/CHECKPOINT_OLLAMA_RHEL.md`, section 'UPDATE 2026-11-27 (later)'. The RAG retrieval fix is written but untested and undeployed: run the tests, deploy to the LPAR, and verify with real questions." The LPAR password is not stored; ask me for it (env var `SPW`, helper `.lpar/lpar.py`).



## UPDATE 2026-11-27 (evening) - retrieval scope in the classifier; tested locally, NOT deployed

- Idea: feature-code chunks (~92% of an index) crowd out narrative chunks, so the classifier now decides which kind a RAG question should favour.
- `query_classifier.QueryClassifier.retrieval_scope()` -> `intent['retrieval_scope']`: `feature` (a code like `#EFP1` / "feature code 0010", "feature codes", FC, CCIN, part number), `mixed` (feature/option/order/adapter/card/DIMM/cable/drive wording; "features" alone can mean highlights), `general` (everything else: max memory, operating systems, power, dimensions).
- `app.py` `_scope_pool_sizes()`: general = all-chunks pool 8 + narrative pool 30; feature = 30 + 5; mixed = 30 + 20 (env `RAG_POOL_K` / `RAG_CONTENT_K` are the base). The log line "RAG candidate pool ... scope=" shows what was used. The exact-code direct lookup is unchanged.
- Tests: 30 pass (`python -m unittest test_intent_extractor test_server_mtm_mapper test_lifecycle_support_level` in `rag-backend/`), includes the new `RetrievalScopeTest`.
- Still to do: the LPAR deploy and real-question check from the previous section (this change and the earlier `_rag_candidates` / `search_query` work are both undeployed). Then check that feature questions ("What PCIe adapters can I order for the S1022?", "What is feature code #EFP1?") still answer as well as before.

### Deployed and measured (2026-11-27, evening)
- Deployed to the LPAR (app.py, query_classifier.py, intent_extractor.py; `.lpar/rebuild-up.sh`). The real Granite writes good `search_query` rewrites (e.g. "supported operating systems software requirements") and the scope shows in the log line "RAG candidate pool ... scope=".
- Production-path eval `.lpar/eval2.py` / `eval2.sh` (real intent -> `_rag_candidates` -> rerank): 5/6 with scope only; the miss was S1022 operating systems (the two "Software requirements" chunks were in the pool but the MiniLM reranker put them 18th and 23rd).
- Fix: `_title_matches()` in `app.py` adds up to 2 narrative chunks whose heading shares >= 2 words with the rewrite (log: "Added heading match"). Now 6/6, and the live S1022 OS answer lists the Linux/AIX versions from Software requirements. Feature questions (`#EPPK`, "which feature codes are memory DIMMs") still answer from feature chunks.
- Live answers are 25-40 s (LLM decode), unchanged. Streaming is still the next idea for perceived latency.
- Everything here is UNCOMMITTED (local only). The LPAR password was given in chat for this session and is not stored anywhere.


## UPDATE 2026-11-27 (late) - OS-level questions: chunker fix, section hint, software_levels (DEPLOYED)

**Problem:** "What level of AIX is needed / minimum for the E980?" gave wrong, inconsistent answers.

**Causes and fixes**
- Chunker split a lead-in line ("If installing the AIX operating system LPAR with any I/O configuration (one of these):") from its list. Fixed in both `rag-backend/chunk_tree.py` and `laptop-scraper/chunk_tree.py` (v2.1.0; the laptop one is what ingestion actually uses).
- Chunk ids are positional, so re-chunking left stale chunks. `/api/ingest-chunks` now takes `replace` (delete index first); `ingest_corpus_to_backend.py` sends it. All 27 families re-ingested (~8 min; each index is empty ~20 s during replace).
- `query_classifier.section_hint()` returns `{'section': 'Software requirements', ...}` for level-type words plus AIX/IBM i/Linux/VIOS/"operating system". `app.py` `_section_chunks()` puts those chunks first and drops feature-code chunks.
- `SOFTWARE_LEVEL_NOTE` added to the prompt (TL/SP/TR notation, "(one of these)" = alternatives, flag inconsistent levels).
- New `rag-backend/software_levels.py` (`oldest_levels`): works out the oldest AIX/IBM i level per list for "minimum" questions, because Granite picks the wrong one. Dockerfile copies it.
- Tests: 39 pass (`python -m unittest test_intent_extractor test_server_mtm_mapper test_lifecycle_support_level test_chunk_tree test_software_levels` in `rag-backend/`).
- Mojibake incident: PowerShell 5.1 `Get-Content -Raw` + write double-encoded `app.py` (shipped in `d7b279c`). Repaired. Never edit source that way; use apply_diff or Python with `encoding='utf-8'`.

**Live results after final deploy**
- Retrieval is right for both AIX questions (the three Software requirements chunks, no NVMe feature chunks).
- "Minimum level of AIX ... E980": now 6.1 6100-09 (service extension). Correct oldest level, but attributed to the Virtual I/O only list; the any-I/O list should also be given.
- "What level of AIX is needed ... E980": STILL WRONG. Granite ignores the note and answers "AIX 7.2 TL4". Should list each supported release (7.3 TL0, 7.2 TL4 ...) newest first.

**Next steps**
1. For "needed" questions, precompute a supported-release table in `software_levels.py` (like `oldest_levels`, one lowest TL per release per list) and put it in the context, rather than relying on the model.
2. Say which list (any I/O vs Virtual I/O only) each computed level comes from.
3. Check IBM i / Linux / VIOS variants; re-run `.lpar/eval2.sh` for regression.
4. The manual has an inconsistent line ("AIX 6.1 with 6100-09 TL and Service Pack 7100-09-07-1614"); consider a data-quality note.
5. Optional: stream answers to the UI (~8 tok/s, 25-45 s per answer).
## UPDATE 2026-11-27 (night) - "what level is needed" answered from a computed table (DEPLOYED, committed 84be0b0)

- software_levels.supported_releases() gives the lowest listed level per release, newest first, one line per list ("Any I/O" / "Virtual I/O only"). app.py puts it in the context for non-"minimum" level questions and tells Granite to present every line (it states the line count).
- Live check: E980 "What level of AIX is needed" now lists 7.3, 7.2, 7.1, 6.1 for BOTH lists; S1022 IBM i lists 7.6 down to 7.3 (one list in the manual). eval2 retrieval regression: 6/6.
- Known: the manual's inconsistent line (AIX 6.1 with "Service Pack 7100-09-07-1614") is quoted as printed and Granite does not flag it. Linux questions have no computed table (answered from the Software requirements chunk, looked right). "Needed" answers take 40-60 s.
- Next: optional data-quality note for the inconsistent line; stream answers to the UI; IBM i/VIOS variants on other servers; the leftover legacy items in the previous sections. The LPAR password is not stored (env var SPW).

## UPDATE 2026-11-27 (night 2) - daily Sales Manual change check (DEPLOYED, timer installed)

- **How it works:** the backend asks the Code Engine scraper (/scrape, returns rendered HTML) for each of the 27 pages in sources.json, parses and chunks them with the same code as the first load, and compares `content_hash` (SHA-256 of the page text, stored in the chunk metadata) and `chunker_version` with what is indexed. Same = skip. Different = re-index that family. A scrape with under half the stored chunk count is reported `suspicious` and NOT indexed (broken page protection); `force` overrides. Code: `rag-backend/manual_refresh.py` (+ `test_manual_refresh.py`), endpoints `POST /api/refresh-manuals` (body optional: `{"force":true}`, `{"family":"9080-03"}`) and `GET /api/refresh-manuals/status`.
- **Verified:** Code Engine HTML gives byte-identical chunks and hash to the laptop corpus. A full run over all 27 families: 27 unchanged (about 10 min, 20-30 s per page, mostly Code Engine). Forced E980 run: swap path OK.
- **Trigger:** the scraper cannot call the LPAR (IBM network only), so a user systemd timer on the LPAR does: `~/sales-assistant/deploy-lpar.sh refresh install|remove|status|run` (daily 03:30 + up to 15 min random; `Persistent=true`). Installed; next run 28 Nov ~03:42. `SCRAPER_URL` is now passed to the backend container by `deploy-lpar.sh`. Results are in memory only (lost on backend restart; the log has them: `grep Refresh`).
- **Bugs found and fixed on the way (important):**
  1. The S1112 (9242-01) index was EMPTY. It has two MTMs; OpenSearch date detection read `9242-21B` as a date and rejected `9242-21T`. `/api/ingest-chunks` still answered `success` with 0 indexed, so the first load never showed it. `_setup_index` now maps `mtm`/`mtms`/`family` explicitly as text+keyword (only new indexes; the other 26 still have `family` as a date, harmless). S1112 now has 451 chunks.
  2. `/api/ingest-chunks` now returns HTTP 500 when 0 chunks were indexed.
  3. `replace` used to delete the index first. Now `_index_chunks()` (extracted from `ingest_chunks`) writes `<index>_new` and only swaps (delete, recreate, reindex) when everything was indexed; otherwise the old index is kept.
- **Not covered:** a NEW manual (not in `sources.json`) or a withdrawn page is not detected; `sources.json` is still generated from the laptop corpus (`make_sources.py`). A 404/403 page is reported `failed` per family, no alert is sent. The old `/api/start-bulk-ingestion` path (hard-coded list, wrong S1112) is still there, unused.
- **Observed, not fixed:** "When was the S1112 announced?" answers for 9242-21B only; 9242-21T is not shown.
