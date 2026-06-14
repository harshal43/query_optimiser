import { SQLBlock } from '../utils/sqlHighlight'

export function SQLDiff({ original, optimized, label }: {
  original: string
  optimized: string
  label?: string
}) {
  return (
    <div>
      {label && (
        <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-muted)', marginBottom: 8 }}>
          {label}
        </div>
      )}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
        <div>
          <div style={{ fontSize: 10, color: 'var(--text-muted)', marginBottom: 4 }}>ORIGINAL</div>
          <SQLBlock sql={original} />
        </div>
        <div>
          <div style={{ fontSize: 10, color: 'var(--success)', marginBottom: 4 }}>OPTIMIZED</div>
          <SQLBlock sql={optimized} style={{ borderColor: 'var(--success)', borderWidth: 1.5 }} />
        </div>
      </div>
    </div>
  )
}
