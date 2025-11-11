import { Outlet, Link, useLocation } from 'react-router-dom'
import { BarChart3, FileText, LogOut } from 'lucide-react'
import { isAuthenticated, clearAuthToken } from '../api/client'

export default function Layout() {
  const location = useLocation()
  const isAuth = isAuthenticated()

  const handleLogout = () => {
    clearAuthToken()
    window.location.href = '/'
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex">
              <div className="flex-shrink-0 flex items-center">
                <h1 className="text-xl font-bold text-gray-900">
                  CBF Borderô Robot
                </h1>
              </div>
              <div className="hidden sm:ml-6 sm:flex sm:space-x-8">
                <Link
                  to="/"
                  className={`inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium ${
                    location.pathname === '/'
                      ? 'border-primary-500 text-gray-900'
                      : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                  }`}
                >
                  <BarChart3 className="w-4 h-4 mr-2" />
                  Analytics
                </Link>
                {isAuth && (
                  <Link
                    to="/pdfs"
                    className={`inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium ${
                      location.pathname === '/pdfs'
                        ? 'border-primary-500 text-gray-900'
                        : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                    }`}
                  >
                    <FileText className="w-4 h-4 mr-2" />
                    PDF Manager
                  </Link>
                )}
              </div>
            </div>
            <div className="flex items-center">
              {isAuth ? (
                <button
                  onClick={handleLogout}
                  className="inline-flex items-center px-3 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700"
                >
                  <LogOut className="w-4 h-4 mr-2" />
                  Logout
                </button>
              ) : (
                <Link
                  to="/admin/login"
                  className="inline-flex items-center px-3 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
                >
                  Admin Login
                </Link>
              )}
            </div>
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Outlet />
      </main>
    </div>
  )
}
