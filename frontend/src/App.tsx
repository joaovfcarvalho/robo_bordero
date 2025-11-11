import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import PDFManager from './pages/PDFManager'
import AdminLogin from './pages/AdminLogin'
import { isAuthenticated } from './api/client'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  return isAuthenticated() ? <>{children}</> : <Navigate to="/admin/login" />
}

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="pdfs" element={
            <ProtectedRoute>
              <PDFManager />
            </ProtectedRoute>
          } />
          <Route path="admin/login" element={<AdminLogin />} />
        </Route>
      </Routes>
    </Router>
  )
}

export default App
