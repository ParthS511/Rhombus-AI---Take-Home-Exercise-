const API_BASE = (import.meta.env.VITE_API_BASE || '').replace(/\/$/, '')

async function parseResponse(res, fallbackMessage) {
  const text = await res.text()
  let data = {}
  try {
    data = text ? JSON.parse(text) : {}
  } catch {
    data = { error: text }
  }
  if (!res.ok) {
    throw new Error(data.error || fallbackMessage)
  }
  return data
}

export async function createJob(formData) {
  const res = await fetch(`${API_BASE}/api/jobs/`, { method: 'POST', body: formData })
  return parseResponse(res, 'Failed to create job')
}

export async function getJob(jobId) {
  const res = await fetch(`${API_BASE}/api/jobs/${jobId}/`)
  return parseResponse(res, 'Failed to fetch job')
}

export async function cancelJob(jobId) {
  const res = await fetch(`${API_BASE}/api/jobs/${jobId}/cancel/`, { method: 'POST' })
  return parseResponse(res, 'Failed to cancel job')
}

export async function fetchResultPage(jobId, page = 1, pageSize = 50) {
  const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) })
  const res = await fetch(`${API_BASE}/api/jobs/${jobId}/result/?${params}`)
  return parseResponse(res, 'Failed to fetch result')
}

export async function generateRegex(prompt) {
  const res = await fetch(`${API_BASE}/api/llm/regex/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt }),
  })
  return parseResponse(res, 'Failed to generate regex')
}

export async function regexReplace(payload) {
  const res = await fetch(`${API_BASE}/api/regex/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  return parseResponse(res, 'Failed to apply regex')
}

export async function healthCheck() {
  const res = await fetch(`${API_BASE}/api/health/`)
  return parseResponse(res, 'Backend is unavailable')
}
