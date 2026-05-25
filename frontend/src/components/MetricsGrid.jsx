// components/MetricsGrid.jsx
function fmt(n) { return Math.round(n).toLocaleString('en-IN') }

export default function MetricsGrid({ metrics }) {
  const cards = [
    {
      label: 'Avg bank balance (ABB)',
      value: '₹' + fmt(metrics.abb),
      note: 'Mean closing balance',
      warn: metrics.abb < 10000,
    },
    {
      label: 'Avg monthly turnover (BTO)',
      value: '₹' + fmt(metrics.avg_bto),
      note: 'Avg monthly inflow',
      warn: false,
    },
    {
      label: 'Bounce ratio',
      value: (metrics.bounce_ratio * 100).toFixed(1) + '%',
      note: 'Bounced / total debits',
      warn: metrics.bounce_ratio > 0.05,
    },
    {
      label: 'FOIR (approx)',
      value: (metrics.foir_approx * 100).toFixed(1) + '%',
      note: 'EMI outflow / total inflow',
      warn: metrics.foir_approx > 0.5,
    },
  ]

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: 'repeat(4, 1fr)',
      gap: 12,
      margin: '20px 0',
    }}>
      {cards.map(card => (
        <div key={card.label} style={{
          padding: 16,
          background: card.warn ? '#fff7ed' : '#f8f9fa',
          borderRadius: 8,
          border: card.warn ? '1px solid #fed7aa' : '1px solid #e5e7eb',
        }}>
          <div style={{ fontSize: 11, color: '#6b7280', marginBottom: 4 }}>{card.label}</div>
          <div style={{
            fontSize: 22,
            fontWeight: 600,
            color: card.warn ? '#c2410c' : '#111827',
            marginBottom: 2,
          }}>{card.value}</div>
          <div style={{ fontSize: 11, color: '#9ca3af' }}>{card.note}</div>
        </div>
      ))}
      {metrics.low_confidence_count > 0 && (
        <div style={{
          gridColumn: '1 / -1',
          padding: '8px 12px',
          background: '#fef3c7',
          borderRadius: 6,
          fontSize: 12,
          color: '#92400e',
          border: '1px solid #fde68a',
        }}>
          {metrics.low_confidence_count} transaction(s) have low classifier confidence (&lt;60%) — flagged for human review (shown in red in the table below)
        </div>
      )}
    </div>
  )
}
