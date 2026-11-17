import { download } from '../api'
import { getUser } from '../api'

export default function Reports() {
  const admin = getUser().role === 'admin'
  const R = [['Faculty report', 'Workload of every teacher', '/reports/faculty.pdf', 'faculty-report.pdf'],
    ['Classroom report', 'Room & lab occupancy', '/reports/classroom.pdf', 'classroom-report.pdf'],
    ['Utilization report', 'Teacher / room / lab utilization and scores', '/reports/utilization.pdf', 'utilization-report.pdf'],
    ['Department report', 'Sections, periods, free time', '/reports/department.pdf', 'department-report.pdf'],
    ['Analytics report', 'Peak hours, day distribution, subjects', '/reports/analytics.pdf', 'analytics-report.pdf'],
    ['Full timetable workbook', 'Excel: every section + workload + rooms', '/export/xlsx', 'timetable.xlsx']]
  return (
    <div className="space-y-4"><h1 className="text-2xl font-extrabold">📄 Reports</h1>
      <p className="text-sm text-mute">Reports are generated from the currently active timetable. Per-section / faculty / room timetable PDFs are on the Timetable page.</p>
      <div className="grid md:grid-cols-3 gap-4">{R.map(([t, d, p, f]) => <div key={t} className="card"><div className="font-bold">{t}</div><div className="text-sm text-mute mb-3">{d}</div>
        <button className="btn" onClick={() => download(p, f)}>⬇ Download</button></div>)}</div>
    </div>)
}
