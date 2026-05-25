// App.jsx
import { useState } from 'react'
import UploadPanel from './components/UploadPanel'
import MetricsGrid from './components/MetricsGrid'
import AnomalyAlert from './components/AnomalyAlert'
import ChartSection from './components/ChartSection'
import TransactionTable from './components/TransactionTable'
import { analyzeStatement } from './api'

export default function App() {
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [fileName, setFileName] = useState(null)

  async function handleUpload(file) {
    setLoading(true)
    setError(null)
    setResult(null)
    setFileName(file.name)
    try {
      const data = await analyzeStatement(file)
      setResult(data)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ maxWidth: 960, margin: '0 auto', padding: '2rem 1rem', fontFamily: 'system-ui, sans-serif' }}>

      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 600, margin: 0, color: '#111827' }}>
          Bank Statement Agent
        </h1>
        <p style={{ fontSize: 13, color: '#6b7280', marginTop: 4, marginBottom: 0 }}>
          Auto-classify transactions · Compute underwriting metrics · Detect anomalies
        </p>
      </div>

      {/* Upload */}
      <UploadPanel onUpload={handleUpload} loading={loading} />

      {/* Error */}
      {error && (
        <div style={{
          marginTop: 16,
          padding: '12px 14px',
          background: '#fef2f2',
          border: '1px solid #fca5a5',
          borderRadius: 8,
          color: '#b91c1c',
          fontSize: 13,
        }}>
          <strong>Error:</strong> {error}
        </div>
      )}

      {/* Results */}
      {result && (
        <div style={{ marginTop: 24 }}>

          {/* File + row count badge */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            marginBottom: 12,
          }}>
            <span style={{ fontSize: 13, fontWeight: 500, color: '#374151' }}>{fileName}</span>
            <span style={{
              fontSize: 11,
              padding: '2px 8px',
              borderRadius: 10,
              background: '#dcfce7',
              color: '#166534',
            }}>
              {result.transactions.length} transactions
            </span>
          </div>

          {/* Anomaly alert — always first if present */}
          <AnomalyAlert anomalies={result.anomalies} />

          {/* Metrics */}
          <MetricsGrid metrics={result.metrics} />

          {/* Charts */}
          <ChartSection transactions={result.transactions} metrics={result.metrics} />

          {/* Summary */}
          <div style={{
            padding: '10px 14px',
            background: '#f8f9fa',
            borderRadius: 8,
            fontSize: 13,
            color: '#4b5563',
            lineHeight: 1.6,
            marginBottom: 4,
          }}>
            {result.summary}
          </div>

          {/* Transaction table */}
          <TransactionTable transactions={result.transactions} />
        </div>
      )}
    </div>
  )
}
