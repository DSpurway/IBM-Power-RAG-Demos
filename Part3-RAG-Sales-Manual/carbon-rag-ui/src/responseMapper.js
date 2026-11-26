// Pure mapping from a rag-backend /api/generate response to Carbon AI Chat response items.
// No DOM or React here, so it can be unit tested with `node --test`.

export const COLLECTION_NAME = 'sales_manuals';
export const TOP_K = 3;

// query_type of a clarification response -> request parameter that carries the user's choice
export const CLARIFICATION_PARAM = {
  mtm_clarification_needed: 'server_mtm',
  server_clarification_needed: 'server_model',
  lifecycle_clarification_needed: 'lifecycle_field',
};

// Escape HTML so angle brackets in answers are shown as text, not interpreted as markup.
export function escapeHtml(text) {
  return String(text ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

function textItem(text) {
  return { response_type: 'text', text: escapeHtml(text) };
}

function userDefined(type, data) {
  return {
    response_type: 'user_defined',
    user_defined: { user_defined_type: type, ...data },
  };
}

export function buildRequestBody(prompt, pending) {
  const body = {
    collection_name: COLLECTION_NAME,
    prompt: pending ? pending.prompt : prompt,
    top_k: TOP_K,
  };
  if (pending) body[pending.param] = pending.value;
  return body;
}

export function mapResponse(data, prompt) {
  const generic = [];
  const queryType = data.query_type;
  const answer = data.content || data.answer || '';

  // 1. Clarification: ask the user to pick, re-send with the choice
  if (
    Array.isArray(data.clarification_options) &&
    data.clarification_options.length > 0
  ) {
    generic.push(textItem(answer || 'Please choose an option.'));
    generic.push(
      userDefined('clarification', {
        prompt,
        param: CLARIFICATION_PARAM[queryType],
        options: data.clarification_options,
      }),
    );
    return generic;
  }

  const hasFeatures =
    (queryType === 'activation_lookup' ||
      queryType === 'physical_feature_lookup') &&
    Array.isArray(data.features);

  // 2. Answer text
  if (hasFeatures) {
    generic.push(
      textItem(
        `Found ${data.features.length} feature(s) for ${data.server_model || 'this server'}.`,
      ),
    );
    generic.push(
      userDefined('features', {
        features: data.features,
        server_model: data.server_model,
      }),
    );
  } else {
    generic.push(textItem(answer || 'No answer was returned.'));
  }

  // 3. Lifecycle table from the Sales Manual (direct lookup, no LLM)
  if (data.table_data) {
    generic.push(userDefined('lifecycle_table', { table: data.table_data }));
  }

  // 4. Sources: link back to the original IBM Sales Manual + retrieved context
  const chunks = (data.chunks_used || []).map((c) => ({
    text: c.text,
    score: c.score,
    section: c.metadata?.section,
    source: c.metadata?.source,
  }));
  if (data.source_url || chunks.length > 0) {
    generic.push(
      userDefined('sources', {
        source_url: data.source_url,
        source_filename: data.source_filename,
        chunks,
      }),
    );
  }

  // 5. How the answer was produced
  if (data.ai_services_used || data.processing_method) {
    generic.push(
      userDefined('meta', {
        services: data.ai_services_used || [],
        llm_model: data.llm_model,
        processing_method: data.processing_method,
        response_time_ms: data.response_time_ms,
      }),
    );
  }

  return generic;
}
