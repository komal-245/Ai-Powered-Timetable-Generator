import { Routes, Route, Navigate } from 'react-router-dom'
import { getUser } from './api'
import Layout from './components/Layout'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Generator from './pages/Generator'
import Timetable from './pages/Timetable'
import History from './pages/History'
import Analytics from './pages/Analytics'
import Rooms from './pages/Rooms'
import Master from './pages/Master'
import Reports from './pages/Reports'
import ApiDocs from './pages/ApiDocs'
import FacultyPortal from './pages/FacultyPortal'
import StudentPortal from './pages/StudentPortal'

const home = () => { const u = getUser(); return u?.role === 'faculty' ? '/faculty' : u?.role === 'student' ? '/student' : '/' }
const Only = ({ role, children }) => (getUser()?.role === role ? children : <Navigate to={home()} replace />)

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route element={<Layout />}>
        <Route path="/" element={<Only role="admin"><Dashboard /></Only>} />
        <Route path="/generate" element={<Only role="admin"><Generator /></Only>} />
        <Route path="/timetable" element={<Only role="admin"><Timetable /></Only>} />
        <Route path="/history" element={<Only role="admin"><History /></Only>} />
        <Route path="/analytics" element={<Only role="admin"><Analytics /></Only>} />
        <Route path="/master" element={<Only role="admin"><Master /></Only>} />
        <Route path="/api-docs" element={<Only role="admin"><ApiDocs /></Only>} />
        <Route path="/reports" element={<Reports />} />
        <Route path="/rooms" element={<Rooms />} />
        <Route path="/faculty" element={<Only role="faculty"><FacultyPortal /></Only>} />
        <Route path="/student" element={<Only role="student"><StudentPortal /></Only>} />
      </Route>
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  )
}
