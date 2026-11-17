const G = [['Auth', 'POST /api/auth/login · GET /api/auth/me · POST /api/auth/change-password · POST /api/auth/reset-password'],
  ['Faculty', 'GET/POST /api/faculty · PUT/DELETE /api/faculty/{id} · /api/faculty/{id}/subjects · /unavailability'],
  ['Students', 'GET/POST /api/students · PUT/DELETE /api/students/{id} · GET /api/me/proctor'],
  ['Subjects / Rooms / Sections / Departments / Calendar', 'GET/POST /api/{resource} · PUT/DELETE /api/{resource}/{id}'],
  ['Timetable generation', 'POST /api/timetables/generate → GET /api/timetables/jobs/{job}'],
  ['Timetables', 'GET /api/timetables · /{id} · /{id}/view · /{id}/conflicts · /{id}/analytics · POST /{id}/move · /activate · /restore · GET /compare'],
  ['Portals', 'GET /api/me/timetable · /me/workload · /me/preferences · /rooms/{id}/status · /search · /notifications'],
  ['Reports & export', 'GET /api/reports/{faculty|classroom|utilization|department|analytics}.pdf · /reports/timetable.pdf · /export/xlsx · /export/ics · /export/gcal-links'],
  ['Chatbot', 'POST /api/chat']]
export default function ApiDocs() {
  return (
    <div className="space-y-4"><h1 className="text-2xl font-extrabold">🔌 REST API</h1>
      <p>Interactive Swagger documentation: <a className="text-accent underline" target="_blank" rel="noreferrer" href="/api/docs">/api/docs</a> (use the <b>Authorize</b> button with admin credentials).</p>
      <div className="card divide-y divide-line">{G.map(([a, b]) => <div key={a} className="py-2"><div className="font-bold">{a}</div><code className="text-xs text-mute break-words">{b}</code></div>)}</div></div>)
}
