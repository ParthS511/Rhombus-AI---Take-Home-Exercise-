import React, {useEffect, useState} from 'react'
import { getJob } from '../api'

export default function JobStatus({jobId,onComplete}){
  const [status, setStatus] = useState(null)
  const [progress, setProgress] = useState(0)
  const [error, setError] = useState(null)

  useEffect(()=>{
    let mounted = true
    let timer = null
    async function poll(){
      try{
        const data = await getJob(jobId)
        if(!mounted) return
        setStatus(data.status)
        setProgress(data.progress || 0)
        if(data.status==='SUCCESS'){
          onComplete && onComplete({rows:data.result_sample_count || 0})
          return
        }
        if(data.status==='FAILED'){
          setError(data.error || 'Task failed')
          return
        }
      }catch(err){
        setError(err.message)
      }
      timer = setTimeout(poll,2000)
    }
    poll()
    return ()=>{mounted=false; timer && clearTimeout(timer)}
  },[jobId,onComplete])

  return (
    <div className="card">
      <h3>Job Status</h3>
      {error ? <div className="err">{error}</div> : (
        <>
          <div className="status">{status || 'QUEUED'}</div>
          <div className="progress">
            <div className="bar" style={{width:`${progress}%`}} />
          </div>
          <div className="meta">{progress}%</div>
        </>
      )}
    </div>
  )
}
