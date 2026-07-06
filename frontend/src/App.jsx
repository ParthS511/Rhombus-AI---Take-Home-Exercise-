import React, { useEffect, useMemo, useState } from 'react'
import {
  cancelJob,
  createJob,
  fetchResultPage,
  generateRegex,
  getJob,
  healthCheck,
  regexReplace,
} from './api'

const TERMINAL_STATUSES = new Set(['succeeded', 'failed', 'canceled'])
const PAGE_SIZE = 25

function statusLabel(status) {
  const labels = {
    pending: 'Queued',
    running: 'Running',
    succeeded: 'Succeeded',
    failed: 'Failed',
    canceled: 'Canceled',
  }
  return labels[status] || 'Idle'
}

function splitColumns(value) {
  return value
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)
}

function parseCsvHeader(text) {
  const firstLine = text.split(/\r?\n/).find((line) => line.trim())
  if (!firstLine) return []
  return firstLine
    .split(',')
    .map((item) => item.trim().replace(/^"|"$/g, ''))
    .filter(Boolean)
}

export default function App() {
  const [backendStatus, setBackendStatus] = useState('checking')
  const [file, setFile] = useState(null)
  const [columns, setColumns] = useState([])
  const [selectedColumns, setSelectedColumns] = useState([])
  const [prompt, setPrompt] = useState('Find email addresses and replace them')
  const [replacement, setReplacement] = useState('REDACTED')
  const [engine, setEngine] = useState('spark')
  const [job, setJob] = useState(null)
  const [jobs, setJobs] = useState([])
  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState('')
  const [preview, setPreview] = useState(null)
  const [previewing, setPreviewing] = useState(false)

  useEffect(() => {
    let ignore = false
    healthCheck()
      .then(() => {
        if (!ignore) setBackendStatus('online')
      })
      .catch(() => {
        if (!ignore) setBackendStatus('offline')
      })
    return () => {
      ignore = true
    }
  }, [])

  useEffect(() => {
    if (!job?.id || TERMINAL_STATUSES.has(job.status)) return undefined
    let ignore = false
    const timer = setInterval(async () => {
      try {
        const freshJob = await getJob(job.id)
        if (ignore) return
        setJob(freshJob)
        setJobs((items) => items.map((item) => (item.id === freshJob.id ? freshJob : item)))
      } catch (error) {
        if (!ignore) setFormError(error.message)
      }
    }, 1800)
    return () => {
      ignore = true
      clearInterval(timer)
    }
  }, [job])

  const selectedColumnText = useMemo(() => selectedColumns.join(', '), [selectedColumns])

  async function handleFileChange(event) {
    const nextFile = event.target.files?.[0] || null
    setFile(nextFile)
    setColumns([])
    setSelectedColumns([])
    setPreview(null)
    if (!nextFile) return
    const sample = await nextFile.slice(0, 8192).text()
    const parsedColumns = parseCsvHeader(sample)
    setColumns(parsedColumns)
    setSelectedColumns(parsedColumns.slice(0, 1))
  }

  function toggleColumn(column) {
    setSelectedColumns((current) => {
      if (current.includes(column)) return current.filter((item) => item !== column)
      return [...current, column]
    })
  }

  async function handlePreviewRegex() {
    setPreviewing(true)
    setFormError('')
    try {
      const payload = await generateRegex(prompt)
      setPreview(payload)
    } catch (error) {
      setFormError(error.message)
    } finally {
      setPreviewing(false)
    }
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setFormError('')
    if (!file) {
      setFormError('Choose a CSV file first.')
      return
    }
    if (!prompt.trim()) {
      setFormError('Describe what pattern should be replaced.')
      return
    }
    setSubmitting(true)
    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('natural_language_prompt', prompt)
      formData.append('replacement', replacement)
      formData.append('target_columns', selectedColumnText)
      formData.append('engine', engine)
      const createdJob = await createJob(formData)
      setJob(createdJob)
      setJobs((items) => [createdJob, ...items.filter((item) => item.id !== createdJob.id)].slice(0, 8))
    } catch (error) {
      setFormError(error.message)
    } finally {
      setSubmitting(false)
    }
  }

  async function handleCancel() {
    if (!job?.id) return
    try {
      const canceledJob = await cancelJob(job.id)
      setJob(canceledJob)
      setJobs((items) => items.map((item) => (item.id === canceledJob.id ? canceledJob : item)))
    } catch (error) {
      setFormError(error.message)
    }
  }

  return (
    <main className="app-shell">
      <header className="app-header">
        <div>
          <p className="eyebrow">Rhombus AI</p>
          <h1>Regex Data Processor</h1>
        </div>
        <div className={`health health-${backendStatus}`}>
          <span aria-hidden="true" />
          {backendStatus === 'online' ? 'API online' : backendStatus === 'offline' ? 'API offline' : 'Checking API'}
        </div>
      </header>

      <section className="workspace">
        <form className="panel job-panel" onSubmit={handleSubmit}>
          <div className="panel-title">
            <h2>New Job</h2>
            <div className="engine-toggle" aria-label="Processing engine">
              <button type="button" className={engine === 'spark' ? 'active' : ''} onClick={() => setEngine('spark')}>
                Spark
              </button>
              <button type="button" className={engine === 'python' ? 'active' : ''} onClick={() => setEngine('python')}>
                Python
              </button>
            </div>
          </div>

          <label className="file-drop">
            <input type="file" accept=".csv,text/csv" onChange={handleFileChange} />
            <span className="file-icon">+</span>
            <span>
              <strong>{file ? file.name : 'Choose CSV file'}</strong>
              <small>{file ? `${Math.max(1, Math.round(file.size / 1024))} KB selected` : 'CSV upload, processed asynchronously'}</small>
            </span>
          </label>

          <label className="field">
            <span>Natural-language pattern</span>
            <textarea value={prompt} onChange={(event) => setPrompt(event.target.value)} rows={4} />
          </label>

          <label className="field">
            <span>Replacement value</span>
            <input value={replacement} onChange={(event) => setReplacement(event.target.value)} />
          </label>

          <div className="field">
            <span>Target columns</span>
            {columns.length ? (
              <div className="column-grid">
                {columns.map((column) => (
                  <button
                    type="button"
                    key={column}
                    className={selectedColumns.includes(column) ? 'selected' : ''}
                    onClick={() => toggleColumn(column)}
                  >
                    {column}
                  </button>
                ))}
              </div>
            ) : (
              <input
                value={selectedColumnText}
                onChange={(event) => setSelectedColumns(splitColumns(event.target.value))}
                placeholder="Email, Phone"
              />
            )}
          </div>

          {preview && (
            <div className="regex-preview">
              <div>
                <span>Generated regex</span>
                <code>{preview.pattern}</code>
              </div>
              <strong>{preview.cached ? 'Cached' : preview.source}</strong>
            </div>
          )}

          {formError && <div className="error-box">{formError}</div>}

          <div className="actions">
            <button type="button" className="secondary" onClick={handlePreviewRegex} disabled={previewing || !prompt.trim()}>
              {previewing ? 'Generating...' : 'Preview regex'}
            </button>
            <button type="submit" disabled={submitting}>
              {submitting ? 'Starting...' : 'Start job'}
            </button>
          </div>
        </form>

        <section className="panel status-panel">
          <JobStatus job={job} onCancel={handleCancel} />
          <JobHistory jobs={jobs} onSelect={setJob} activeId={job?.id} />
        </section>
      </section>

      <ResultsPanel job={job} />
      <RegexSandbox />
    </main>
  )
}

function JobStatus({ job, onCancel }) {
  const progress = job?.progress || 0
  const canCancel = job && !TERMINAL_STATUSES.has(job.status)

  return (
    <div className="status-block">
      <div className="panel-title">
        <h2>Current Job</h2>
        {job && <span className={`status-pill ${job.status}`}>{statusLabel(job.status)}</span>}
      </div>
      {job ? (
        <>
          <div className="job-summary">
            <span>#{job.id}</span>
            <strong>{job.natural_language_prompt || job.pattern}</strong>
          </div>
          <div className="progress-rail">
            <div style={{ width: `${progress}%` }} />
          </div>
          <div className="status-meta">
            <span>{progress}% complete</span>
            <span>{job.task_id ? `Task ${job.task_id.slice(0, 8)}` : 'Task pending'}</span>
          </div>
          {job.error_message && <div className="error-box">{job.error_message}</div>}
          {canCancel && (
            <button type="button" className="secondary full" onClick={onCancel}>
              Cancel job
            </button>
          )}
        </>
      ) : (
        <p className="muted">Start a job to see live status and progress here.</p>
      )}
    </div>
  )
}

function JobHistory({ jobs, onSelect, activeId }) {
  return (
    <div className="history-block">
      <h3>Recent Jobs</h3>
      {jobs.length ? (
        <div className="history-list">
          {jobs.map((item) => (
            <button key={item.id} type="button" className={item.id === activeId ? 'active' : ''} onClick={() => onSelect(item)}>
              <span>#{item.id}</span>
              <strong>{statusLabel(item.status)}</strong>
            </button>
          ))}
        </div>
      ) : (
        <p className="muted">No submitted jobs yet.</p>
      )}
    </div>
  )
}

function ResultsPanel({ job }) {
  const [rows, setRows] = useState([])
  const [columns, setColumns] = useState([])
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    setPage(1)
    setRows([])
    setColumns([])
    setTotalPages(0)
  }, [job?.id])

  useEffect(() => {
    if (job?.status !== 'succeeded') return undefined
    let ignore = false
    setLoading(true)
    setError('')
    fetchResultPage(job.id, page, PAGE_SIZE)
      .then((payload) => {
        if (ignore) return
        setRows(payload.rows || [])
        setColumns(payload.columns || [])
        setTotalPages(payload.total_pages || 0)
      })
      .catch((nextError) => {
        if (!ignore) setError(nextError.message)
      })
      .finally(() => {
        if (!ignore) setLoading(false)
      })
    return () => {
      ignore = true
    }
  }, [job, page])

  const metadata = job?.result?.metadata || {}

  return (
    <section className="panel results-panel">
      <div className="panel-title">
        <h2>Processed Data</h2>
        {metadata.regex_source && <span className="source-tag">{metadata.regex_source}</span>}
      </div>
      {job?.status === 'succeeded' ? (
        <>
          <div className="result-metrics">
            <span>{metadata.rows ? `${metadata.rows} rows processed` : `${rows.length} preview rows`}</span>
            <span>{metadata.engine || 'engine unknown'}</span>
            {job.pattern && <code>{job.pattern}</code>}
          </div>
          {error && <div className="error-box">{error}</div>}
          <div className="table-wrap">
            <table>
              <thead>
                <tr>{columns.map((column) => <th key={column}>{column}</th>)}</tr>
              </thead>
              <tbody>
                {rows.map((row, index) => (
                  <tr key={`${page}-${index}`}>
                    {columns.map((column) => <td key={column}>{String(row[column] ?? '')}</td>)}
                  </tr>
                ))}
              </tbody>
            </table>
            {!loading && !rows.length && <p className="muted empty">No rows returned for this page.</p>}
          </div>
          <div className="pager">
            <button type="button" className="secondary" disabled={page <= 1} onClick={() => setPage((value) => value - 1)}>
              Previous
            </button>
            <span>Page {totalPages ? page : 0} of {totalPages}</span>
            <button
              type="button"
              className="secondary"
              disabled={!totalPages || page >= totalPages}
              onClick={() => setPage((value) => value + 1)}
            >
              Next
            </button>
          </div>
        </>
      ) : (
        <p className="muted">Completed output appears here with pagination.</p>
      )}
    </section>
  )
}

function RegexSandbox() {
  const [text, setText] = useState('Order 123 and order 456')
  const [pattern, setPattern] = useState('\\d+')
  const [replacement, setReplacement] = useState('#')
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')

  async function runSandbox(event) {
    event.preventDefault()
    setError('')
    try {
      setResult(await regexReplace({ text, pattern, replacement }))
    } catch (nextError) {
      setError(nextError.message)
    }
  }

  return (
    <section className="panel sandbox-panel">
      <div className="panel-title">
        <h2>Regex Sandbox</h2>
      </div>
      <form onSubmit={runSandbox} className="sandbox-grid">
        <label className="field">
          <span>Sample text</span>
          <textarea rows={3} value={text} onChange={(event) => setText(event.target.value)} />
        </label>
        <label className="field">
          <span>Pattern</span>
          <input value={pattern} onChange={(event) => setPattern(event.target.value)} />
        </label>
        <label className="field">
          <span>Replacement</span>
          <input value={replacement} onChange={(event) => setReplacement(event.target.value)} />
        </label>
        <button type="submit">Run</button>
      </form>
      {error && <div className="error-box">{error}</div>}
      {result && (
        <div className="sandbox-result">
          <span>{result.match_count} matches</span>
          <code>{result.result}</code>
        </div>
      )}
    </section>
  )
}
