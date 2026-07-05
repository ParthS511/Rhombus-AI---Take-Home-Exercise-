const API_BASE = (import.meta.env.VITE_API_BASE || 'http://localhost:8000')

export async function createJob(formData){
  const res = await fetch(`${API_BASE}/api/jobs/`, { method: 'POST', body: formData })
  if(!res.ok) throw new Error('Failed to create job')
  return res.json()
}

export async function getJob(jobId){
  const res = await fetch(`${API_BASE}/api/jobs/${jobId}/`)
  if(!res.ok) throw new Error('Failed to fetch job')
  return res.json()
}

export async function fetchResultPage(jobId,page=1,page_size=50){
  const res = await fetch(`${API_BASE}/api/jobs/${jobId}/result/?page=${page}&page_size=${page_size}`)
  if(!res.ok) throw new Error('Failed to fetch result')
  return res.json()
}
