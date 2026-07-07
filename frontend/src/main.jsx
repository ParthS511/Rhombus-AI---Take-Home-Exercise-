import React from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import './index.css'

class AppErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { error: null }
  }

  static getDerivedStateFromError(error) {
    return { error }
  }

  componentDidCatch(error) {
    console.error(error)
  }

  render() {
    if (this.state.error) {
      return (
        <main className="app-shell boot-shell">
          <header className="app-header">
            <div className="brand-lockup">
              <span className="brand-mark" aria-hidden="true" />
              <strong>lattice</strong>
            </div>
            <div className="health health-offline">
              <span aria-hidden="true" />
              app error
            </div>
          </header>
          <section className="boot-panel">
            <h1>React failed to render.</h1>
            <p>{this.state.error.message}</p>
          </section>
        </main>
      )
    }

    return this.props.children
  }
}

const root = createRoot(document.getElementById('root'))
root.render(
  <AppErrorBoundary>
    <App />
  </AppErrorBoundary>,
)
