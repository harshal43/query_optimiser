// Use Vite env VITE_API_BASE when provided (e.g. http://localhost:8000)
const VITE_BASE = import.meta.env.VITE_API_BASE;
const BASE = (VITE_BASE ? VITE_BASE.replace(/\/$/, '') : 'http://localhost:8000') + '/api';

// ------------------------------------------------------------------ // Helpers // ------------------------------------------------------------------
async function handleResponse(res) {
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try { const body = await res.json(); detail = body.detail || JSON.stringify(body); }
    catch (_) { detail = await res.text(); }
    throw new Error(detail);
  }
  return res.json();
}

// ------------------------------------------------------------------ // Endpoints // ------------------------------------------------------------------

/** Fetch all available Query IDs */
export async function fetchQueryIds() {
  const res = await fetch(`${BASE}/queries`);
  const data = await handleResponse(res);
  return data.query_ids;
}

/** Fetch a single query's text + credits */
export async function fetchQueryDetail(queryId) {
  const res = await fetch(`${BASE}/queries/${encodeURIComponent(queryId)}`);
  return handleResponse(res);
}

/** Upload an Excel file. Returns { filename, query_count, query_ids }. */
export async function uploadExcel(file) {
  const form = new FormData();
  form.append('file', file);
  const res = await fetch(`${BASE}/upload-excel`, { method: 'POST', body: form });
  return handleResponse(res);
}

/** Fetch supported model names */
export async function fetchModels() {
  const res = await fetch(`${BASE}/models`);
  const data = await handleResponse(res);
  return data.models;
}

/** * Step 1 - Run Agent 1 only. Returns parsed suggestions list.
 * @param {string} queryId
 * @param {{ apiKey, baseUrl, model }} llmConfig
 */
export async function analyzeQuery(queryId, llmConfig) {
  const res = await fetch(`${BASE}/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query_id: queryId,
      llm_config: {
        api_key: llmConfig.apiKey,
        base_url: llmConfig.baseUrl,
        model: llmConfig.model,
      },
    }),
  });
  return handleResponse(res);
}

/** * Step 2 - Run Agent 2 with only the user-selected suggestions.
 * @param {string} queryId
 * @param {{ apiKey, baseUrl, model }} llmConfig
 * @param {string[]} selectedSuggestions - full_text of each selected suggestion
 */
export async function optimizeQuery(queryId, llmConfig, selectedSuggestions) {
  const res = await fetch(`${BASE}/optimize`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query_id: queryId,
      llm_config: {
        api_key: llmConfig.apiKey,
        base_url: llmConfig.baseUrl,
        model: llmConfig.model,
      },
      selected_suggestions: selectedSuggestions,
    }),
  });
  return handleResponse(res);
}

/** * Step 1 (custom) - Run Agent 1 on a user-supplied SQL query.
 * @param {string} queryText
 * @param {number} credits
 * @param {{ apiKey, baseUrl, model }} llmConfig
 */
export async function analyzeCustomQuery(queryText, credits, llmConfig) {
  const res = await fetch(`${BASE}/analyze-custom`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query_text: queryText,
      credits: credits || 0,
      llm_config: {
        api_key: llmConfig.apiKey,
        base_url: llmConfig.baseUrl,
        model: llmConfig.model,
      },
    }),
  });
  return handleResponse(res);
}

/** * Step 2 (custom) - Run Agent 2 on a user-supplied SQL query.
 * @param {string} queryText
 * @param {number} credits
 * @param {{ apiKey, baseUrl, model }} llmConfig
 * @param {string[]} selectedSuggestions
 */
export async function optimizeCustomQuery(queryText, credits, llmConfig, selectedSuggestions) {
  const res = await fetch(`${BASE}/optimize-custom`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query_text: queryText,
      credits: credits || 0,
      llm_config: {
        api_key: llmConfig.apiKey,
        base_url: llmConfig.baseUrl,
        model: llmConfig.model,
      },
      selected_suggestions: selectedSuggestions,
    }),
  });
  return handleResponse(res);
}