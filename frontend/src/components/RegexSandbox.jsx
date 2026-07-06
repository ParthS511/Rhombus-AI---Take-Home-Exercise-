import { useState } from 'react'

import { regexReplace } from '../api'

export default function RegexSandbox() {
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
        <h2>$ regex sandbox</h2>
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
