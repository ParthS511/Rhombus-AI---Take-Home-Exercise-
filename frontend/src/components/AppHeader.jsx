export default function AppHeader({ backendStatus }) {
  const label =
    backendStatus === 'online'
      ? 'API online'
      : backendStatus === 'offline'
        ? 'API offline'
        : 'checking API'

  return (
    <header className="app-header">
      <div className="brand-lockup">
        <span className="brand-mark" aria-hidden="true" />
        <div>
          <strong>Rhombus AI</strong>
          <small>Regex replacement workspace</small>
        </div>
      </div>

      <div className="header-right">
        <span className="worker-chip">Celery + Redis + Spark</span>
        <div className={`health health-${backendStatus}`}>
          <span aria-hidden="true" />
          {label}
        </div>
      </div>
    </header>
  )
}
