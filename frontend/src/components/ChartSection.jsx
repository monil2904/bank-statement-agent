// components/ChartSection.jsx
// Lightweight dashboard charts using plain HTML/CSS — no chart library.

const MONTH_NAMES = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun']

const CATEGORY_LABELS = {
  salary: 'Salary',
  business_inflow: 'Business Inflow',
  emi_payment: 'EMI Payment',
  bounce: 'Bounce',
  circular_transfer: 'Circular Transfer',
  gambling_crypto: 'Gambling / Crypto',
  regular_expense: 'Regular Expense',
  other: 'Other',
}

const CATEGORY_COLORS = {
  salary: '#166534',
  business_inflow: '#1e40af',
  emi_payment: '#92400e',
  bounce: '#991b1b',
  circular_transfer: '#b45309',
  gambling_crypto: '#6b21a8',
  regular_expense: '#374151',
  other: '#6b7280',
}

function fmt(n) {
  return Math.round(n).toLocaleString('en-IN')
}

export default function ChartSection({ transactions, metrics }) {
  // ── Monthly BTO bars ──────────────────────────────────────────────
  const maxBto = Math.max(...metrics.monthly_bto, 1)
  const btoData = metrics.monthly_bto.map((value, i) => ({
    month: `${MONTH_NAMES[i]} 2024`,
    value,
    pct: (value / maxBto) * 100,
  }))

  // ── Category distribution ─────────────────────────────────────────
  const catStats = {}
  transactions.forEach(t => {
    const cat = t.category
    if (!catStats[cat]) {
      catStats[cat] = { count: 0, amount: 0 }
    }
    catStats[cat].count += 1
    catStats[cat].amount += Math.abs(t.amount)
  })

  const catEntries = Object.entries(catStats)
    .map(([key, val]) => ({
      key,
      label: CATEGORY_LABELS[key] || key,
      color: CATEGORY_COLORS[key] || '#6b7280',
      ...val,
    }))
    .sort((a, b) => b.amount - a.amount)

  const maxCatAmount = Math.max(...catEntries.map(c => c.amount), 1)
  const totalTx = transactions.length

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
      gap: 16,
      margin: '20px 0',
    }}>
      {/* Monthly BTO */}
      <div style={{
        padding: 16,
        background: '#fff',
        borderRadius: 8,
        border: '1px solid #e5e7eb',
      }}>
        <div style={{ fontSize: 13, fontWeight: 600, color: '#111827', marginBottom: 12 }}>
          Monthly Bank Turnover (BTO)
        </div>
        {btoData.map(d => (
          <div key={d.month} style={{ marginBottom: 10 }}>
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              fontSize: 11,
              color: '#4b5563',
              marginBottom: 3,
            }}>
              <span>{d.month}</span>
              <span style={{ fontWeight: 500 }}>₹{fmt(d.value)}</span>
            </div>
            <div style={{
              height: 10,
              background: '#e5e7eb',
              borderRadius: 5,
              overflow: 'hidden',
            }}>
              <div style={{
                height: '100%',
                width: `${d.pct}%`,
                background: '#3b82f6',
                borderRadius: 5,
                transition: 'width 0.4s ease',
              }} />
            </div>
          </div>
        ))}
        <div style={{
          marginTop: 8,
          paddingTop: 8,
          borderTop: '1px solid #e5e7eb',
          fontSize: 11,
          color: '#6b7280',
          display: 'flex',
          justifyContent: 'space-between',
        }}>
          <span>Average</span>
          <span style={{ fontWeight: 500, color: '#111827' }}>₹{fmt(metrics.avg_bto)}</span>
        </div>
      </div>

      {/* Category Breakdown */}
      <div style={{
        padding: 16,
        background: '#fff',
        borderRadius: 8,
        border: '1px solid #e5e7eb',
      }}>
        <div style={{ fontSize: 13, fontWeight: 600, color: '#111827', marginBottom: 12 }}>
          Category Breakdown
        </div>
        {catEntries.map(c => (
          <div key={c.key} style={{ marginBottom: 10 }}>
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              fontSize: 11,
              color: '#4b5563',
              marginBottom: 3,
            }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <span style={{
                  width: 8,
                  height: 8,
                  borderRadius: 2,
                  background: c.color,
                  display: 'inline-block',
                }} />
                {c.label}
              </span>
              <span style={{ fontWeight: 500 }}>
                {c.count} tx · ₹{fmt(c.amount)}
              </span>
            </div>
            <div style={{
              height: 10,
              background: '#e5e7eb',
              borderRadius: 5,
              overflow: 'hidden',
            }}>
              <div style={{
                height: '100%',
                width: `${(c.amount / maxCatAmount) * 100}%`,
                background: c.color,
                borderRadius: 5,
                transition: 'width 0.4s ease',
              }} />
            </div>
          </div>
        ))}
        <div style={{
          marginTop: 8,
          paddingTop: 8,
          borderTop: '1px solid #e5e7eb',
          fontSize: 11,
          color: '#6b7280',
          display: 'flex',
          justifyContent: 'space-between',
        }}>
          <span>Total transactions</span>
          <span style={{ fontWeight: 500, color: '#111827' }}>{totalTx}</span>
        </div>
      </div>
    </div>
  )
}
