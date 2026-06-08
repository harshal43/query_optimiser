import { useState } from 'react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';

/** * Renders a SQL string with syntax highlighting and a copy button.
 *
 * Props:
 *   sql      : string - the SQL to display
 *   maxHeight: string - CSS max-height (default '320px')
 */
export default function SqlDisplay({ sql, maxHeight = '320px' }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(sql).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    });
  };

  return (
    <div className="sql-block-wrapper" style={{ '--max-h': maxHeight }}>
      <button
        className={`copy-btn ${copied ? 'copied' : ''}`}
        onClick={handleCopy}
        title="Copy SQL"
      >
        {copied ? '&#x2713; Copied' : 'Copy'}
      </button>
      <SyntaxHighlighter
        language="sql"
        style={vscDarkPlus}
        customStyle={{
          margin: 0, maxHeight, fontSize: '12.5px',
          background: '#0d1117', border: '1px solid #30363d',
          borderRadius: '8px',
        }}
        wrapLongLines={false}
      >
        {sql || '-- No query loaded'}
      </SyntaxHighlighter>
    </div>
  );
}