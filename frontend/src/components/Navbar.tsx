import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { Science, History, Settings, Logout } from '@mui/icons-material'; // Optional: Use Lucide if already in project

export default function Navbar() {
  const { user, logout } = useAuth();
  const location = useLocation();

  const isActive = (path: string) => location.pathname === path;

  return (
    <nav className="fixed top-0 left-0 right-0 h-20 px-8 flex items-center justify-between z-50 bg-[#0f172a]/40 backdrop-blur-xl border-b border-white/5">
      <div className="flex items-center gap-12">
        <Link to="/" className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-indigo-600 flex items-center justify-center text-white font-black shadow-[0_0_20px_rgba(79,70,229,0.4)]">A</div>
          <span className="text-sm font-bold tracking-[0.3em] text-white uppercase">Antigravity ARS</span>
        </Link>

        <div className="hidden md:flex items-center gap-8">
          {[
            { label: 'Swarm', path: '/', icon: 'science' },
            { label: 'Archives', path: '/history', icon: 'history' },
            { label: 'Config', path: '/settings', icon: 'settings' },
          ].map((item) => (
            <Link 
              key={item.path}
              to={item.path}
              className={`text-[10px] font-bold uppercase tracking-widest transition-all ${
                isActive(item.path) ? 'text-indigo-400' : 'text-slate-500 hover:text-slate-300'
              }`}
            >
              {item.label}
            </Link>
          ))}
        </div>
      </div>

      <div className="flex items-center gap-6">
        <div className="flex flex-col items-end">
          <span className="text-[10px] font-bold text-slate-300 uppercase tracking-widest">{user?.username}</span>
          <span className="text-[8px] text-indigo-500 font-black uppercase tracking-widest">{user?.role}</span>
        </div>
        <button 
          onClick={logout}
          className="w-10 h-10 rounded-xl bg-slate-800/50 flex items-center justify-center text-slate-400 hover:text-white hover:bg-red-500/10 transition-all border border-white/5"
        >
          <Logout fontSize="small" />
        </button>
      </div>
    </nav>
  );
}
