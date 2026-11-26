// Canned stand-in for rag-backend, for UI development only:  npm run mock
// Serves the same response shapes as POST /api/generate on http://localhost:8401
import http from 'node:http';
import { readFileSync } from 'node:fs';

const PORT = process.env.PORT || 8401;
const IBM = 'https://www.ibm.com/docs/en/announcements/';

const lifecycleTable = [
  '| Announced | Available | Withdrawn from marketing | End of service |',
  '|---|---|---|---|',
  '| 2026-07-14 | 2026-07-21 | - | Not yet announced |',
].join('\n');

function respond(body) {
  const prompt = (body.prompt || '').toLowerCase();

  if (/withdraw|lifecycle|end of/.test(prompt)) {
    if (prompt.includes('s1112') && !body.server_mtm) {
      return {
        query_type: 'mtm_clarification_needed',
        content: 'The IBM Power S1112 has more than one model. Which one do you mean?',
        clarification_options: [
          { value: '9242-21B', label: '9242-21B (rack)' },
          { value: '9242-21T', label: '9242-21T (tower)' },
        ],
        ai_services_used: ['watsonx_assistant'],
        processing_method: 'nlp_intent_detection',
      };
    }
    return {
      query_type: 'lifecycle_lookup',
      content: `**IBM Power ${body.server_mtm || 'E980'}** - not yet withdrawn from marketing.`,
      table_data: lifecycleTable,
      source_url: `${IBM}family-9242-01-power-s1112`,
      source_filename: 'IBM Power S1112 Sales Manual',
      ai_services_used: ['watsonx_assistant', 'opensearch'],
      processing_method: 'hybrid_table_lookup',
      response_time_ms: 42,
    };
  }

  if (/activation|feature code/.test(prompt)) {
    return {
      query_type: 'activation_lookup',
      server_model: 'S1022',
      source_url: `${IBM}power-s1022-9105-22a`,
      source_filename: 'IBM Power S1022 Sales Manual',
      features: [
        {
          feature_code: 'EPUA',
          description: 'One processor core activation for #EPG9',
          is_available: true,
          chunk_text: 'Feature EPUA: One processor core activation for #EPG9 ...',
          metadata: { source_url: `${IBM}power-s1022-9105-22a` },
        },
        {
          feature_code: 'EMAB',
          description: 'Memory activation 1 GB',
          is_available: false,
          discontinued_date: '2025-06-30',
          chunk_text: 'Feature EMAB: 1 GB memory activation ...',
        },
      ],
      ai_services_used: ['watsonx_assistant', 'opensearch'],
      processing_method: 'hybrid_table_lookup',
    };
  }

  return {
    query_type: 'rag',
    content:
      'The IBM Power E1180 is a POWER11 enterprise server. It scales to four system nodes and offers large memory capacity. (mock answer)',
    chunks_used: [
      {
        text: 'Power E1180 - Highlights: enterprise-class server built on the POWER11 processor ...',
        score: 0.912,
        metadata: { section: 'Highlights', source: `${IBM}family-908005-power-e1180-enterprise-server-9080-heu` },
      },
    ],
    source_url: `${IBM}family-908005-power-e1180-enterprise-server-9080-heu`,
    source_filename: 'IBM Power E1180 Sales Manual',
    ai_services_used: ['watsonx_assistant', 'opensearch', 'llm'],
    llm_model: 'granite',
    processing_method: 'full_rag_generation',
    response_time_ms: 1850,
  };
}

http
  .createServer((req, res) => {
    const send = (code, obj) => {
      res.writeHead(code, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify(obj));
    };
    if (req.url === '/health') return send(200, { status: 'ok', mock: true });
    if (req.url === '/api/sources' && req.method === 'GET') {
      // The real list (generated from the corpus); chunk counts are made up.
      const data = JSON.parse(
        readFileSync(new URL('../../rag-backend/sources.json', import.meta.url), 'utf8'),
      );
      data.sets.forEach((s) =>
        s.sources.forEach((src, i) => {
          src.chunks = i % 9 === 8 ? 0 : 120 + i * 37;
        }),
      );
      return send(200, data);
    }
    if (req.url === '/api/generate' && req.method === 'POST') {
      let raw = '';
      req.on('data', (c) => (raw += c));
      req.on('end', () => {
        try {
          const body = JSON.parse(raw || '{}');
          setTimeout(() => send(200, respond(body)), 400);
        } catch {
          send(400, { error: 'bad json' });
        }
      });
      return;
    }
    send(404, { error: 'not found' });
  })
  .listen(PORT, () => console.log(`mock rag-backend on http://localhost:${PORT}`));
