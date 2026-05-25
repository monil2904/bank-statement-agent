// api.js
// Single function: sends CSV to backend, returns analysis result.
// All fetch logic lives here — components never call fetch directly.

const API_BASE = 'http://localhost:8000'

export async function analyzeStatement(file) {
  const form = new FormData()
  form.append('file', file)

  const response = await fetch(`${API_BASE}/analyze`, {
    method: 'POST',
    body: form,
  })

  if (!response.ok) {
    const errorText = await response.text()
    let detail = errorText
    try {
      detail = JSON.parse(errorText).detail || errorText
    } catch (_) {}
    throw new Error(detail)
  }

  return response.json()
}
