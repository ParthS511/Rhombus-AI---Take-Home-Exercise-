import { TERMINAL_STATUSES, statusLabel } from '../constants'

export default function JobStatus({ job, onCancel }) {
  const progress = job?.progress || 0
  const canCancel = job && !TERMINAL_STATUSES.has(job.status)
  const rowsProcessed = job?.result?.metadata?.rows || (progress ? Math.round(progress * 1200) : 0)

  return (
    <div className="status-block">
      <div className="panel-title">
        <div>
          <span className="section-kicker">{job ? `job_${String(job.id).padStart(4, '0')}` : 'job_idle'}</span>
          <h2>Live progress</h2>
        </div>
        {job && <span className={`status-pill ${job.status}`}>{statusLabel(job.status)}</span>}
      </div>
      {job ? (
        <>
          <div className="progress-rail">
            <div style={{ width: `${progress}%` }} />
          </div>
          <div className="status-meta">
            <span>{rowsProcessed.toLocaleString()} rows touched</span>
            <span>{progress}% complete</span>
          </div>
          <div className="stats-grid">
            <div>
              <span>engine</span>
              <strong>{job.result?.metadata?.engine || 'spark'}</strong>
            </div>
            <div>
              <span>task</span>
              <strong>{job.task_id ? job.task_id.slice(0, 6) : 'queued'}</strong>
            </div>
            <div>
              <span>matches</span>
              <strong>{job.result?.metadata?.match_count ?? '--'}</strong>
            </div>
          </div>
          <div className="job-summary">
            <span>prompt</span>
            <strong>{job.natural_language_prompt || job.pattern}</strong>
          </div>
          {job.error_message && <div className="error-box">{job.error_message}</div>}
          {canCancel && (
            <button type="button" className="secondary full" onClick={onCancel}>
              Cancel job
            </button>
          )}
        </>
      ) : (
        <>
          <div className="progress-rail">
            <div style={{ width: '0%' }} />
          </div>
          <div className="status-meta">
            <span>waiting for dataset</span>
            <span>0% complete</span>
          </div>
          <div className="stats-grid">
            <div>
              <span>partitions</span>
              <strong>--</strong>
            </div>
            <div>
              <span>throughput</span>
              <strong>--</strong>
            </div>
            <div>
              <span>matches</span>
              <strong>--</strong>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
