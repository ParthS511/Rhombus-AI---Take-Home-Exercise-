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
        <strong>lattice</strong>
        <nav className="top-tabs" aria-label="Primary">
          <span className="active">new job</span>
          <span>jobs</span>
          <span>history</span>
        </nav>
      </div>

      <div className="header-right">
        <span className="worker-chip">worker pool: 4 active</span>
        <div className={`health health-${backendStatus}`}>
          <span aria-hidden="true" />
          {label}
        </div>
      </div>
    </header>
  )
}
