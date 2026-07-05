import React, {useEffect, useState} from 'react'
import { fetchResultPage } from '../api'

export default function ResultsTable({jobId,meta}){
  const [rows,setRows] = useState([])
  const [cols,setCols] = useState([])
  const [page,setPage] = useState(1)
  const [totalPages,setTotalPages] = useState(1)

  useEffect(()=>{ load(page) },[jobId,page])

  async function load(p){
    try{
      const data = await fetchResultPage(jobId,p,50)
      setRows(data.rows || [])
      setCols(data.columns || (data.rows && data.rows.length ? Object.keys(data.rows[0]) : []))
      setTotalPages(data.total_pages || 1)
    }catch(err){
      console.error(err)
    }
  }

  return (
    <div>
      <div className="result-meta">Estimated rows: {meta.rows}</div>
      <table className="result-table">
        <thead>
          <tr>{cols.map(c=> <th key={c}>{c}</th>)}</tr>
        </thead>
        <tbody>
          {rows.map((r,idx)=> (
            <tr key={idx}>{cols.map(c=> <td key={c}>{r[c]}</td>)}</tr>
          ))}
        </tbody>
      </table>

      <div className="pager">
        <button onClick={()=>setPage(p=>Math.max(1,p-1))} disabled={page===1}>Prev</button>
        <span>Page {page} / {totalPages}</span>
        <button onClick={()=>setPage(p=>Math.min(totalPages,p+1))} disabled={page===totalPages}>Next</button>
      </div>
    </div>
  )
}
