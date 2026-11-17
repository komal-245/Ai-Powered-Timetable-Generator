import { useEffect, useState } from 'react'
import { api } from '../api'
import { useMeta } from '../hooks'

export default function Rooms() {
  const meta = useMeta(), [rooms, setRooms] = useState([]), [id, setId] = useState(null), [s, setS] = useState(null)
  useEffect(() => { api.get('/rooms').then((r) => { setRooms(r); setId(r[0]?.id) }) }, [])
  useEffect(() => { if (id) api.get(`/rooms/${id}/status`).then(setS) }, [id])
  const occ = new Set((s?.schedule || []).map((x) => `${x.day}-${x.slot}`))
  const at = (d, t) => s?.schedule.find((x) => x.day === d && x.slot === t)
  const line = (x) => x ? `${meta?.days[x.day]} ${meta?.slots[x.slot].start} · ${x.subject} · ${x.section} · ${x.faculty}` : null
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-extrabold">🏫 Classroom Portal</h1>
      <select className="inp !w-auto" value={id || ''} onChange={(e) => setId(+e.target.value)}>{rooms.map((r) => <option key={r.id} value={r.id}>{r.name} {r.is_lab ? '(Lab)' : ''} — cap {r.capacity}</option>)}</select>
      {s && meta && <>
        <div className="grid md:grid-cols-3 gap-3">
          <div className="card"><div className="text-xs text-mute">Current class</div><div className="font-bold">{s.current ? `${s.current.subject} (${s.current.section})` : 'Free right now'}</div></div>
          <div className="card"><div className="text-xs text-mute">Upcoming</div>{s.upcoming.length ? s.upcoming.slice(0, 3).map((u, i) => <div key={i} className="text-sm">{line(u)}</div>) : <div className="text-sm">Nothing more this week</div>}</div>
          <div className="card"><div className="text-xs text-mute">Weekly occupancy</div><div className="text-3xl font-extrabold text-accent">{s.occupancy_pct}%</div><div className="text-xs text-mute">{s.free_slots.length} free periods</div></div>
        </div>
        <div className="card overflow-x-auto"><h3 className="font-bold mb-2">Weekly occupancy (red = occupied, green = free)</h3>
          <table className="border-separate border-spacing-1 text-xs"><thead><tr><th />{meta.slots.map((x, i) => <th key={i} className="text-mute">P{i + 1}<div>{x.start}</div></th>)}</tr></thead>
            <tbody>{meta.days.map((dn, d) => <tr key={d}><td className="font-semibold pr-2">{dn}</td>{meta.slots.map((_, t) => {
              const x = at(d, t); return <td key={t} title={x ? `${x.subject} · ${x.faculty}` : 'Free'} className={`w-24 h-10 rounded text-center ${x ? 'bg-bad/20 text-bad' : 'bg-ok/20 text-ok'}`}>{x ? <>{x.section}<div className="truncate w-20 mx-auto">{x.subject}</div></> : 'free'}</td>
            })}</tr>)}</tbody></table></div></>}
    </div>)
}
