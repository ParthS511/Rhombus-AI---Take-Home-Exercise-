import { useEffect, useState } from 'react'

import { fetchResultPage } from '../api'
import { PAGE_SIZE } from '../constants'

export default function ResultsPanel({ job }) {
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
  const hasRows = rows.length > 0
  const replacementValue = job?.replacement ? String(job.replacement) : 'REDACTED'

  return (
    <section className="panel results-panel">
      <div className="panel-title">
        <div>
          <span className="section-kicker">
            preview {totalPages ? `- page ${page} of ${totalPages}` : ''}
          </span>
          <h2>Processed output</h2>
        </div>
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
                    {columns.map((column) => {
                      const value = String(row[column] ?? '')
                      const isReplacement = replacementValue && value === replacementValue
                      return (
                        <td key={column}>
                          {isReplacement ? <span className="replacement-pill">{value}</span> : value}
                        </td>
                      )
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
            {!loading && !hasRows && <p className="muted empty">No rows returned for this page.</p>}
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
        <div className="empty-preview">
          <table>
            <thead>
              <tr>
                <th>id</th>
                <th>name</th>
                <th>email</th>
              </tr>
            </thead>
            <tbody>
              {['John Doe', 'Jane Smith', 'Alice Brown'].map((name, index) => (
                <tr key={name}>
                  <td>{index + 1}</td>
                  <td>{name}</td>
                  <td><span className="replacement-pill">REDACTED</span></td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="muted">Run a job to replace this sample preview with live paginated results.</p>
        </div>
      )}
    </section>
  )
}
