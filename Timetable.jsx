import { useSearchParams } from 'react-router-dom'
import { useLoad } from '../hooks'
import { api } from '../api'
import TimetableView from '../components/TimetableView'

export default function Timetable() {
  const [sp, setSp] = useSearchParams()
  const [list] = useLoad(() => api.get('/timetables'))
  if (!list) return <div className="text-mute">Loading…</div>
  if (!list.length) return <div className="card">No timetable yet — go to <b>AI Generator</b>.</div>
  const tid = +sp.get('tid') || (list.find((t) => t.is_active) || list[0]).id
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3"><h1 className="text-2xl font-extrabold">🗓️ Timetable</h1>
        <select className="inp !w-auto" value={tid} onChange={(e) => setSp({ tid: e.target.value })}>
          {list.map((t) => <option key={t.id} value={t.id}>{t.is_active ? '● ' : ''}{t.name} — {t.score.overall}%</option>)}</select></div>
      <TimetableView key={tid} tid={tid} editable />
    </div>)
}
