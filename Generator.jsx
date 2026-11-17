import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import { useMeta } from '../hooks'
import { ScorePanel } from '../components/Charts'

export default function Generator() {
  const meta = useMeta(), nav = useNavigate()
  const [n, setN] = useState(5), [tl, setTl] = useState(10), [block, setBlock] = useState({})   // block["4-pm"]=true
  const [job, setJob] = useState(null), [cands, setCands] = useState([]), [err, setErr] = useState('')
  const timer = useRef()
  useEffect(() => () => clearInterval(timer.current), [])

  const toggle = (k) => setBlock({ ...block, [k]: !block[k] })
  const blocked = () => (meta?.days || []).map((_, d) => {
   const slots = [...(block[`${d}-am`] ? [0, 1, 2] : []), ...(block[`${d}-pm`] ? [3, 4] : [])]
    return { day: d, slots }
  }).filter((b) => b.slots.length)

  const poll = (id) => {
    clearInterval(timer.current)
    timer.current = setInterval(async () => {
      const j = await api.get('/timetables/jobs/' + id).catch(() => null)
      if (!j) return
      setJob(j)
      if (j.status !== 'running') {
        clearInterval(timer.current)
        if (j.status === 'done') setCands(await Promise.all(j.timetable_ids.map((i) => api.get('/timetables/' + i))))
      }
    }, 2000)
  }
  const start = async () => {
    setErr(''); setCands([])
    try { const r = await api.post('/timetables/generate', { candidates: n, time_limit: tl, blocked: blocked() }); setJob({ status: 'running', progress: 0, total: n, message: 'Starting…', warnings: [] }); poll(r.job_id) }
    catch (e) { setErr(e.message) }
  }
  const activate = async (id) => { await api.post(`/timetables/${id}/activate`); nav('/timetable?tid=' + id) }

  return (
    <div className="space-y-5">
      <h1 className="text-2xl font-extrabold">🧠 AI Scheduling Engine</h1>
      <div className="card grid md:grid-cols-3 gap-4">
        <div className="space-y-3">
          <label className="block text-sm">Candidate timetables (1–10)<input type="number" min="1" max="10" className="inp" value={n} onChange={(e) => setN(+e.target.value)} /></label>
          <label className="block text-sm">Time limit per candidate (seconds)<input type="number" min="2" max="60" className="inp" value={tl} onChange={(e) => setTl(+e.target.value)} /></label>
          <p className="text-xs text-mute">Engine: Google OR-Tools CP-SAT. Hard constraints (no teacher/room/lab overlap, required hours, continuous labs, capacity, availability) are always enforced; soft goals are optimised and each candidate is scored.</p>
        </div>
        <div className="md:col-span-2">
          <div className="text-sm font-semibold mb-1">Optional: keep these periods free (e.g. “no Friday afternoon”)</div>
          <table className="text-sm"><tbody>{(meta?.days || []).map((dn, d) => (
            <tr key={d}><td className="pr-3 font-semibold">{dn}</td>
              <td className="pr-3"><label><input type="checkbox" checked={!!block[`${d}-am`]} onChange={() => toggle(`${d}-am`)} /> Morning</label></td>
              <td><label><input type="checkbox" checked={!!block[`${d}-pm`]} onChange={() => toggle(`${d}-pm`)} /> Afternoon</label></td></tr>))}</tbody></table>
          <button className="btn mt-3" disabled={job?.status === 'running'} onClick={start}>{job?.status === 'running' ? 'Generating…' : '⚡ Generate timetables'}</button>
          {err && <div className="text-bad text-sm mt-2">{err}</div>}
        </div>
      </div>

      {job && <div className="card">
        <div className="flex justify-between text-sm"><b>{job.status === 'error' ? '❌ Failed' : job.status === 'done' ? '✅ Done' : '⏳ ' + job.message}</b><span>{job.progress}/{job.total}</span></div>
        <div className="h-2 bg-line rounded mt-2"><div className="h-full bg-accent rounded transition-all" style={{ width: `${100 * job.progress / job.total}%` }} /></div>
        {job.status === 'error' && <div className="text-bad text-sm mt-2">{job.message}</div>}
        {job.warnings?.map((w, i) => <div key={i} className="text-warn text-sm mt-1">⚠ {w}</div>)}
      </div>}

      {cands.length > 0 && <div className="space-y-4">
        <h2 className="text-lg font-bold">Candidates (ranked by AI score)</h2>
        {cands.map((c, i) => (
          <div key={c.id} className={`card grid md:grid-cols-3 gap-4 ${i === 0 ? 'ring-2 ring-ok' : ''}`}>
            <div><div className="font-bold">{i === 0 && '🏆 '}{c.name}</div><div className="text-xs text-mute mb-2">profile: {c.params.profile}</div><ScorePanel score={c.score} />
              <div className="text-xs text-mute mt-2">Idle periods: {c.score.idle_periods} · Hard violations: {c.score.hard_violations}</div></div>
            <div className="md:col-span-2 flex flex-col"><div className="text-sm bg-bg rounded-lg p-3 flex-1"><b>AI explanation</b><p className="mt-1">{c.explanation}</p></div>
              <div className="mt-3 flex gap-2"><button className="btn" onClick={() => activate(c.id)}>Activate & open</button><button className="btn-ghost" onClick={() => nav('/timetable?tid=' + c.id)}>Preview</button></div></div>
          </div>))}
      </div>}
    </div>)
}
