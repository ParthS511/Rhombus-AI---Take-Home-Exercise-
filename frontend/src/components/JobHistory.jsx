import { statusLabel } from '../constants'

export default function JobHistory({ activeId, jobs, onSelect }) {
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
