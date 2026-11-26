import assert from 'node:assert/strict';
import { test } from 'node:test';
import {
  buildRequestBody,
  escapeHtml,
  mapResponse,
} from './responseMapper.js';

const types = (items) =>
  items.map((i) => i.user_defined?.user_defined_type || i.response_type);

test('escapeHtml escapes angle brackets and ampersands', () => {
  assert.equal(escapeHtml('a <b> & c'), 'a &lt;b&gt; &amp; c');
});

test('plain RAG answer: text, sources (with source link), meta', () => {
  const items = mapResponse(
    {
      query_type: 'rag',
      content: 'The E1080 supports up to 64 TB.',
      source_url: 'https://www.ibm.com/docs/en/announcements/x',
      source_filename: 'x',
      chunks_used: [
        { text: 'chunk', score: 0.91, metadata: { section: 'Memory' } },
      ],
      ai_services_used: ['opensearch', 'llm'],
      processing_method: 'full_rag_generation',
    },
    'q',
  );
  assert.deepEqual(types(items), ['text', 'sources', 'meta']);
  assert.equal(items[1].user_defined.chunks[0].section, 'Memory');
  assert.equal(
    items[1].user_defined.source_url,
    'https://www.ibm.com/docs/en/announcements/x',
  );
});

test('lifecycle answer from table lookup includes the table, no chunks', () => {
  const items = mapResponse(
    {
      query_type: 'lifecycle',
      content: '**Withdrawn:** 2026-01-01',
      table_data: '| a | b |',
      source_url: 'https://example/x',
      processing_method: 'hybrid_table_lookup',
    },
    'q',
  );
  assert.deepEqual(types(items), ['text', 'lifecycle_table', 'sources', 'meta']);
});

test('clarification response carries prompt, parameter name and options', () => {
  const options = [{ value: '9242-21B', label: '9242-21B' }];
  const items = mapResponse(
    {
      query_type: 'mtm_clarification_needed',
      content: 'Which model?',
      clarification_options: options,
    },
    'when is S1112 withdrawn',
  );
  assert.deepEqual(types(items), ['text', 'clarification']);
  assert.equal(items[1].user_defined.param, 'server_mtm');
  assert.equal(items[1].user_defined.prompt, 'when is S1112 withdrawn');
  assert.deepEqual(items[1].user_defined.options, options);
});

test('feature lookup yields a features block, not the answer text', () => {
  const items = mapResponse(
    {
      query_type: 'activation_lookup',
      server_model: 'S1022',
      features: [{ feature_code: 'EPUB', description: 'Proc activation' }],
    },
    'q',
  );
  assert.deepEqual(types(items), ['text', 'features']);
  assert.match(items[0].text, /Found 1 feature\(s\) for S1022/);
});

test('answers are HTML-escaped', () => {
  const [text] = mapResponse({ content: 'up to <4 GHz>' }, 'q');
  assert.equal(text.text, 'up to &lt;4 GHz&gt;');
});

test('buildRequestBody re-sends the original prompt with the clarification choice', () => {
  assert.deepEqual(buildRequestBody('hello', null), {
    collection_name: 'sales_manuals',
    prompt: 'hello',
    top_k: 3,
  });
  assert.deepEqual(
    buildRequestBody('9242-21B', {
      prompt: 'when is S1112 withdrawn',
      param: 'server_mtm',
      value: '9242-21B',
    }),
    {
      collection_name: 'sales_manuals',
      prompt: 'when is S1112 withdrawn',
      top_k: 3,
      server_mtm: '9242-21B',
    },
  );
});
