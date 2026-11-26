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
