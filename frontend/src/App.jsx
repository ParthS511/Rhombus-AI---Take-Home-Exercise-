import React, { useEffect, useMemo, useState } from 'react'

import { cancelJob, createJob, generateRegex, getJob, healthCheck } from './api'
import AppHeader from './components/AppHeader'
import JobForm from './components/JobForm'
import JobHistory from './components/JobHistory'
import JobStatus from './components/JobStatus'
import RegexSandbox from './components/RegexSandbox'
import ResultsPanel from './components/ResultsPanel'
import { TERMINAL_STATUSES } from './constants'
import { parseCsvHeader } from './utils/csv'

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
      setPreview(await generateRegex(prompt))
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
      <AppHeader backendStatus={backendStatus} />

      <section className="workspace">
        <JobForm
          columns={columns}
          engine={engine}
          file={file}
          formError={formError}
          onFileChange={handleFileChange}
          onPreviewRegex={handlePreviewRegex}
          onSubmit={handleSubmit}
          onToggleColumn={toggleColumn}
          preview={preview}
          previewing={previewing}
          prompt={prompt}
          replacement={replacement}
          selectedColumns={selectedColumns}
          setEngine={setEngine}
          setPrompt={setPrompt}
          setReplacement={setReplacement}
          setSelectedColumns={setSelectedColumns}
          submitting={submitting}
        />

        <section className="panel status-panel">
          <div className="command-label">$ job status</div>
          <JobStatus job={job} onCancel={handleCancel} />
          <JobHistory jobs={jobs} onSelect={setJob} activeId={job?.id} />
        </section>
      </section>

      <ResultsPanel job={job} />
      <RegexSandbox />
    </main>
  )
}
