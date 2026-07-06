import { useMemo } from 'react'

import { splitColumns } from '../utils/csv'

export default function JobForm({
  columns,
  engine,
  file,
  formError,
  onFileChange,
  onPreviewRegex,
  onSubmit,
  onToggleColumn,
  preview,
  previewing,
  prompt,
  replacement,
  selectedColumns,
  setEngine,
  setPrompt,
  setReplacement,
  setSelectedColumns,
  submitting,
}) {
  const selectedColumnText = useMemo(() => selectedColumns.join(', '), [selectedColumns])
  const fileSize = file ? `${Math.max(1, Math.round(file.size / 1024))} KB` : 'CSV upload'

  return (
    <form className="panel job-panel" onSubmit={onSubmit}>
      <div className="panel-title">
        <div>
          <span className="section-kicker">configure</span>
          <h2>Regex pipeline</h2>
        </div>
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
        <input type="file" accept=".csv,text/csv" onChange={onFileChange} />
        <span className="file-icon" aria-hidden="true">+</span>
        <span>
          <strong>{file ? file.name : 'Choose CSV file'}</strong>
          <small>{file ? `${fileSize} selected` : 'processed asynchronously in the backend'}</small>
        </span>
      </label>

      <label className="field">
        <span>describe the pattern</span>
        <textarea value={prompt} onChange={(event) => setPrompt(event.target.value)} rows={4} />
      </label>

      <div className="form-grid">
        <div className="field">
          <span>target column</span>
          {columns.length ? (
            <div className="column-grid">
              {columns.map((column) => (
                <button
                  type="button"
                  key={column}
                  className={selectedColumns.includes(column) ? 'selected' : ''}
                  onClick={() => onToggleColumn(column)}
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

        <label className="field">
          <span>replacement value</span>
          <input value={replacement} onChange={(event) => setReplacement(event.target.value)} />
        </label>
      </div>

      {preview && (
        <div className="regex-preview">
          <span className="bolt" aria-hidden="true">*</span>
          <div>
            <span>{preview.cached ? 'pattern cached' : 'pattern generated'}</span>
            <code>{preview.pattern}</code>
          </div>
          <strong>{preview.cached ? 'Cached' : preview.source}</strong>
        </div>
      )}

      {formError && <div className="error-box">{formError}</div>}

      <div className="actions">
        <button type="button" className="secondary" onClick={onPreviewRegex} disabled={previewing || !prompt.trim()}>
          {previewing ? 'Generating...' : 'Preview regex'}
        </button>
        <button type="submit" disabled={submitting}>
          {submitting ? 'Starting...' : 'Run pipeline'}
        </button>
      </div>
    </form>
  )
}
