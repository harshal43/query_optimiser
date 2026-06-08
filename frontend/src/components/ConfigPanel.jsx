import { useRef, useState } from 'react';
import Editor from '@monaco-editor/react';

export default function ConfigPanel({
  config, onConfigChange, queryIds, selectedQueryId, onQueryChange,
  onUpload, uploading, uploadedFilename,
  inputMode, onInputModeChange, customQueryText, onCustomQueryTextChange,
  customCredits, onCustomCreditsChange,
  sfConnected, sfAccount, onOpenSnowflakeModal,
}) {
  const fileInputRef = useRef(null);
  const [dragOver, setDragOver] = useState(false);

  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    if (file) onUpload(file);
    e.target.value = '';
  };

  const isValidFile = (file) => /\.(xlsx|xls|csv)$/i.test(file.name);

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    if (uploading) return;
    const file = e.dataTransfer.files?.[0];
    if (file && isValidFile(file)) onUpload(file);
  };

  const handleDragOver = (e) => { e.preventDefault(); if (!uploading) setDragOver(true); };
  const handleDragLeave = (e) => { e.preventDefault(); setDragOver(false); };

  return (
    <div className="card">
      <div className="card-title">Configuration</div>

      {/* Model selector + Analyze button */}
      <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-end', marginBottom: '16px' }}>
        <div className="field" style={{ width: '220px', flexShrink: 0 }}>
          <label>Model</label>
          <select value={config.model} onChange={(e) => onConfigChange('model', e.target.value)}>
            <option value="claude-sonnet-4-5">Claude Sonnet 4</option>
            <option value="claude-3-5-sonnet-20241022">Claude 3.5 Sonnet</option>
            <option value="gpt-4o">GPT-4o</option>
            <option value="gpt-4o-mini">GPT-4o mini</option>
          </select>
        </div>
        <div style={{ flex: 1 }} />
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
          &#x1F4C1; Upload Excel / CSV
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
        <button
          onClick={() => {
            onInputModeChange('snowflake');
            if (!sfConnected) onOpenSnowflakeModal();
          }}
          style={{
            padding: '5px 14px', fontSize: '12px', borderRadius: 'var(--radius)',
            border: '1px solid var(--border-2)',
            background: inputMode === 'snowflake' ? 'var(--accent)' : 'var(--surface-2)',
            color: inputMode === 'snowflake' ? '#fff' : 'var(--text)',
            cursor: 'pointer', fontFamily: 'var(--sans)',
          }}
        >
          &#x2744;&#xFE0F; Snowflake Live
        </button>
      </div>

      {/* Snowflake mode — connect CTA or connected status */}
      {inputMode === 'snowflake' && !sfConnected && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <button
            onClick={onOpenSnowflakeModal}
            style={{
              padding: '7px 18px', fontSize: 13, borderRadius: 'var(--radius)',
              border: '1px solid var(--border-2)', background: 'var(--surface-2)',
              color: 'var(--text)', cursor: 'pointer', fontFamily: 'var(--sans)',
            }}
          >
            &#x2744;&#xFE0F; Connect to Snowflake
          </button>
          <span style={{ fontSize: 12, color: 'var(--text-dim)', fontFamily: 'var(--mono)' }}>
            No active connection
          </span>
        </div>
      )}
      {inputMode === 'snowflake' && sfConnected && (
        <div style={{ fontSize: 12, color: 'var(--success)', fontFamily: 'var(--mono)' }}>
          &#x25CF; Connected to {sfAccount} &mdash; select a query from the dashboard below
        </div>
      )}

      {/* Excel / CSV mode */}
      {inputMode === 'excel' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <input
            ref={fileInputRef}
            type="file"
            accept=".xlsx,.xls,.csv"
            style={{ display: 'none' }}
            onChange={handleFileChange}
          />

          {/* Drop zone */}
          <div
            onClick={() => !uploading && fileInputRef.current?.click()}
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            style={{
              border: `2px dashed ${dragOver ? 'var(--accent)' : uploadedFilename ? 'var(--success)' : 'var(--border-2)'}`,
              borderRadius: 8,
              padding: '20px 16px',
              textAlign: 'center',
              cursor: uploading ? 'not-allowed' : 'pointer',
              background: dragOver ? 'rgba(99,102,241,0.07)' : 'var(--surface-2)',
              transition: 'border-color 0.15s, background 0.15s',
              opacity: uploading ? 0.7 : 1,
            }}
          >
            {uploading ? (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8, color: 'var(--text-muted)', fontSize: 13, fontFamily: 'var(--sans)' }}>
                <span className="spinner" style={{ borderColor: 'rgba(255,255,255,0.2)', borderTopColor: 'var(--text-muted)' }} />
                Uploading...
              </div>
            ) : uploadedFilename ? (
              <div style={{ fontFamily: 'var(--mono)', fontSize: 12 }}>
                <div style={{ color: 'var(--success)', fontWeight: 600, marginBottom: 4 }}>
                  &#x2713; {uploadedFilename}
                </div>
                <div style={{ color: 'var(--text-dim)' }}>
                  {queryIds.length} queries loaded &mdash; drop another file to replace
                </div>
              </div>
            ) : (
              <div style={{ fontFamily: 'var(--sans)', fontSize: 13 }}>
                <div style={{ fontSize: 22, marginBottom: 6 }}>&#x1F4C1;</div>
                <div style={{ color: 'var(--text)', fontWeight: 600, marginBottom: 4 }}>
                  {dragOver ? 'Drop to upload' : 'Drag & drop here, or click to browse'}
                </div>
                <div style={{ color: 'var(--text-dim)', fontSize: 11 }}>
                  Supports .xlsx, .xls, .csv
                </div>
              </div>
            )}
          </div>

        </div>
      )}

      {/* Custom query mode */}
      {inputMode === 'custom' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          <div className="field" style={{ marginBottom: 0 }}>
            <label>SQL Query</label>
            <div style={{ height: 220, border: '1px solid #30363d', borderRadius: 8, overflow: 'hidden' }}>
              <Editor
                language="sql"
                value={customQueryText}
                theme="vs-dark"
                onChange={(val) => onCustomQueryTextChange(val ?? '')}
                options={{
                  minimap: { enabled: false },
                  scrollBeyondLastLine: false,
                  fontSize: 12.5,
                  lineNumbers: 'on',
                  wordWrap: 'on',
                  automaticLayout: true,
                  scrollbar: { verticalScrollbarSize: 6, horizontalScrollbarSize: 6 },
                }}
                loading={
                  <div style={{
                    height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center',
                    background: '#0d1117', color: '#8b949e', fontSize: 12, fontFamily: 'monospace',
                  }}>
                    Loading editor...
                  </div>
                }
              />
            </div>
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
