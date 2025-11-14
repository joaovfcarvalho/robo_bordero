import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import PDFUpload from './pages/PDFUpload'
import PasswordGate from './components/PasswordGate'

function App() {
  return (
    <PasswordGate>
      <Router>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Dashboard />} />
            <Route path="upload" element={<PDFUpload />} />
          </Route>
        </Routes>
      </Router>
    </PasswordGate>
  )
}

export default App
