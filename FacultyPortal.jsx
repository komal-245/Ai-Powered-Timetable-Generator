import { useEffect, useState } from 'react'
import { api, download, getUser } from '../api'
import { useLoad, useMeta } from '../hooks'
import { ChartBox, Bar } from '../components/Charts'
import TimetableView from '../components/TimetableView'

function CellPicker({ meta, value, onChange, tone }) {
  const has = (d, t) => value.some(([a, b]) => a === d && b === t)
  const tog = (d, t) => onChange(has(d, t) ? value.filter(([a, b]) => !(a === d && b === t)) : [...value, [d, t]])
  return (
    <table className="border-separate border-spacing-1 text-xs"><thead><tr><th />{meta.slots.map((s, i) => <th key={i} className="text-mute">P{i + 1}</th>)}</tr></thead>
      <tbody>{meta.days.map((dn, d) => <tr key={d}><td className="pr-2 font-semibold">{dn}</td>{meta.slots.map((_, t) =>
        <td key={t} onClick={() => tog(d, t)} className={`w-10 h-8 rounded cursor-pointer text-center border border-line ${has(d, t) ? tone : 'bg-card'}`}>{has(d, t) ? '✓' : ''}</td>)}</tr>)}</tbody></table>)
}

function Prefs() {
  const meta = useMeta(), [p, , , setP] = useLoad(() => api.get('/me/preferences')), [saved, setSaved] = useState(false)
  if (!p || !meta) return null
  const save = async () => { await api.put('/me/preferences', p); setSaved(true); setTimeout(() => setSaved(false), 2000) }
  return (
    <div className="card space-y-4">
      <p className="text-sm text-mute">The AI scheduler tries to satisfy these (soft) preferences. “Unavailable” periods are treated as hard constraints.</p>
      <div className="grid md:grid-cols-3 gap-4">
        <label className="text-sm">Preferred shift<select className="inp" value={p.shift} onChange={(e) => setP({ ...p, shift: e.target.value })}><option value="any">No preference</option><option value="morning">Morning</option><option value="afternoon">Afternoon</option></select></label>
        <label className="text-sm">Max classes per day<input type="number" min="1" max="7" className="inp" value={p.max_per_day} onChange={(e) => setP({ ...p, max_per_day: +e.target.value })} /></label>
        <div className="text-sm">Avoid days<div className="flex gap-2 flex-wrap mt-1">{meta.days.map((dn, d) => <label key={d}><input type="checkbox" checked={p.no_days.includes(d)} onChange={() => setP({ ...p, no_days: p.no_days.includes(d) ? p.no_days.filter((x) => x !== d) : [...p.no_days, d] })} /> {dn}</label>)}</div></div>
      </div>
      <div className="grid lg:grid-cols-2 gap-4 overflow-x-auto">
        <div><div className="text-sm font-semibold mb-1">Preferred free periods</div><CellPicker meta={meta} value={p.free_slots} onChange={(v) => setP({ ...p, free_slots: v })} tone="bg-ok/30" /></div>
        <div><div className="text-sm font-semibold mb-1">Unavailable (hard)</div><CellPicker meta={meta} value={p.unavailable} onChange={(v) => setP({ ...p, unavailable: v })} tone="bg-bad/30" /></div>
      </div>
      <button className="btn" onClick={save}>Save preferences</button>{saved && <span className="ml-3 text-ok text-sm">✓ Saved — applied the next time a timetable is generated</span>}
    </div>)
}

export default function FacultyPortal() {
  const u = getUser(), [tab, setTab] = useState('tt')
  const [tt] = useLoad(() => api.get('/me/timetable')), [w] = useLoad(() => api.get('/me/workload')), [n] = useLoad(() => api.get('/notifications'))
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-extrabold">👩‍🏫 Welcome, {u.full_name}</h1>
      <div className="flex gap-1 flex-wrap">{[['tt', 'My timetable'], ['wl', 'Workload'], ['pref', 'Preferences'], ['nt', 'Notifications']].map(([k, l]) => <button key={k} className={tab === k ? 'btn' : 'btn-ghost'} onClick={() => setTab(k)}>{l}</button>)}</div>
      {tab === 'tt' && <>{tt?.timetable && <div className="text-xs text-mute">Timetable: {tt.timetable}</div>}
        {tt && <div className="card"><TimetableView fixed={{ faculty_id: u.faculty_id }} entries={tt.entries} /></div>}</>}
      {tab === 'wl' && w && <div className="grid md:grid-cols-2 gap-4">
        <div className="card"><h3 className="font-bold mb-2">Weekly load</h3><Bar label={`${w.hours} of ${w.faculty.max_hours} periods`} value={Math.round(100 * w.hours / w.faculty.max_hours)} color={w.hours > w.faculty.max_hours ? 'bad' : 'accent'} />
          <ChartBox labels={w.days} datasets={[{ label: 'Periods', data: w.per_day }]} height={200} /></div>
        <div className="card overflow-x-auto"><h3 className="font-bold mb-2">Subjects handled</h3><table className="w-full"><thead><tr><th className="th">Code</th><th className="th">Subject</th><th className="th">Section</th><th className="th">Periods</th></tr></thead>
          <tbody>{w.subjects.map((s, i) => <tr key={i}><td className="td">{s.code}</td><td className="td">{s.name}</td><td className="td">{s.section}</td><td className="td">{s.periods}</td></tr>)}</tbody></table></div></div>}
      {tab === 'pref' && <Prefs />}
      {tab === 'nt' && <div className="card space-y-2">{(n || []).map((x, i) => <div key={i} className="text-sm border-b border-line pb-1">{x.message}<span className="text-mute text-xs ml-2">{new Date(x.created_at + 'Z').toLocaleString()}</span></div>)}{n?.length === 0 && 'No notifications'}</div>}
    </div>)
}
