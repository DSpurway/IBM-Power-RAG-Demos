# IBM Power Sales Manual Assistant (UI)

Chat front end for the Sales Manual RAG backend (`../rag-backend`). Answers questions about IBM Power servers from the IBM Sales Manuals and links back to the original IBM pages.

Built on the IBM Launchpad `chatbot-ui` template (Apache-2.0, `IBM/project-ai-services`, `ui/chatbot`): Vite, React 19, `@carbon/react` and `@carbon/ai-chat`.

## How it works

The backend keeps its `POST /api/generate` contract. The browser converts each response into Carbon AI Chat blocks (`src/responseMapper.js`), so the backend does not need to know about the UI.

| Backend response | What the user sees |
|---|---|
| `*_clarification_needed` | Buttons; the choice re-sends the question with `server_mtm`, `server_model` or `lifecycle_field` |
| `table_data` | Carbon table |
| `features` | Accordion of feature codes with availability tags |
| `content` / `answer` | Markdown answer |
| `source_url` | Tile linking to the original IBM Sales Manual page |
| `chunks_used` | "Show context used" panel |

## Develop

```bash
npm install
npm run mock     # canned backend on :8401 (UI development only)
npm run dev      # http://localhost:3000, proxies /api and /health to RAG_BACKEND_URL (default http://localhost:8401)
npm run lint
npm test         # response mapper tests
npm run build    # static files in build/
```

To develop against a real backend: `RAG_BACKEND_URL=http://host:8401 npm run dev`.

## Deploy

Target is the Spyre LPAR, rootless podman, UI on port 8400 and backend on 8401. See `../UI_LAUNCHPAD_PLAN.md`.
