// components/UploadPanel.jsx
export default function UploadPanel({ onUpload, loading }) {
  function handleChange(e) {
    const file = e.target.files[0]
    if (file) onUpload(file)
  }

  return (
    <div style={{
      border: '2px dashed #d1d5db',
      borderRadius: 10,
      padding: '2rem',
      textAlign: 'center',
      background: loading ? '#f9fafb' : '#fff',
      transition: 'background 0.2s',
    }}>
      <div style={{ fontSize: 13, color: '#6b7280', marginBottom: 12 }}>
        Upload a bank statement CSV (date, description, amount, balance columns required)
      </div>
      <input
        type="file"
        accept=".csv"
        disabled={loading}
        onChange={handleChange}
        style={{ display: 'block', margin: '0 auto', cursor: loading ? 'not-allowed' : 'pointer' }}
      />
      {loading && (
        <div style={{ marginTop: 16 }}>
          <div style={{ fontSize: 13, color: '#6b7280' }}>
            Classifying transactions with Claude... this takes ~15 seconds
          </div>
          <div style={{
            marginTop: 8,
            height: 4,
            background: '#e5e7eb',
            borderRadius: 2,
            overflow: 'hidden',
          }}>
            <div style={{
              height: '100%',
              width: '60%',
              background: '#3b82f6',
              borderRadius: 2,
              animation: 'pulse 1.5s ease-in-out infinite',
            }} />
          </div>
          <style>{`@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }`}</style>
        </div>
      )}
    </div>
  )
}
