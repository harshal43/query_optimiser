import React from 'react'

export type TokenKind = 'keyword' | 'string' | 'comment' | 'number' | 'plain'

export interface Token {
  kind: TokenKind
  text: string
}

const KEYWORDS = new Set([
  'SELECT','FROM','WHERE','JOIN','LEFT','RIGHT','INNER','OUTER','FULL','CROSS',
  'ON','AND','OR','NOT','IN','EXISTS','BETWEEN','LIKE','IS','NULL','AS',
  'GROUP','BY','ORDER','HAVING','LIMIT','OFFSET','UNION','ALL','DISTINCT',
  'INSERT','INTO','VALUES','UPDATE','SET','DELETE','CREATE','TABLE','VIEW',
  'DROP','ALTER','ADD','COLUMN','INDEX','WITH','RECURSIVE','CASE','WHEN',
  'THEN','ELSE','END','CAST','OVER','PARTITION','ROWS','RANGE','UNBOUNDED',
  'PRECEDING','FOLLOWING','CURRENT','ROW','ASC','DESC','NULLS','FIRST','LAST',
  'DATEADD','DATEDIFF','CURRENT_TIMESTAMP','GETDATE','IFF','COALESCE','NVL',
])

export function tokenize(sql: string): Token[] {
  const tokens: Token[] = []
  let i = 0

  while (i < sql.length) {
    // Line comment
    if (sql[i] === '-' && sql[i + 1] === '-') {
      const end = sql.indexOf('\n', i)
      const text = end === -1 ? sql.slice(i) : sql.slice(i, end + 1)
      tokens.push({ kind: 'comment', text })
      i += text.length
      continue
    }

    // Block comment
    if (sql[i] === '/' && sql[i + 1] === '*') {
      const end = sql.indexOf('*/', i + 2)
      const text = end === -1 ? sql.slice(i) : sql.slice(i, end + 2)
      tokens.push({ kind: 'comment', text })
      i += text.length
      continue
    }

    // String literal
    if (sql[i] === "'" || sql[i] === '"') {
      const q = sql[i]
      let j = i + 1
      while (j < sql.length) {
        if (sql[j] === q && sql[j + 1] === q) { j += 2; continue }
        if (sql[j] === q) { j++; break }
        j++
      }
      tokens.push({ kind: 'string', text: sql.slice(i, j) })
      i = j
      continue
    }

    // Number
    if (/[0-9]/.test(sql[i]) || (sql[i] === '.' && /[0-9]/.test(sql[i + 1] ?? ''))) {
      let j = i
      while (j < sql.length && /[0-9._eE+\-]/.test(sql[j])) j++
      tokens.push({ kind: 'number', text: sql.slice(i, j) })
      i = j
      continue
    }

    // Word / keyword
    if (/[A-Za-z_$]/.test(sql[i])) {
      let j = i
      while (j < sql.length && /[\w$]/.test(sql[j])) j++
      const word = sql.slice(i, j)
      tokens.push({ kind: KEYWORDS.has(word.toUpperCase()) ? 'keyword' : 'plain', text: word })
      i = j
      continue
    }

    // Whitespace & punctuation
    let j = i
    while (j < sql.length && !/[A-Za-z_$0-9'"/-]/.test(sql[j])) j++
    if (j === i) j++
    tokens.push({ kind: 'plain', text: sql.slice(i, j) })
    i = j
  }

  return tokens
}

export function SQLBlock({ sql, style }: { sql: string; style?: React.CSSProperties }) {
  const tokens = tokenize(sql)
  return (
    <pre style={{
      fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
      fontSize: 12, lineHeight: 1.6, margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word',
      background: 'var(--code-bg)', border: '1px solid var(--code-border)',
      borderRadius: 6, padding: '12px 14px', overflowX: 'auto',
      ...style,
    }}>
      {tokens.map((t, i) => {
        const color = t.kind === 'keyword' ? 'var(--sql-kw)'
          : t.kind === 'string' ? 'var(--sql-str)'
          : t.kind === 'comment' ? 'var(--sql-comment)'
          : t.kind === 'number' ? 'var(--sql-num)'
          : 'var(--text-primary)'
        return <span key={i} style={{ color }}>{t.text}</span>
      })}
    </pre>
  )
}
