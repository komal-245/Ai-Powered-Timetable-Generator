import { useLoad } from '../hooks'
import { api } from '../api'
import { ChartBox, Heatmap, Bar } from '../components/Charts'

export default function Analytics() {
  const [d] = useLoad(() => api.get('/dashboard'))
  if (!d) return <div className="text-mute">Loading…</div>
  const a = d.analytics
  const fac = a.faculty.filter((f) => f.hours > 0)
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-extrabold">📈 Resource Optimization & Analytics</h1>
      <div className="grid md:grid-cols-4 gap-3">{[['Teacher Utilization', a.resource.teacher_utilization], ['Room Utilization', a.resource.room_utilization], ['Lab Utilization', a.resource.lab_utilization], ['Faculty Balance', a.resource.faculty_balance]]
        .map(([l, v]) => <div key={l} className="card text-center"><div className="text-3xl font-extrabold text-accent">{v}%</div><div className="text-sm text-mute">{l}</div></div>)}</div>
      <div className="grid lg:grid-cols-2 gap-4">
        <div className="card"><h3 className="font-bold mb-2">Faculty utilization (% of max hours)</h3><ChartBox type="bar" labels={fac.map((f) => f.name.split(' ').slice(-1)[0])} datasets={[{ label: '%', data: fac.map((f) => f.pct) }]} height={300} /></div>
        <div className="card"><h3 className="font-bold mb-2">Heatmap: classes running in parallel</h3><Heatmap data={a.heatmap} days={a.days} slots={a.slots} /></div>
        <div className="card"><h3 className="font-bold mb-2">Classes by period (peak hours)</h3><ChartBox labels={a.slots.map((s, i) => `P${i + 1}`)} datasets={[{ label: 'Classes', data: a.slots.map((_, t) => a.heatmap.reduce((x, r) => x + r[t], 0)) }]} /></div>
        <div className="card"><h3 className="font-bold mb-2">Room efficiency</h3>{a.rooms.map((r) => <Bar key={r.id} label={r.name + (r.is_lab ? ' (lab)' : '')} value={r.pct} color={r.is_lab ? 'ok' : 'accent'} />)}</div>
      </div>
    </div>)
}
