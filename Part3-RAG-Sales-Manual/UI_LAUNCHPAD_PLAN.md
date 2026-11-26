# Sales Manual UI on the Launchpad template - intent and plan

> Status (2026-11-26 evening): chat UI and Sources page are BUILT and pushed (see the latest section of `CHECKPOINT_OLLAMA_RHEL.md`). Not yet packaged or deployed to the LPAR. The sections below are the original plan and decisions; they still hold. Target is the persistent Spyre LPAR (see `SPYRE_LPAR_PLAN.md`), a long-lived tool, not a repeatable recipe. Techzone is unavailable.
>
> Product name: **IBM Power Sales Manual Assistant** (not "DigitalAssistant"). Built in place in `carbon-rag-ui/` (no one else uses it; no need to keep a parallel copy). Keep the design open to other documentation sets later.

## Intent and purpose of the UI we built (`carbon-rag-ui`)

A pre-sales / support tool for IBM Power: ask a natural-language question about the IBM Power Sales Manuals and get a grounded, verifiable answer with a link back to the IBM source.

What it does today (`src/app/sales-manual/page.js`, three tabs):

| Tab | Purpose | Backend |
|---|---|---|
| Query Documentation | The core. Free-text question -> answer. | `POST /api/generate` (`collection_name`, `prompt`, `top_k`, optional `server_mtm` / `server_model` / `lifecycle_field`) |
| Manage Source Documents | Table of the 27 servers: MTM, processor, category, status, doc count, last updated, content hash. Single and bulk ingest. | `/api/collections`, `/api/ingest-sales-manual`, `/api/bulk-ingestion-status`, `/api/start-bulk-ingestion` |
| IBM Power Announcements | Scan and ingest announcements, show lifecycle deltas. | `/api/announcements/scan`, `/api/announcements/ingest` |

Behaviours the new UI MUST keep (these are what make it more than a generic chatbot):

1. **Clarification loop.** If the question is ambiguous the backend returns `clarification_options` (`[{value,label}]`) and a `query_type` of `mtm_clarification_needed`, `server_clarification_needed` or `lifecycle_clarification_needed`. The UI re-submits the same prompt with `server_mtm`, `server_model` or `lifecycle_field` set.
2. **Different answer shapes by `query_type`.**
   - Lifecycle questions are answered from the structured table with no LLM (`processing_method: hybrid_table_lookup`), plus `table_data`.
   - Feature and activation questions return `features` (rendered by `FeaturesView`) plus `server_model`.
   - Everything else is `full_rag_generation`: `content`/`answer` plus `chunks_used` (`text`, `score`, `metadata.section`).
3. **Provenance.** `source_url` / `source_filename` link to the original IBM Sales Manual page. This is the trust feature; keep it prominent.
4. **Transparency.** `ai_services_used` (watsonx Assistant, OpenSearch, LLM) and `processing_method` tags, `response_time_ms`, and the "AI generated" label.
5. **Admin/ingest visibility** (server table, doc counts, hash, last updated). On the LPAR, ingest comes from the laptop corpus via `/api/ingest-chunks`, so the scrape and bulk-scrape buttons go; the status table stays.

## The Launchpad template (what "professional" means here)

Source: `IBM/project-ai-services`, `ui/chatbot` (Apache-2.0). The LPAR runs it as `chatbot-ui:v0.0.55`. About 25 files:

- Stack: Vite + React 19 + `@carbon/react` ^1.118 + **`@carbon/ai-chat`** (`ChatCustomElement`), `openai` client, small Express proxy, SCSS. Dark `GlobalTheme g100`, white content, g90 header ("DigitalAssistant"), square corners, "new chat" action.
- Chat plumbing: `customSendMessage.jsx` streams from `/v1/chat/completions` into `addMessageChunk`; `renderUserDefinedResponse.jsx` renders custom blocks (their only one is `ReferenceDocsButton`, a "Get reference documents" tile list); `/db-status` gates "ingest documents first"; `/v1/models` probes whether an API key is needed.
- Deploy: `Containerfile` = UBI9 node build, then `ubi9/nginx-126` serving `build/` on :3000, `nginx.conf.tmpl` rendered with `BACKEND_HOST` / `BACKEND_PORT`. nginx only proxies `/v1/chat/completions`, `/v1/models`, `/db-status`.

Gap vs ours: our UI is Next 13.4.9 / React 18 / `@carbon/react` 1.33, page-and-tabs, no chat component, no streaming. Different framework, so this is a rebuild on the template's stack, not a restyle. Our `src/app/*` and Next API routes are not carried over; `FeaturesView` and the clarification/lifecycle logic are ported as `user_defined` chat blocks.

## Proposed design

**Keep the rag-backend contract; adapt on the client.** Reasons: the backend already encodes the clarification/lifecycle/feature behaviour; an OpenAI-style adapter would flatten exactly the rich answers that make this useful. This is the checkpoint's "Option 1".

1. Rebuild `carbon-rag-ui/` IN PLACE on the Launchpad `ui/chatbot` layout (same versions, header, theming, nginx/Containerfile pattern). The Next.js app is replaced; git history keeps the old version. Header reads "IBM Power Sales Manual Assistant".
2. `customSendMessage` calls `POST /api/generate` (non-streaming JSON) and maps the response:
   - `content`/`answer` -> `text` item (pre-escaped/sanitised; the old UI used `dangerouslySetInnerHTML`, do not carry that over).
   - `clarification_options` -> Carbon AI Chat `option` response (buttons); a click re-sends with `server_mtm` / `server_model` / `lifecycle_field` chosen by `query_type`.
   - `table_data` -> `user_defined` lifecycle-table block.
   - `features` -> `user_defined` block wrapping the ported `FeaturesView`.
   - `chunks_used` + `source_url` -> `user_defined` "Reference documents" block (same pattern as `ReferenceDocsButton`) with section, score and the IBM source link.
   - `ai_services_used` / `processing_method` / `response_time_ms` -> small tag row under the answer.
3. **Sources = links back to the original IBM Sales Manual pages.** Every answer carries its source link(s) (`source_url`, per-chunk `metadata.source`). A read-only "Sources" page (Carbon DataTable) lists every manual we hold: server, MTM(s), family, link to the IBM page, doc count, last updated, content hash. The URLs are stable, so we link to them rather than storing or re-hosting content. Ingest/scrape controls are not part of v1; announcements view later.
   - Single source of truth for the URL mapping: the corpus (`laptop-scraper/corpus/<family>.json` has `url` and `mtms` per family page). The UI should get the list from the backend (collections/metadata) and not keep its own hard-coded `IBM_POWER_SERVERS` array.
   - Checked 2026-11-26: 26 of 27 UI URLs equal the corpus URLs. The one difference is **S1112**: UI has `power-s1112-server` with MTM `9028-21N`; the corpus has `family-9242-01-power-s1112` with MTMs `9242-21B` and `9242-21T`. The corpus is right and the UI entry was a mistake (confirmed by the user 2026-11-26): `9028-21N` does not exist, and `9028-21B` is the S1012, the S1112's POWER10 precursor, which is already its own correct entry (corpus `9028-01`). The S1112 is MTMs `9242-21B` / `9242-21T`.
   - The corpus is keyed by family (e.g. `9242-01`), and a family can cover several MTMs, so "Sources" rows are per family page with all its MTMs listed.
   - Later documentation sets (e.g. other IBM docs) fit as additional source types with the same link-back behaviour.
4. Packaging for the LPAR: build `build/` on the laptop (x86, Vite), then a Containerfile that only copies static files into the multi-arch `ubi9/nginx-126` image (no npm on the LPAR, per the "no rebuilds on this box" principle). nginx proxies `/api/` to rag-backend on localhost. Rootless podman as `david`, one agreed port.
5. Auth/CORS: single user-facing port; nginx same-origin proxy means no CORS config and rag-backend stays bound to localhost.

## Decisions (agreed 2026-11-26)

1. Convert on the client, keep `/api/generate`; do NOT reuse the stock Launchpad `chatbot-ui` as-is (it cannot carry clarification, lifecycle or feature cards, and our own UI leaves room for other documentation sets).
2. Chat first; read-only Sources page second.
3. In place in `carbon-rag-ui/`.
4. Name: IBM Power Sales Manual Assistant.
5. Still needs Andrew (informal check is enough): see below.

## Andrew's answers (2026-11-26, via the user) - supersede the questions below

| # | Question | Answer |
|---|---|---|
| 1 | Two free ports; reachable from where? | **8400 and 8401** (and anything in the 84xx range). IBM network / VPN only. Verified free 2026-11-26: nothing listens on 84xx. Plan: 8400 = UI (nginx, also proxies `/api/` to the backend), 8401 = backend, bound to localhost unless needed externally. Note `firewalld` is running; opening 8400 to the network may need Andrew (root). |
| 2 | Use the Spyre Granite as a client | YES. Details (URL, model name, auth) are in the service listing in the Catalog UI (port 9191). No rate limits that he knows of. |
| 3 | `loginctl enable-linger david` | YES. "Feel free to linger on the system and run your services long term." |
| 4 | `/home` quota / long-running-service policy | NO policy or quota. |

Which LLM (Andrew, 12:13 PM): two "Digital Assistant" deployments exist. `al-assistant` is CPU only. **"Digital Assistant" uses Spyre for Digitize and Q&A and is the faster one: use that.** The user also said: sudo to root is fine for what we need, including opening the agreed port.

Reranker: the user wants to use it. On this box both `embedding-*` and `reranker-*` run `icr.io/ppc64le-oss/vllm-ppc64le:0.28.0`, i.e. CPU (not `vllm-spyre`); only the `llm-*` containers use `vllm-spyre-rhel9`. So the embedding service is CPU too, as the user thought. The reranker is worth using for retrieval quality. Using the box's embedding service would add no speed and force re-embedding, so keep our own embeddings for now.

We use only the Digital Assistant's LLM, not its knowledge base (which holds whatever the Nordics demos loaded), so we neither affect nor depend on those documents.

## LLM endpoint (verified 2026-11-26, read-only: sudo inspect + GET /v1/models as `david`)

| | Spyre "Digital Assistant" (USE THIS) | 2nd Spyre LLM | CPU `al-assistant` |
|---|---|---|---|
| Container | `llm-1241b938ce-llm` | `llm-854167af0d-llm` | `llm-c77888ac44-llm` |
| Image | `vllm-spyre-rhel9:3.5.0` | same | `vllm-ppc64le:0.28.0` |
| Model id | `ibm-granite/granite-4.1-8b-fp8` | same | `ibm-granite/granite-4.1-8b` |
| `max_model_len` | **32768** | 32768 | 8096 |
| Alias / IP:port | `llm-1241b938ce:8000` / `10.89.0.72:8000` | `10.89.0.83:8000` | `10.89.0.89:8000` |

- Earlier guess corrected: the 8096-context instance is the CPU `al-assistant`, not `llm-854167af0d`. Both Spyre LLMs are 32768.
- The Digital Assistant chat backend uses `LLM_ENDPOINT=http://llm-1241b938ce:8000`, `LLM_MODEL=ibm-granite/granite-4.1-8b-fp8`, `LLM_MAX_MODEL_LEN=32768`. OpenAI-compatible (`/v1/models`, `/v1/chat/completions`).
- **No API key**: no key/token/password variables in that backend's environment, and `/v1/models` returns HTTP 200 with no auth header.
- **Reachable from `david` without sudo**: `curl http://10.89.0.72:8000/v1/models` -> 200 in about 2 ms (route via `podman1`; `10.89.0.0/24` is a trusted firewalld source). A rootless container of ours should be able to use it (to be proven when we run one).
- Caveat: `10.89.x.x` belongs to root's `podman-default-kube-network`, addresses are assigned by podman and may change if those pods restart. Our rootless containers cannot resolve the alias. Keep the LLM base URL a single setting (`LLM_BASE_URL`) and, at stack start, resolve the current IP with `sudo podman inspect llm-1241b938ce-llm`, or ask Andrew for a stable route.
- Launchpad's RAG settings for reference: embeddings `ibm-granite/granite-embedding-278m-multilingual` at `embedding-8228b3940e:8001` (max 512), `CHATBOT_RERANK=true`, `CHATBOT_NUM_CHUNKS_POST_RERANKER=3`. The reranker gave no `/v1/models` response on port 8000, so find its real port/route before wiring it in.
- Firewall: `firewalld` public zone allows only cockpit, dhcpv6-client, rsct-ctrmc, ssh; NO open ports. When our UI runs on 8400: `sudo firewall-cmd --permanent --add-port=8400/tcp && sudo firewall-cmd --reload`. Only 8400 needs opening; 8401 stays on localhost.
- 84xx ports: nothing listening (checked 2026-11-26).

## Quick check with Andrew (answered above; original wording kept for reference)

All we ask is to run a small rootless stack as `david` beside his work, touching nothing of his.
1. Is that OK, and which two free ports can we use (UI, backend)? Reachable from the IBM network or VPN only?
2. LLM: **agreed in principle (user and Andrew, 2026-11-26): we use the Granite 4 served on the Spyre cards (vLLM-Spyre), as a shared service, to speed up the RAG work.** What is still needed is only the mechanics: the URL/model name, whether it needs an API key, how our rootless containers reach it, and any rate or context limit (32768 vs 8096 noted in `SPYRE_LPAR_PLAN.md`; which instance is which). Read-only inspection shows the Spyre containers (`llm-1241b938ce-llm`, `llm-854167af0d-llm`, image `vllm-spyre-rhel9:3.5.0`) publish no host ports; they sit on the Launchpad pods' internal networks, so the route (a published port, a shared podman network, or via the Launchpad caddy/LiteLLM) must come from Andrew. Also on the box: `embedding-*` and `reranker-*` (vLLM) services. Worth asking whether we may use those too instead of in-process CPU embeddings (see open question below); a different embedding model means re-embedding our corpus.
3. Any objection to `loginctl enable-linger david` so our containers survive logout and reboot? (`linger` is `no` today.)
4. Quick `/home` quota or long-running-user-service policy? (`/home` has 322 GB free.)
5. Optional: are any Spyre cards free? Not needed, since we only act as an LLM client.

(Angela only needs to know we are a light second client on the Granite endpoint.)

## Superseded: original open decisions

1. Confirm Option 1 (keep `/api/generate`, client-side mapping) vs an OpenAI-compatible adapter so the stock `chatbot-ui` image could be reused unchanged (fastest, loses clarification and lifecycle cards).
2. Admin/ingest page in v1, or chat only first (recommended: chat first, read-only Sources page second)?
3. Folder: new `launchpad-ui/` (recommended) or replace `carbon-rag-ui/` in place?
4. Name/branding in the header (Launchpad uses "DigitalAssistant").
5. Still blocked on Andrew: ports, `linger`, and the Granite endpoint (see `SPYRE_LPAR_PLAN.md`).

## Verified facts

- 2026-11-26: `david` on the LPAR has no containers, images or listeners of ours. Launchpad runs as root podman: `chatbot-ui:v0.0.55`, `digitize-ui:v0.0.37`, `catalog-ui:v0.0.94`, OpenSearch 3.8.0, Granite on `vllm-spyre-rhel9:3.5.0`. `ai-services` CLI is v0.4.0; our work must not touch any of it.
- Template facts above were read from `IBM/project-ai-services` `main` on 2026-11-26.
