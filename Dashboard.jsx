import { useLoad } from '../hooks'
import { api } from '../api'
import { ChartBox, Heatmap, Bar, ScorePanel, scoreColor } from '../components/Charts'

const Card = ({ icon, label, value, suffix = '' }) => (
  <div className="card flex items-center gap-3"><div className="text-2xl">{icon}</div><div><div className="text-2xl font-extrabold">{value}{suffix}</div><div className="text-xs text-mute">{label}</div></div></div>)

export default function Dashboard() {
  const [d, , err] = useLoad(() => api.get('/dashboard'))
  if (err) return <div className="text-bad">{err}</div>
  if (!d) return <div className="text-mute">Loading…</div>
  const { cards: c, analytics: a } = d
  const empty = !a.subjects.length
  const top = a.faculty.slice(0, 15)
  const rooms = a.rooms.filter((r) => !r.is_lab), labs = a.rooms.filter((r) => r.is_lab)
  return (
    <div className="space-y-5">
      <div className="flex items-baseline justify-between"><h1 className="text-2xl font-extrabold">Dashboard</h1><span className="text-sm text-mute">Active: {d.active || 'none — generate one in AI Generator'}</span></div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Card icon="👩‍🏫" label="Total Faculty" value={c.total_faculty} /><Card icon="🎓" label="Total Students" value={c.total_students} />
        <Card icon="🏛️" label="Departments" value={c.total_departments} /><Card icon="🏫" label="Classrooms" value={c.total_rooms} />
        <Card icon="🧪" label="Laboratories" value={c.total_labs} /><Card icon="🗓️" label="Timetables Generated" value={c.timetables_generated} />
        <Card icon="✅" label="Active Faculty" value={c.active_faculty} /><Card icon="🧠" label="AI Optimization Score" value={c.ai_score} suffix="%" />
      </div>
      {empty ? <div className="card text-mute">No timetable yet. Open <b>AI Generator</b> to create one.</div> : <>
        <div className="grid lg:grid-cols-3 gap-4">
          <div className="card"><h3 className="font-bold mb-2">Resource Optimization</h3>
            <Bar label="Teacher Utilization" value={a.resource.teacher_utilization} color={scoreColor(a.resource.teacher_utilization + 20)} />
            <Bar label="Room Utilization" value={a.resource.room_utilization} /><Bar label="Lab Utilization" value={a.resource.lab_utilization} color="ok" />
            <Bar label="Faculty Balance" value={a.resource.faculty_balance} color={scoreColor(a.resource.faculty_balance)} /></div>
          <div className="card"><h3 className="font-bold mb-2">Timetable Quality</h3><ScorePanel score={a.score} /></div>
          <div className="card"><h3 className="font-bold mb-2">Smart Notifications</h3><div className="space-y-1 text-sm max-h-60 overflow-y-auto">
            {d.notifications.length === 0 && <div className="text-ok">✓ Nothing needs attention</div>}
            {d.notifications.map((n, i) => <div key={i} className={n.level === 'danger' ? 'text-bad' : n.level === 'warning' ? 'text-warn' : 'text-mute'}>• {n.message}</div>)}</div></div>
        </div>
        <div className="grid lg:grid-cols-2 gap-4">
          <div className="card"><h3 className="font-bold mb-2">Faculty Workload (periods / week)</h3>
            <ChartBox labels={top.map((f) => f.name.replace(/^(Dr|Mr|Mrs|Ms)\.?\s*(\(Mrs\.\)\s*)?/, ''))} datasets={[{ label: 'Periods', data: top.map((f) => f.hours) }, { label: 'Max', data: top.map((f) => f.max), backgroundColor: '#cbd5e1' }]} height={300} /></div>
          <div className="card"><h3 className="font-bold mb-2">Weekly Schedule Heatmap</h3><Heatmap data={a.heatmap} days={a.days} slots={a.slots} /></div>
          <div className="card"><h3 className="font-bold mb-2">Room Utilization (%)</h3><ChartBox labels={rooms.map((r) => r.name)} datasets={[{ label: '% of week', data: rooms.map((r) => r.pct) }]} /></div>
          <div className="card"><h3 className="font-bold mb-2">Lab Usage (%)</h3><ChartBox labels={labs.map((r) => r.name)} datasets={[{ label: '% of week', data: labs.map((r) => r.pct) }]} /></div>
          <div className="card"><h3 className="font-bold mb-2">Subject Distribution</h3><ChartBox type="doughnut" labels={a.subjects.map((s) => s.code)} datasets={[{ data: a.subjects.map((s) => s.periods) }]} /></div>
          <div className="card"><h3 className="font-bold mb-2">Daily Class Distribution</h3><ChartBox labels={a.days} datasets={[{ label: 'Periods', data: a.daily }]} /></div>
          <div className="card"><h3 className="font-bold mb-2">Department Comparison</h3><ChartBox labels={d.departments.map((x) => x.name)} datasets={[{ label: 'Periods', data: d.departments.map((x) => x.periods) }, { label: 'Faculty', data: d.departments.map((x) => x.faculty) }]} /></div>
          <div className="card"><h3 className="font-bold mb-2">Free-Period Analysis (avg free / day)</h3><ChartBox labels={a.sections.map((s) => s.label)} datasets={[{ label: 'Free periods', data: a.sections.map((s) => s.avg_free) }]} /></div>
        </div>
        <div className="card"><h3 className="font-bold mb-2">Admin Analytics</h3><div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-sm">
          {[['Peak teaching hour', a.stats.peak_hour], ['Most crowded day', a.stats.most_crowded_day], ['Least occupied room', a.stats.least_occupied_room],
            ['Faculty utilization', a.stats.faculty_utilization + '%'], ['Avg free periods / day', a.stats.avg_free_periods], ['AI optimization score', a.stats.optimization_score + '%']]
            .map(([k, v]) => <div key={k} className="bg-bg rounded-lg p-3"><div className="text-mute text-xs">{k}</div><div className="font-bold text-lg">{v}</div></div>)}</div></div></>}
    </div>)
}
