import React, {useState} from 'react'
import { createJob } from '../api'

export default function UploadForm({onJobCreated}){
  const [file, setFile] = useState(null)
  const [prompt, setPrompt] = useState('')
  const [replacement, setReplacement] = useState('')
  const [targetCols, setTargetCols] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e){
    e.preventDefault()
    if(!file) return alert('Please choose a file')
    setLoading(true)
    try{
      const fd = new FormData()
      fd.append('file', file)
      fd.append('nl_prompt', prompt)
      fd.append('replacement', replacement)
      fd.append('target_columns', targetCols)
      const data = await createJob(fd)
      onJobCreated && onJobCreated(data.job_id || data.id)
    }catch(err){
      alert(err.message)
    }finally{setLoading(false)}
  }

  return (
    <div className="card">
      <h2>Upload file & describe pattern</h2>
      <form onSubmit={handleSubmit} className="form">
        <label>CSV / Excel file</label>
        <input type="file" accept=".csv,.xlsx,.xls" onChange={e=>setFile(e.target.files[0])} />

        <label>Describe the pattern (natural language)</label>
        <textarea value={prompt} onChange={e=>setPrompt(e.target.value)} placeholder="e.g. Find email addresses in the Email column" />

        <label>Replacement value</label>
        <input value={replacement} onChange={e=>setReplacement(e.target.value)} placeholder="REDACTED" />

        <label>Target column(s) (comma separated, optional)</label>
        <input value={targetCols} onChange={e=>setTargetCols(e.target.value)} placeholder="Email" />

        <button type="submit" className="btn" disabled={loading}>{loading ? 'Creating job…' : 'Start Job'}</button>
      </form>
    </div>
  )
}
