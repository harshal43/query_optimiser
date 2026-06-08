import { useRef } from 'react';

export default function ConfigPanel({
  config, onConfigChange, queryIds, selectedQueryId, onQueryChange,
  onAnalyze, analyzing, canAnalyze, onUpload, uploading, uploadedFilename,
  inputMode, onInputModeChange, customQueryText, onCustomQueryTextChange,
  customCredits, onCustomCreditsChange,
}) {
  const fileInputRef = useRef(null);

  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    if (file) onUpload(file);
    e.target.value = '';
  };

  const analyzeTooltip = !config.apiKey.trim() ? 'Enter an API key'
    : !config.baseUrl.trim() ? 'Enter an endpoint URL'
    : inputMode === 'custom' && !customQueryText.trim() ? 'Enter a SQL query'
    : inputMode === 'excel' && !selectedQueryId ? 'Select a query'
    : 'Run Agent 1 - get optimization suggestions';

  return (
    <div className="card">
      <div className="card-title">Configuration</div>

      {/* Row 1 - API Key + Endpoint URL */}
      <div className="config-grid" style={{ marginBottom: '12px' }}>
        <div className="field">
          <label>API Key</label>
          <input
            type="password"
            placeholder="sk-... or your X-API-KEY value"
            value={config.apiKey}
            onChange={(e) => onConfigChange('apiKey', e.target.value)}
            autoComplete="off"
          />
        </div>
        <div className="field">
          <label>LLM API Endpoint URL</label>
          <input
            type="url"
            placeholder="https://api.openai.com/v1 or full /chat/completions URL"
            value={config.baseUrl}
            onChange={(e) => onConfigChange('baseUrl', e.target.value)}
          />
        </div>
      </div>

      {/* Row 2 - Model + Analyze button */}
      <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-end', marginBottom: '16px' }}>
        <div className="field" style={{ width: '180px', flexShrink: 0 }}>
          <label>Model</label>
          <select value={config.model} onChange={(e) => onConfigChange('model', e.target.value)}>
            <option value="gpt-4o">gpt-4o</option>
            <option value="gpt-4o-mini">gpt-4o-mini</option>
          </select>
        </div>
        <div style={{ flex: 1 }} />
        <button
          className="btn-optimize"
          onClick={onAnalyze}
          disabled={!canAnalyze}
          title={analyzeTooltip}
        >
          {analyzing ? (<> <span className="spinner" /> Analyzing...</>) : (<>&#x1F50D; Analyze</>)}
        </button>
      </div>

      {/* Mode toggle */}
      <div style={{ display: 'flex', gap: '8px', marginBottom: '14px', borderTop: '1px solid var(--border)', paddingTop: '14px' }}>
        <span style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.07em', alignSelf: 'center', marginRight: '4px', whiteSpace: 'nowrap' }}>
          Input Mode
        </span>
        <button
          onClick={() => onInputModeChange('excel')}
          style={{
            padding: '5px 14px', fontSize: '12px', borderRadius: 'var(--radius)',
            border: '1px solid var(--border-2)',
            background: inputMode === 'excel' ? 'var(--accent)' : 'var(--surface-2)',
            color: inputMode === 'excel' ? '#fff' : 'var(--text)',
            cursor: 'pointer', fontFamily: 'var(--sans)',
          }}
        >
          &#x1F4C1; Upload Excel
        </button>
        <button
          onClick={() => onInputModeChange('custom')}
          style={{
            padding: '5px 14px', fontSize: '12px', borderRadius: 'var(--radius)',
            border: '1px solid var(--border-2)',
            background: inputMode === 'custom' ? 'var(--accent)' : 'var(--surface-2)',
            color: inputMode === 'custom' ? '#fff' : 'var(--text)',
            cursor: 'pointer', fontFamily: 'var(--sans)',
          }}
        >
          &#x270F; Custom Query
        </button>
      </div>

      {/* Excel mode */}
      {inputMode === 'excel' && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <input
            ref={fileInputRef}
            type="file"
            accept=".xlsx,.xls"
            style={{ display: 'none' }}
            onChange={handleFileChange}
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
            style={{
              display: 'flex', alignItems: 'center', gap: '7px',
              background: 'var(--surface-2)', border: '1px solid var(--border-2)',
              borderRadius: 'var(--radius)', color: 'var(--text)',
              fontFamily: 'var(--sans)', fontSize: '13px', padding: '7px 14px',
              cursor: uploading ? 'not-allowed' : 'pointer',
              opacity: uploading ? 0.6 : 1, whiteSpace: 'nowrap',
            }}
            onMouseEnter={(e) => { if (!uploading) e.currentTarget.style.borderColor = 'var(--accent-dim)'; }}
            onMouseLeave={(e) => { e.currentTarget.style.borderColor = 'var(--border-2)'; }}
          >
            {uploading ? (<> <span className="spinner" style={{ borderColor: 'rgba(255,255,255,0.3)', borderTopColor: 'var(--text-muted)' }} /> Uploading...</>) : (<>&#x1F4C1; Upload Excel</>)}
          </button>
          <span style={{ fontSize: '12px', color: uploadedFilename ? 'var(--success)' : 'var(--text-dim)', fontFamily: 'var(--mono)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {uploadedFilename ? `&#x2713; ${uploadedFilename} (${queryIds.length} queries loaded)` : 'No file uploaded'}
          </span>
          <div className="field" style={{ flex: 1, minWidth: 0, marginBottom: 0 }}>
            <select
              value={selectedQueryId}
              onChange={(e) => onQueryChange(e.target.value)}
              disabled={queryIds.length === 0 || uploading}
            >
              <option value="">{uploading ? 'Uploading...' : queryIds.length === 0 ? 'Upload a file first...' : '- Select a query -'}</option>
              {queryIds.map((id) => (<option key={id} value={id}>{id}</option>))}
            </select>
          </div>
        </div>
      )}

      {/* Custom query mode */}
      {inputMode === 'custom' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          <div className="field" style={{ marginBottom: 0 }}>
            <label>SQL Query</label>
            <textarea
              rows={8}
              placeholder="Paste or type your Snowflake SQL query here..."
              value={customQueryText}
              onChange={(e) => onCustomQueryTextChange(e.target.value)}
              style={{
                width: '100%', boxSizing: 'border-box', fontFamily: 'var(--mono)',
                fontSize: '12px', background: 'var(--surface-2)', color: 'var(--text)',
                border: '1px solid var(--border-2)', borderRadius: 'var(--radius)',
                padding: '10px 12px', resize: 'vertical', outline: 'none',
              }}
              onFocus={(e) => { e.currentTarget.style.borderColor = 'var(--accent-dim)'; }}
              onBlur={(e) => { e.currentTarget.style.borderColor = 'var(--border-2)'; }}
            />
          </div>
          <div className="field" style={{ width: '220px', marginBottom: 0 }}>
            <label>Snowflake Credits (optional)</label>
            <input
              type="number"
              min="0"
              step="any"
              placeholder="e.g. 4.5"
              value={customCredits}
              onChange={(e) => onCustomCreditsChange(e.target.value)}
            />
          </div>
        </div>
      )}
    </div>
  );
}