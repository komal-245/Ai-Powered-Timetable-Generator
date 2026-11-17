import { useState } from 'react'
import { useLoad } from '../hooks'
import { api } from '../api'

const SCHEMA = {
  departments: { code: '', name: '' },
  sections: { department_id: 1, semester: 5, name: '', batch: '', strength: 60, proctor_id: null },
  subjects: { code: '', name: '', department_id: 1, semester: 5, credits: 3, hours_per_week: 3, is_lab: false },
  faculty: { name: '', designation: 'Assistant Professor', phone: '', email: '', department_id: 1, max_hours_week: 16, active: true },
  rooms: { name: '', building: '', capacity: 60, is_lab: false },
  students: { roll_no: '', reg_no: '', name: '', phone: '', section_id: 1, proctor_id: null },
  calendar: { title: '', kind: 'event', start_date: '', end_date: '' },
}
const TABS = { departments: 'Departments', sections: 'Semesters & Sections', subjects: 'Subjects', faculty: 'Faculty', rooms: 'Classrooms & Labs', students: 'Students', calendar: 'Academic Calendar' }

function Form({ res, row, onClose, onSaved }) {
  const [f, setF] = useState({ ...SCHEMA[res], ...(row || {}) }), [err, setErr] = useState('')
  const save = async () => {
    try { row?.id ? await api.put(`/${res}/${row.id}`, f) : await api.post(`/${res}`, f); onSaved() } catch (e) { setErr(e.message) }
  }
  return (
    <div className="fixed inset-0 bg-black/50 z-50 grid place-items-center p-4" onClick={onClose}>
      <div className="card w-full max-w-lg max-h-[90vh] overflow-y-auto space-y-2" onClick={(e) => e.stopPropagation()}>
        <h3 className="font-bold">{row?.id ? 'Edit' : 'Add'} {TABS[res]}</h3>
        {Object.keys(SCHEMA[res]).map((k) => {
          const t = SCHEMA[res][k]
          return <label key={k} className="block text-sm"><span className="text-mute">{k.replace(/_/g, ' ')}</span>
            {typeof t === 'boolean' ? <input type="checkbox" className="ml-2" checked={!!f[k]} onChange={(e) => setF({ ...f, [k]: e.target.checked })} />
              : <input className="inp" type={typeof t === 'number' ? 'number' : k.includes('date') ? 'date' : 'text'} value={f[k] ?? ''}
                onChange={(e) => setF({ ...f, [k]: typeof t === 'number' || t === null ? (e.target.value === '' ? null : +e.target.value) : e.target.value })} />}</label>
        })}
        {err && <div className="text-bad text-sm">{err}</div>}
        <div className="flex gap-2 justify-end"><button className="btn-ghost" onClick={onClose}>Cancel</button><button className="btn" onClick={save}>Save</button></div>
      </div></div>)
}

function CanTeach({ fac, onClose }) {
  const [subs] = useLoad(() => api.get('/subjects')), [mine, , , setMine] = useLoad(() => api.get(`/faculty/${fac.id}/subjects`))
  if (!subs || !mine) return null
  const tog = (id) => setMine(mine.includes(id) ? mine.filter((x) => x !== id) : [...mine, id])
  return (
    <div className="fixed inset-0 bg-black/50 z-50 grid place-items-center p-4" onClick={onClose}>
      <div className="card w-full max-w-md max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        <h3 className="font-bold mb-2">Subjects {fac.name} can teach</h3>
        {subs.map((s) => <label key={s.id} className="block text-sm"><input type="checkbox" checked={mine.includes(s.id)} onChange={() => tog(s.id)} /> {s.code} — {s.name} (Sem {s.semester})</label>)}
        <div className="flex gap-2 justify-end mt-3"><button className="btn-ghost" onClick={onClose}>Cancel</button><button className="btn" onClick={async () => { await api.put(`/faculty/${fac.id}/subjects`, mine); onClose() }}>Save</button></div>
      </div></div>)
}

export default function Master() {
  const [tab, setTab] = useState('faculty'), [q, setQ] = useState(''), [edit, setEdit] = useState(null), [teach, setTeach] = useState(null)
  const [rows, reload, , setRows] = useLoad(() => api.get(`/${tab}?limit=1000`), [tab])
  const cols = Object.keys(SCHEMA[tab])
  const shown = (rows || []).filter((r) => JSON.stringify(Object.values(r)).toLowerCase().includes(q.toLowerCase()))
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-extrabold">🗂️ Master Data Management</h1>
      <div className="flex flex-wrap gap-1">{Object.entries(TABS).map(([k, l]) => <button key={k} className={tab === k ? 'btn' : 'btn-ghost'} onClick={() => { setTab(k); setRows(null) }}>{l}</button>)}</div>
      <div className="flex gap-2"><input className="inp max-w-xs" placeholder="Filter…" value={q} onChange={(e) => setQ(e.target.value)} /><button className="btn" onClick={() => setEdit({})}>＋ Add</button><span className="text-sm text-mute self-center">{shown.length} records</span></div>
      <div className="card overflow-x-auto p-0"><table className="w-full"><thead><tr>{cols.map((c) => <th key={c} className="th">{c.replace(/_/g, ' ')}</th>)}<th className="th" /></tr></thead>
        <tbody>{shown.map((r) => <tr key={r.id}>{cols.map((c) => <td key={c} className="td">{typeof r[c] === 'boolean' ? (r[c] ? '✓' : '—') : r[c]}</td>)}
          <td className="td whitespace-nowrap space-x-1">{tab === 'faculty' && <button className="btn-ghost !py-0.5" onClick={() => setTeach(r)}>Subjects</button>}
            <button className="btn-ghost !py-0.5" onClick={() => setEdit(r)}>Edit</button>
            <button className="btn-ghost !py-0.5 text-bad" onClick={async () => { if (confirm('Delete?')) { try { await api.del(`/${tab}/${r.id}`); reload() } catch (e) { alert(e.message) } } }}>🗑</button></td></tr>)}</tbody></table></div>
      {edit && <Form res={tab} row={edit} onClose={() => setEdit(null)} onSaved={() => { setEdit(null); reload() }} />}
      {teach && <CanTeach fac={teach} onClose={() => setTeach(null)} />}
    </div>)
}
