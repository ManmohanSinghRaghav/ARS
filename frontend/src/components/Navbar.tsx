import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';

export default function Navbar() {
  const { user, logout } = useAuth();
  const location = useLocation();

  const isActive = (path: string) => location.pathname === path;

  return (
    <>
      {/* TopNavBar */}
      <header className="fixed top-0 right-0 p-6 flex justify-end items-center w-full z-50 bg-transparent">
        <div className="flex items-center gap-6">
          <Link to="/" className="font-['Space_Grotesk'] text-sm text-[#a1faff] font-bold tracking-widest uppercase">ARS</Link>
          <div className="text-sm font-['Manrope'] text-[#aaabb0]">
            {user?.username}
            {user?.role === 'admin' && (
              <span className="ml-2 px-1.5 py-0.5 bg-[#a1faff]/20 text-[#a1faff] text-xs rounded-full font-semibold uppercase tracking-wider">
                admin
              </span>
            )}
          </div>
          <button 
            onClick={logout}
            className="hover:bg-slate-800/60 rounded-full p-2 transition-all active:opacity-80 flex items-center"
            title="Logout"
          >
            <span className="material-symbols-outlined text-[#a1faff]">logout</span>
          </button>
        </div>
      </header>

      {/* SideNavBar */}
      <nav className="fixed left-6 top-1/2 -translate-y-1/2 rounded-full w-20 py-8 border-r border-[#a1faff]/10 bg-slate-800/40 backdrop-blur-2xl flex flex-col items-center gap-10 z-50 shadow-[0_20px_40px_rgba(0,244,254,0.08)]">
        <div className="flex flex-col items-center gap-2 mb-4">
          <Link to="/" className="text-[#a1faff] font-['Space_Grotesk'] font-bold tracking-widest uppercase text-xs">ARS</Link>
        </div>
        <Link 
          to="/" 
          className={`group flex flex-col items-center gap-1 transition-all duration-300 ${
            isActive('/') ? 'text-[#a1faff] drop-shadow-[0_0_8px_rgba(161,250,255,0.6)] scale-110' : 'text-slate-500 scale-100 hover:text-[#00f4fe]'
          }`}
        >
          <span className="material-symbols-outlined">science</span>
        </Link>
        <Link 
          to="/history" 
          className={`group flex flex-col items-center gap-1 transition-all duration-300 ${
            isActive('/history') || location.pathname.startsWith('/runs') ? 'text-[#a1faff] drop-shadow-[0_0_8px_rgba(161,250,255,0.6)] scale-110' : 'text-slate-500 scale-100 hover:text-[#00f4fe]'
          }`}
        >
          <span className="material-symbols-outlined">cyclone</span>
        </Link>
        <Link 
          to="#" 
          className="group flex flex-col items-center gap-1 text-slate-500 scale-100 hover:text-[#00f4fe] transition-all duration-300"
        >
          <span className="material-symbols-outlined">insights</span>
        </Link>
        <Link 
          to="/settings" 
          className={`group flex flex-col items-center gap-1 transition-all duration-300 mt-auto ${
            isActive('/settings') ? 'text-[#a1faff] drop-shadow-[0_0_8px_rgba(161,250,255,0.6)] scale-110' : 'text-slate-500 scale-100 hover:text-[#00f4fe]'
          }`}
        >
          <span className="material-symbols-outlined">settings</span>
        </Link>
      </nav>

      {/* Background Decorative Elements */}
      <div className="fixed bottom-0 left-0 w-full h-64 pointer-events-none z-0 opacity-20">
        <div className="absolute inset-0 bg-gradient-to-t from-[#a1faff]/10 to-transparent"></div>
      </div>
      <div className="fixed top-20 right-20 w-[500px] h-[500px] bg-[#a1faff]/5 rounded-full blur-[120px] pointer-events-none -z-10"></div>
    </>
  );
}
