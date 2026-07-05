import React, {useState} from 'react'
import UploadForm from './components/UploadForm'
import JobStatus from './components/JobStatus'
import ResultsTable from './components/ResultsTable'

export default function App(){
  const [jobId, setJobId] = useState(null)
  const [completedMeta, setCompletedMeta] = useState(null)

  return (
    <div className="app-root">
      <header className="topbar">
        <div className="brand">Rhombus AI</div>
        <nav className="nav">
          <span>Upload</span>
          <span>Jobs</span>
        </nav>
      </header>

      <main className="container">
        <section className="left">
          <UploadForm onJobCreated={(id)=>{setJobId(id); setCompletedMeta(null)}} />
          {jobId && <JobStatus jobId={jobId} onComplete={(meta)=>{setCompletedMeta(meta)}} />}
        </section>

        <section className="right">
          <div className="card">
            <h2>Processed Result</h2>
            {completedMeta ? (
              <ResultsTable jobId={jobId} meta={completedMeta} />
            ) : (
              <div className="placeholder">Results will appear here after job completes.</div>
            )}
          </div>
        </section>
      </main>
    </div>
  )
}
