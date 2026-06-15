const VITE_BASE = import.meta.env.VITE_API_BASE;
const ROOT = VITE_BASE ? VITE_BASE.replace(/\/$/, '') : 'http://localhost:8000';
const BASE = ROOT + '/api';
const ADMIN_BASE = ROOT + '/admin';

async function handleResponse(res) {
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try { const body = await res.json(); detail = body.detail || JSON.stringify(body); }
    catch (_) { detail = await res.text(); }
    throw new Error(detail);
  }
  return res.json();
}

export async function fetchQueryIds() {
  const res = await fetch(`${BASE}/queries`);
  const data = await handleResponse(res);
  return data.query_ids;
}

export async function fetchQueryDetail(queryId) {
  const res = await fetch(`${BASE}/queries/${encodeURIComponent(queryId)}`);
  return handleResponse(res);
}

export async function uploadExcel(file) {
  const form = new FormData();
  form.append('file', file);
  const res = await fetch(`${BASE}/upload-excel`, { method: 'POST', body: form });
  return handleResponse(res);
}

export async function fetchModels() {
  const res = await fetch(`${BASE}/models`);
  const data = await handleResponse(res);
  return data.models;
}

export async function analyzeQuery(queryId, model, strategy = '') {
  const res = await fetch(`${BASE}/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query_id: queryId, model, strategy }),
  });
  return handleResponse(res);
}

export async function optimizeQuery(queryId, model, selectedSuggestions, strategy = '') {
  const res = await fetch(`${BASE}/optimize`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query_id: queryId, model, selected_suggestions: selectedSuggestions, strategy }),
  });
  return handleResponse(res);
}

export async function analyzeCustomQuery(queryText, credits, model, strategy = '') {
  const res = await fetch(`${BASE}/analyze-custom`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query_text: queryText, credits: credits || 0, model, strategy }),
  });
  return handleResponse(res);
}

export async function optimizeCustomQuery(queryText, credits, model, selectedSuggestions, strategy = '') {
  const res = await fetch(`${BASE}/optimize-custom`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query_text: queryText, credits: credits || 0, model, selected_suggestions: selectedSuggestions, strategy }),
  });
  return handleResponse(res);
}

export async function connectSnowflake(credentials) {
  const res = await fetch(`${BASE}/snowflake/connect`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(credentials),
  });
  return handleResponse(res);
}

export async function checkSnowflakeStatus() {
  const res = await fetch(`${BASE}/snowflake/status`);
  return handleResponse(res);
}

export async function disconnectSnowflake() {
  const res = await fetch(`${BASE}/snowflake/disconnect`, { method: 'POST' });
  return handleResponse(res);
}

export async function fetchSnowflakeQueries(category) {
  const res = await fetch(`${BASE}/snowflake/queries?category=${encodeURIComponent(category)}`);
  return handleResponse(res);
}

export async function qualifyStrategy(priority, tolerance) {
  const res = await fetch(`${BASE}/qualify`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ priority, tolerance }),
  });
  return handleResponse(res);
}

export async function batchAnalyzeQueries(queryIds, model) {
  const res = await fetch(`${BASE}/batch-analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query_ids: queryIds, model }),
  });
  return handleResponse(res);
}

export async function getAdminConfig() {
  const res = await fetch(`${ADMIN_BASE}/config`);
  return handleResponse(res);
}

export async function saveAdminConfig(config) {
  const res = await fetch(`${ADMIN_BASE}/config`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  });
  return handleResponse(res);
}

export async function batchOptimizeQueries(items, model) {
  const res = await fetch(`${BASE}/batch-optimize`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ items, model }),
  });
  return handleResponse(res);
}
