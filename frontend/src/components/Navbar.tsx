import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';

export default function Navbar() {
  const { user, logout } = useAuth();
  const location = useLocation();

  const linkClass = (path: string) =>
    `px-3 py-2 rounded-md text-sm font-medium transition-colors ${
      location.pathname === path
        ? 'bg-primary-700 text-white'
        : 'text-primary-100 hover:bg-primary-600 hover:text-white'
    }`;

  return (
    <nav className="bg-primary-800 shadow-lg">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center space-x-4">
            <Link to="/" className="text-white font-bold text-lg tracking-wide">
              ARS
            </Link>
            <div className="hidden sm:flex space-x-2">
              <Link to="/" className={linkClass('/')}>
                Dashboard
              </Link>
              <Link to="/history" className={linkClass('/history')}>
                History
              </Link>
              <Link to="/settings" className={linkClass('/settings')}>
                Settings
              </Link>
            </div>
          </div>
          <div className="flex items-center space-x-4">
            <span className="text-primary-200 text-sm">
              {user?.username}
              {user?.role === 'admin' && (
                <span className="ml-1 px-1.5 py-0.5 bg-yellow-500 text-yellow-900 text-xs rounded-full font-semibold">
                  admin
                </span>
              )}
            </span>
            <button
              onClick={logout}
              className="px-3 py-1.5 bg-primary-900 text-primary-200 rounded-md text-sm hover:bg-primary-950 transition-colors"
            >
              Logout
            </button>
          </div>
        </div>
      </div>
    </nav>
  );
}
