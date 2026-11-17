import { useEffect, useState } from 'react'
import { api, download } from '../api'
import { useMeta } from '../hooks'
import Grid from './Grid'
import { ScorePanel } from './Charts'

/** Timetable viewer. If `fixed` ({faculty_id}|{section_id}) is given the selectors are hidden (portals). */
export default function TimetableView({ tid, editable = false, fixed = null, entries: given = null, mode0 = 'section' }) {
  const meta = useMeta()
  const [mode, setMode] = useState(fixed ? Object.keys(fixed)[0].replace('_id', '') : mode0)
  const [lists, setLists] = useState({ section: [], faculty: [], room: [] })
  const [id, setId] = useState(fixed ? Object.values(fixed)[0] : null)
  const [entries, setEntries] = useState(given || [])
  const [tt, setTt] = useState(null)
  const [msg, setMsg] = useState(null)             // {ok, conflicts, suggestions}
  const [conflicts, setConflicts] = useState([])
  const [gcal, setGcal] = useState(null)

  useEffect(() => {
    if (fixed) return
    Promise.all([api.get('/sections'), api.get('/faculty'), api.get('/rooms')]).then(([s, f, r]) => {
      setLists({ section: s.map((x) => ({ id: x.id, name: `Sem ${x.semester} · CSE-${x.name}` })), faculty: f.map((x) => ({ id: x.id, name: x.name })), room: r.map((x) => ({ id: x.id, name: x.name })) })
    })
  }, [])
  useEffect(() => { if (!fixed && lists[mode].length && !lists[mode].some((x) => x.id === id)) setId(lists[mode].find((x) => mode !== 'section' || /Sem 5 · CSE-B/.test(x.name))?.id || lists[mode][0].id) }, [mode, lists])
  useEffect(() => { if (tid) api.get('/timetables/' + tid).then((t) => setTt(t)) }, [tid])
  const load = () => { if (tid && id && !given) api.get(`/timetables/${tid}/view?${mode}_id=${id}`).then(setEntries) }
  useEffect(load, [tid, mode, id])
  useEffect(() => { if (given) setEntries(given) }, [given])
  const refreshTt = () => api.get('/timetables/' + tid).then(setTt)
  const q = `${mode}_id=${id}`

  const move = async (block_id, day, slot) => {
    const r = await api.post(`/timetables/${tid}/move`, { block_id, day, slot })
    setMsg({ ...r, block_id })
    if (r.ok) { load(); refreshTt() }
  }
  const check = async () => setConflicts(await api.get(`/timetables/${tid}/conflicts`))
  const name = lists[mode]?.find((x) => x.id === id)?.name || 'timetable'

  return (
    <div className="space-y-4">
      {!fixed && <div className="card flex flex-wrap gap-2 items-center">
        <select className="inp !w-auto" value={mode} onChange={(e) => { setMode(e.target.value); setId(null) }}><option value="section">By Section</option><option value="faculty">By Faculty</option><option value="room">By Room / Lab</option></select>
        <select className="inp !w-auto max-w-xs" value={id || ''} onChange={(e) => setId(+e.target.value)}>{lists[mode].map((x) => <option key={x.id} value={x.id}>{x.name}</option>)}</select>
        <div className="ml-auto flex flex-wrap gap-2">
          <button className="btn-ghost" onClick={() => download(`/reports/timetable.pdf?tid=${tid}&${q}`, `${name}.pdf`)}>⬇ PDF</button>
          <button className="btn-ghost" onClick={() => download(`/export/ics?tid=${tid}&${q}`, `${name}.ics`)}>📅 ICS</button>
          <button className="btn-ghost" onClick={async () => setGcal(await api.get(`/export/gcal-links?tid=${tid}&${q}`))}>Google Calendar</button>
          <button className="btn-ghost" onClick={() => download(`/export/xlsx?tid=${tid}`, 'timetable.xlsx')}>📊 Excel</button>
          <button className="btn-ghost" onClick={() => window.print()}>🖨 Print</button>
        </div></div>}
      {fixed && <div className="flex gap-2 justify-end">
        <button className="btn-ghost" onClick={() => download(`/reports/timetable.pdf?${q}`, 'my-timetable.pdf')}>⬇ PDF</button>
        <button className="btn-ghost" onClick={() => download(`/export/ics?${q}`, 'my-timetable.ics')}>📅 ICS</button>
        <button className="btn-ghost" onClick={async () => setGcal(await api.get(`/export/gcal-links?${q}`))}>Google Calendar</button>
        <button className="btn-ghost" onClick={() => window.print()}>🖨 Print</button></div>}

      {gcal && <div className="card"><div className="flex justify-between"><b>Add to Google Calendar</b><button onClick={() => setGcal(null)}>✕</button></div>
        <p className="text-xs text-mute mb-2">Each link opens Google Calendar with a weekly recurring event. To add everything at once, download the ICS file and import it in Google Calendar → Settings → Import.</p>
        <div className="grid md:grid-cols-2 gap-1 max-h-56 overflow-y-auto text-sm">{gcal.map((g, i) => <a key={i} className="text-accent underline" target="_blank" rel="noreferrer" href={g.url}>{g.when} — {g.title}</a>)}</div></div>}

      {editable && <div className="text-xs text-mute">💡 Drag a class tile onto another period. The engine validates teacher, room, lab and time conflicts instantly.</div>}
      {msg && !msg.ok && <div className="card border-bad">
        <div className="font-bold text-bad">Conflict found</div>
        {msg.conflicts.map((c, i) => <div key={i} className="text-sm">• {c.message}</div>)}
        {msg.suggestions?.length > 0 && <div className="mt-2"><div className="font-semibold text-sm">Suggested solution</div>
          {msg.suggestions.map((s, i) => <div key={i} className="flex items-center gap-2 text-sm py-1"><span className="flex-1">{s.text} <span className="text-mute">(score → {s.resulting_score}%)</span></span>
            <button className="btn !py-0.5" onClick={() => move(s.block_id, s.day, s.slot)}>Apply</button></div>)}</div>}
        <button className="text-xs text-mute mt-1" onClick={() => setMsg(null)}>dismiss</button></div>}
      {msg?.ok && <div className="card border-ok text-ok text-sm">✓ Moved. No conflicts — new score {msg.score?.overall}%. <button className="ml-2 text-mute" onClick={() => setMsg(null)}>dismiss</button></div>}

      <div className="card print:border-0"><Grid entries={entries} meta={meta} mode={mode} editable={editable} onMove={move} highlight={msg?.block_id} /></div>

      {!fixed && tt && <div className="grid md:grid-cols-3 gap-4">
        <div className="card"><h3 className="font-bold mb-2">{tt.name}{tt.is_active && <span className="badge bg-ok text-white ml-2">ACTIVE</span>}</h3><ScorePanel score={tt.score} /></div>
        <div className="card md:col-span-2"><h3 className="font-bold mb-1">AI explanation</h3><p className="text-sm">{tt.explanation}</p>
          <div className="mt-3 flex gap-2"><button className="btn-ghost" onClick={check}>🔍 Validate & suggest fixes</button>
            {editable && !tt.is_active && <button className="btn" onClick={async () => { await api.post(`/timetables/${tid}/activate`); refreshTt() }}>Activate</button>}</div>
          {conflicts.length === 0 && <div className="text-xs text-mute mt-2">Click “Validate” to list conflicts with AI-suggested moves.</div>}
          {conflicts.map((c, i) => <div key={i} className={`text-sm mt-1 ${c.severity === 'hard' ? 'text-bad' : 'text-warn'}`}>• {c.message}{c.suggestions?.map((s, j) => <div key={j} className="ml-4 text-accent">↳ {s.text}</div>)}</div>)}
        </div></div>}
    </div>)
}
