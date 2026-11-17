import { useState } from 'react'
import { api, getUser } from '../api'
import { useLoad } from '../hooks'
import TimetableView from '../components/TimetableView'

export default function StudentPortal() {
  const u = getUser(), [tab, setTab] = useState('tt'), [q, setQ] = useState('')
  const [tt] = useLoad(() => api.get('/me/timetable')), [pr] = useLoad(() => api.get('/me/proctor'))
  const [dir] = useLoad(() => api.get('/faculty-directory')), [cal] = useLoad(() => api.get('/calendar'))
  const subs = []
  const seen = new Set()
  ;(tt?.entries || []).forEach((e) => { if (!seen.has(e.subject_id)) { seen.add(e.subject_id); subs.push(e) } })
  const match = (s) => s.toLowerCase().includes(q.toLowerCase())
  const sectionId = tt?.entries?.[0]?.section_id
  return (
    <div className="space-y-4">
      <div><h1 className="text-2xl font-extrabold">🎓 Welcome, {u.full_name}</h1>{pr && <div className="text-sm text-mute">{pr.student.roll_no} · Reg {pr.student.reg_no} · Section {pr.student.section} ({pr.student.batch})</div>}</div>
      <div className="flex gap-1 flex-wrap">{[['tt', 'Timetable'], ['sub', 'Subjects'], ['fac', 'Faculty info'], ['proc', 'My proctor'], ['exam', 'Exams']].map(([k, l]) => <button key={k} className={tab === k ? 'btn' : 'btn-ghost'} onClick={() => setTab(k)}>{l}</button>)}</div>
      {tab === 'tt' && tt && (sectionId ? <div className="card"><TimetableView fixed={{ section_id: sectionId }} entries={tt.entries} /></div> : <div className="card text-mute">No timetable published yet.</div>)}
      {tab === 'sub' && <div className="card"><input className="inp max-w-xs mb-3" placeholder="Search subjects…" value={q} onChange={(e) => setQ(e.target.value)} />
        <table className="w-full"><thead><tr>{['Code', 'Subject', 'Faculty', 'Type'].map((h) => <th key={h} className="th">{h}</th>)}</tr></thead>
          <tbody>{subs.filter((s) => match(s.subject + s.code + s.faculty)).map((s) => <tr key={s.subject_id}><td className="td">{s.code}</td><td className="td">{s.subject}</td><td className="td">{s.faculty}</td><td className="td">{s.is_lab ? 'Lab' : 'Theory'}</td></tr>)}</tbody></table></div>}
      {tab === 'fac' && <div className="card"><input className="inp max-w-xs mb-3" placeholder="Search faculty or subject…" value={q} onChange={(e) => setQ(e.target.value)} />
        <div className="grid md:grid-cols-2 gap-2">{(dir || []).filter((f) => match(f.name + f.subjects.join(' '))).map((f) => <div key={f.id} className="bg-bg rounded-lg p-3 text-sm"><b>{f.name}</b> <span className="text-mute">· {f.designation}</span>
          <div className="text-mute">{f.email}</div>{f.subjects.length > 0 && <div>Teaches: {f.subjects.join(', ')}</div>}</div>)}</div></div>}
      {tab === 'proc' && pr && <div className="card space-y-3">
        {pr.proctor ? <div><div className="text-xs text-mute">Proctor</div><div className="font-bold text-lg">{pr.proctor.name}</div><div className="text-sm">{pr.proctor.email} · {pr.proctor.phone}</div></div> : <div>No proctor assigned</div>}
        <div><div className="font-semibold mb-1">Proctor meeting cycles</div>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-2">{[1, 2, 3, 4, 5].map((n) => { const c = pr.cycles.find((x) => x.cycle === n); return <div key={n} className="bg-bg rounded-lg p-3 text-center"><div className="text-xs text-mute">Cycle {n}</div><div className="font-bold">{c ? new Date(c.date).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' }) : 'Not scheduled'}</div></div> })}</div></div></div>}
      {tab === 'exam' && <div className="card"><h3 className="font-bold mb-2">Academic calendar</h3>{(cal || []).map((c) => <div key={c.id} className="text-sm border-b border-line py-1">{c.start_date}{c.end_date ? ` → ${c.end_date}` : ''} — {c.title}</div>)}
        <p className="text-xs text-mute mt-2">Detailed exam timetables are a planned future enhancement.</p></div>}
    </div>)
}
