// components/AnomalyAlert.jsx
export default function AnomalyAlert({ anomalies }) {
  if (!anomalies || anomalies.length === 0) return null

  return (
    <div style={{
      margin: '16px 0',
      padding: '14px 16px',
      background: '#fff7ed',
      border: '1px solid #fed7aa',
      borderRadius: 8,
    }}>
      <div style={{
        fontWeight: 600,
        color: '#c2410c',
        fontSize: 14,
        marginBottom: 8,
        display: 'flex',
        alignItems: 'center',
        gap: 6,
      }}>
        Anomalies detected — {anomalies.length} issue(s) require underwriter review
      </div>
      {anomalies.map((anomaly, i) => (
        <div key={i} style={{
          marginTop: i > 0 ? 10 : 0,
          paddingTop: i > 0 ? 10 : 0,
          borderTop: i > 0 ? '1px solid #fed7aa' : 'none',
          display: 'flex',
          gap: 10,
          alignItems: 'flex-start',
        }}>
          <span style={{
            fontSize: 10,
            fontWeight: 600,
            padding: '3px 8px',
            borderRadius: 12,
            background: anomaly.severity === 'hard' ? '#fca5a5' : '#fde68a',
            color: anomaly.severity === 'hard' ? '#991b1b' : '#92400e',
            whiteSpace: 'nowrap',
            marginTop: 1,
          }}>
            {anomaly.severity.toUpperCase()}
          </span>
          <div>
            <span style={{
              fontSize: 12,
              fontWeight: 500,
              color: '#374151',
              marginRight: 6,
            }}>
              {anomaly.anomaly_type.replace(/_/g, ' ')}:
            </span>
            <span style={{ fontSize: 12, color: '#4b5563' }}>
              {anomaly.description}
            </span>
            <div style={{ fontSize: 11, color: '#9ca3af', marginTop: 2 }}>
              Rows affected: {anomaly.affected_rows.join(', ')}
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}
