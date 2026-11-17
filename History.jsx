import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useLoad } from '../hooks'
import { api } from '../api'

export default function History() {
  const [list, reload] = useLoad(() => api.get('/timetables'))
  const [sel, setSel] = useState([]), [cmp, setCmp] = useState(null), nav = useNavigate()
  if (!list) return <div className="text-mute">Loading…</div>
  const pick = (id) => setSel((s) => s.includes(id) ? s.filter((x) => x !== id) : [...s.slice(-1), id])
  const act = async (fn) => { await fn(); reload() }
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-extrabold">🕘 Timetable History</h1>
      <div className="flex gap-2 items-center"><button className="btn" disabled={sel.length !== 2} onClick={async () => setCmp(await api.get(`/timetables/compare?a=${sel[0]}&b=${sel[1]}`))}>⚖ Compare selected ({sel.length}/2)</button></div>
      {cmp && <div className="card"><div className="flex justify-between"><b>{cmp.a.name} → {cmp.b.name}</b><button onClick={() => setCmp(null)}>✕</button></div>
        <div className="text-sm text-mute mb-2">{cmp.changed_periods} periods differ between the two schedules</div>
        <table className="w-full"><thead><tr><th className="th">Metric</th><th className="th">A</th><th className="th">B</th><th className="th">Δ</th></tr></thead>
          <tbody>{cmp.diff.map((r) => <tr key={r.metric}><td className="td capitalize">{r.metric.replace('_', ' ')}</td><td className="td">{r.a}</td><td className="td">{r.b}</td>
            <td className={`td font-bold ${r.delta > 0 ? 'text-ok' : r.delta < 0 ? 'text-bad' : ''}`}>{r.delta > 0 ? '+' : ''}{r.delta}</td></tr>)}</tbody></table></div>}
      <div className="card overflow-x-auto"><table className="w-full"><thead><tr>{['', 'Version', 'Name', 'Profile', 'Score', 'Created', 'Status', ''].map((h, i) => <th key={i} className="th">{h}</th>)}</tr></thead>
        <tbody>{list.map((t) => (
          <tr key={t.id}><td className="td"><input type="checkbox" checked={sel.includes(t.id)} onChange={() => pick(t.id)} /></td>
            <td className="td">v{t.version}.{t.rank}</td><td className="td">{t.name}</td><td className="td">{t.params.profile}</td>
            <td className="td font-bold">{t.score.overall}%</td><td className="td">{new Date(t.created_at + 'Z').toLocaleString()}</td>
            <td className="td">{t.is_active ? <span className="badge bg-ok text-white">ACTIVE</span> : t.status === 'best' ? <span className="badge bg-accent text-white">BEST</span> : ''}</td>
            <td className="td whitespace-nowrap space-x-1">
              <button className="btn-ghost !py-0.5" onClick={() => nav('/timetable?tid=' + t.id)}>View</button>
              <button className="btn-ghost !py-0.5" onClick={() => act(() => api.post(`/timetables/${t.id}/activate`))}>Activate</button>
              <button className="btn-ghost !py-0.5" onClick={() => act(() => api.post(`/timetables/${t.id}/restore`))}>Restore</button>
              <button className="btn-ghost !py-0.5 text-bad" onClick={() => confirm('Delete this version?') && act(() => api.del('/timetables/' + t.id))}>🗑</button></td></tr>))}</tbody></table>
        {!list.length && <div className="p-4 text-mute">Nothing saved yet.</div>}</div>
    </div>)
}
