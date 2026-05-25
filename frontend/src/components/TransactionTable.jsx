// components/TransactionTable.jsx
import { useState } from 'react'

const CATEGORY_COLORS = {
  salary:            { bg: '#dcfce7', text: '#166534', label: 'salary' },
  business_inflow:   { bg: '#dbeafe', text: '#1e40af', label: 'business inflow' },
  emi_payment:       { bg: '#fef3c7', text: '#92400e', label: 'emi payment' },
  bounce:            { bg: '#fca5a5', text: '#991b1b', label: 'bounce' },
  circular_transfer: { bg: '#fde68a', text: '#92400e', label: 'circular transfer' },
  gambling_crypto:   { bg: '#f3e8ff', text: '#6b21a8', label: 'gambling/crypto' },
  regular_expense:   { bg: '#f3f4f6', text: '#374151', label: 'regular expense' },
  other:             { bg: '#f9fafb', text: '#6b7280', label: 'other' },
}

function fmtAmount(n) {
  const abs = Math.abs(n).toLocaleString('en-IN', { maximumFractionDigits: 0 })
  return n >= 0 ? `+${abs}` : `-${abs}`
}

export default function TransactionTable({ transactions }) {
  const [filter, setFilter] = useState('all')

  const categories = ['all', ...Object.keys(CATEGORY_COLORS)]
  const visible = filter === 'all'
    ? transactions
    : transactions.filter(t => t.category === filter)

  return (
    <div style={{ marginTop: 20 }}>
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 12, alignItems: 'center' }}>
        <span style={{ fontSize: 12, color: '#6b7280', marginRight: 4 }}>Filter:</span>
        {categories.map(cat => {
          const color = CATEGORY_COLORS[cat]
          const isActive = filter === cat
          return (
            <button
              key={cat}
              onClick={() => setFilter(cat)}
              style={{
                fontSize: 11,
                padding: '3px 10px',
                borderRadius: 12,
                border: isActive ? '1.5px solid #374151' : '1px solid #e5e7eb',
                background: isActive ? (color?.bg || '#111827') : '#fff',
                color: isActive ? (color?.text || '#fff') : '#6b7280',
                cursor: 'pointer',
                fontWeight: isActive ? 600 : 400,
              }}
            >
              {cat === 'all' ? `all (${transactions.length})` : (color?.label || cat)}
            </button>
          )
        })}
      </div>

      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: '2px solid #e5e7eb' }}>
              {['Date', 'Description', 'Amount (₹)', 'Balance (₹)', 'Category', 'Conf', 'Reason'].map(h => (
                <th key={h} style={{
                  textAlign: h === 'Amount (₹)' || h === 'Balance (₹)' ? 'right' : 'left',
                  padding: '8px 10px',
                  fontWeight: 500,
                  color: '#6b7280',
                  whiteSpace: 'nowrap',
                }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {visible.map((t, i) => {
              const color = CATEGORY_COLORS[t.category] || CATEGORY_COLORS.other
              const lowConf = t.confidence < 0.6
              return (
                <tr key={i} style={{
                  background: color.bg,
                  borderBottom: '0.5px solid rgba(0,0,0,0.04)',
                }}>
                  <td style={{ padding: '7px 10px', whiteSpace: 'nowrap', color: '#374151' }}>{t.date}</td>
                  <td style={{
                    padding: '7px 10px',
                    maxWidth: 220,
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                    color: '#111827',
                  }} title={t.description}>{t.description}</td>
                  <td style={{
                    padding: '7px 10px',
                    textAlign: 'right',
                    fontVariantNumeric: 'tabular-nums',
                    color: t.amount >= 0 ? '#166534' : '#991b1b',
                    fontWeight: 500,
                  }}>{fmtAmount(t.amount)}</td>
                  <td style={{
                    padding: '7px 10px',
                    textAlign: 'right',
                    fontVariantNumeric: 'tabular-nums',
                    color: '#374151',
                  }}>{Math.round(t.balance).toLocaleString('en-IN')}</td>
                  <td style={{ padding: '7px 10px' }}>
                    <span style={{
                      fontSize: 10,
                      padding: '2px 7px',
                      borderRadius: 10,
                      background: 'rgba(0,0,0,0.07)',
                      color: color.text,
                      fontWeight: 500,
                    }}>{color.label}</span>
                  </td>
                  <td style={{
                    padding: '7px 10px',
                    fontWeight: 500,
                    color: lowConf ? '#dc2626' : '#374151',
                    whiteSpace: 'nowrap',
                  }}>
                    {(t.confidence * 100).toFixed(0)}%
                    {lowConf && <span style={{ fontSize: 10, marginLeft: 3 }}>⚠</span>}
                  </td>
                  <td style={{
                    padding: '7px 10px',
                    color: '#6b7280',
                    maxWidth: 220,
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                  }} title={t.reason}>{t.reason}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
        {visible.length === 0 && (
          <div style={{ padding: '20px', textAlign: 'center', color: '#9ca3af', fontSize: 13 }}>
            No transactions match this filter.
          </div>
        )}
      </div>
    </div>
  )
}
