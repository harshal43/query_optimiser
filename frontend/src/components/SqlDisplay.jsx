import { useState } from 'react';
import Editor from '@monaco-editor/react';

export default function SqlDisplay({ sql, maxHeight = '320px' }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(sql || '').then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    });
  };

  return (
    <div className="sql-block-wrapper" style={{ position: 'relative' }}>
      <button
        className={`copy-btn ${copied ? 'copied' : ''}`}
        onClick={handleCopy}
        title="Copy SQL"
      >
        {copied ? '&#x2713; Copied' : 'Copy'}
      </button>
      <div style={{
        height: maxHeight, border: '1px solid #30363d', borderRadius: 8, overflow: 'hidden',
      }}>
        <Editor
          language="sql"
          value={sql || '-- No query loaded'}
          theme="vs-dark"
          options={{
            readOnly: true,
            minimap: { enabled: false },
            scrollBeyondLastLine: false,
            fontSize: 12.5,
            lineNumbers: 'on',
            wordWrap: 'on',
            automaticLayout: true,
            renderLineHighlight: 'none',
            contextmenu: false,
            folding: true,
            overviewRulerBorder: false,
            hideCursorInOverviewRuler: true,
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
  );
}
