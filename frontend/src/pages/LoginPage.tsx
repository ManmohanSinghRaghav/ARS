import { useState, FormEvent } from 'react';
import { useAuth } from '../auth/AuthContext';
import toast from 'react-hot-toast';

interface LoginPageProps {
  isModal?: boolean;
}

export default function LoginPage({ isModal = false }: LoginPageProps) {
  const { login, register, loginWithGoogle } = useAuth();
  const [activeTab, setActiveTab] = useState<'login' | 'register'>('login');
  const [loading, setLoading] = useState(false);

  // Login form state
  const [loginEmail, setLoginEmail] = useState('');
  const [loginPassword, setLoginPassword] = useState('');

  // Register form state
  const [registerUsername, setRegisterUsername] = useState('');
  const [registerEmail, setRegisterEmail] = useState('');
  const [registerPassword, setRegisterPassword] = useState('');
  const [registerConfirmPassword, setRegisterConfirmPassword] = useState('');

  const handleLogin = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await login(loginEmail, loginPassword);
      toast.success('Welcome back!');
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (e: FormEvent) => {
    e.preventDefault();
    if (registerPassword !== registerConfirmPassword) {
      toast.error('Passwords do not match');
      return;
    }
    if (registerPassword.length < 6) {
      toast.error('Password must be at least 6 characters');
      return;
    }
    setLoading(true);
    try {
      await register(registerUsername, registerEmail, registerPassword);
      toast.success('Account created successfully!');
      setActiveTab('login');
      setRegisterUsername('');
      setRegisterEmail('');
      setRegisterPassword('');
      setRegisterConfirmPassword('');
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleSignIn = async () => {
    setLoading(true);
    try {
      await loginWithGoogle();
      toast.success('Welcome!');
    } catch (err: any) {
      console.error('Google Sign-In error:', err);
      toast.error(err.message || 'Google Sign-In failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={`${
      isModal 
        ? 'absolute inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4' 
        : 'fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4 z-50'
    }`}>
      {/* Background blur overlay */}
      <div className="absolute inset-0 bg-gradient-to-br from-primary-900/20 via-primary-800/10 to-primary-950/20"></div>

      {/* Modal Container */}
      <div className="relative w-full max-w-4xl mx-auto">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-0 rounded-2xl overflow-hidden shadow-2xl bg-slate-900/80 backdrop-blur-xl border border-slate-700/50">
          {/* Left Section - Branding */}
          <div className="hidden md:flex flex-col justify-center items-center p-12 bg-gradient-to-br from-slate-800 to-slate-900 border-r border-slate-700/50">
            <div className="text-center">
              <div className="inline-flex items-center justify-center w-16 h-16 bg-cyan-500/20 rounded-xl mb-6">
                <svg className="w-8 h-8 text-cyan-400" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M10 2a1 1 0 011 1v1.22l3.844-1.615a1 1 0 11.912 1.736L12.9 5.957V8h1.222a1 1 0 110 2H12.9v1.957l3.656 1.539a1 1 0 11-.912 1.736L11 11.78V13h1.222a1 1 0 110 2H11v1.222a1 1 0 11-2 0V15H7.957l-1.539 3.656a1 1 0 11-1.736-.912L5.957 12.9H3a1 1 0 110-2h2.22L1.78 9.156a1 1 0 011.736-.912L5.15 10.9V9H3.93a1 1 0 110-2h1.22V5.043L1.494 3.504a1 1 0 01.912-1.736L9 4.22V3a1 1 0 011-1z" />
                </svg>
              </div>
              <h1 className="text-4xl font-bold text-white mb-2">ARS</h1>
              <p className="text-cyan-400 text-sm font-semibold tracking-widest mb-4">AUTOMATED RESEARCH SCIENTIST</p>
              <div className="w-16 h-1 bg-gradient-to-r from-cyan-400 to-blue-500 mx-auto"></div>
            </div>
          </div>

          {/* Right Section - Forms */}
          <div className="p-8 md:p-12">
            {/* Tab Navigation */}
            <div className="flex gap-4 mb-8 border-b border-slate-700">
              <button
                onClick={() => setActiveTab('login')}
                className={`pb-3 px-2 font-semibold text-sm tracking-wider transition-all ${
                  activeTab === 'login'
                    ? 'text-cyan-400 border-b-2 border-cyan-400'
                    : 'text-gray-400 hover:text-gray-300'
                }`}
              >
                ACCESS PORTAL
              </button>
              <button
                onClick={() => setActiveTab('register')}
                className={`pb-3 px-2 font-semibold text-sm tracking-wider transition-all ${
                  activeTab === 'register'
                    ? 'text-cyan-400 border-b-2 border-cyan-400'
                    : 'text-gray-400 hover:text-gray-300'
                }`}
              >
                JOIN LABORATORY
              </button>
            </div>

            {/* Login Form */}
            {activeTab === 'login' && (
              <form onSubmit={handleLogin} className="space-y-5">
                <div>
                  <label className="block text-sm font-semibold text-gray-300 mb-2 uppercase tracking-wider">
                    Researcher ID
                  </label>
                  <input
                    type="email"
                    value={loginEmail}
                    onChange={(e) => setLoginEmail(e.target.value)}
                    required
                    className="w-full px-4 py-3 bg-slate-800/50 border border-slate-600 rounded-lg text-white placeholder-gray-500 focus:ring-2 focus:ring-cyan-400 focus:border-cyan-400 outline-none transition-all"
                    placeholder="your@email.com"
                  />
                </div>

                <div>
                  <label className="block text-sm font-semibold text-gray-300 mb-2 uppercase tracking-wider">
                    Access Cipher
                  </label>
                  <input
                    type="password"
                    value={loginPassword}
                    onChange={(e) => setLoginPassword(e.target.value)}
                    required
                    className="w-full px-4 py-3 bg-slate-800/50 border border-slate-600 rounded-lg text-white placeholder-gray-500 focus:ring-2 focus:ring-cyan-400 focus:border-cyan-400 outline-none transition-all"
                    placeholder="••••••••"
                  />
                </div>

                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="maintain"
                    className="w-4 h-4 rounded border-slate-600 text-cyan-400 focus:ring-2 focus:ring-cyan-400"
                  />
                  <label htmlFor="maintain" className="text-sm text-gray-400">
                    Maintain persistent laboratory session
                  </label>
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full py-3 bg-gradient-to-r from-cyan-500 to-blue-500 hover:from-cyan-600 hover:to-blue-600 disabled:opacity-50 text-white font-semibold rounded-lg transition-all mt-6 uppercase tracking-wider"
                >
                  {loading ? 'Initializing...' : 'Initialize Synthesis'}
                </button>

                <div className="relative my-6">
                  <div className="absolute inset-0 flex items-center">
                    <div className="w-full border-t border-slate-600"></div>
                  </div>
                  <div className="relative flex justify-center text-sm">
                    <span className="px-2 bg-slate-900/80 text-gray-400">OR ACCESS VIA</span>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={handleGoogleSignIn}
                  disabled={loading}
                  className="w-full py-3 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 border border-slate-600 text-white font-semibold rounded-lg transition-all flex items-center justify-center gap-2 uppercase tracking-wider"
                >
                  <svg className="w-5 h-5" viewBox="0 0 24 24">
                    <path fill="currentColor" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                    <path fill="currentColor" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                    <path fill="currentColor" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                    <path fill="currentColor" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                  </svg>
                  {loading ? 'Initializing...' : 'Continue with Google'}
                </button>
              </form>
            )}

            {/* Register Form */}
            {activeTab === 'register' && (
              <form onSubmit={handleRegister} className="space-y-4">
                <div>
                  <label className="block text-sm font-semibold text-gray-300 mb-2 uppercase tracking-wider">
                    Full Name
                  </label>
                  <input
                    type="text"
                    value={registerUsername}
                    onChange={(e) => setRegisterUsername(e.target.value)}
                    required
                    className="w-full px-4 py-3 bg-slate-800/50 border border-slate-600 rounded-lg text-white placeholder-gray-500 focus:ring-2 focus:ring-cyan-400 focus:border-cyan-400 outline-none transition-all"
                    placeholder="Dr. Jane Smith"
                  />
                </div>

                <div>
                  <label className="block text-sm font-semibold text-gray-300 mb-2 uppercase tracking-wider">
                    Researcher ID
                  </label>
                  <input
                    type="email"
                    value={registerEmail}
                    onChange={(e) => setRegisterEmail(e.target.value)}
                    required
                    className="w-full px-4 py-3 bg-slate-800/50 border border-slate-600 rounded-lg text-white placeholder-gray-500 focus:ring-2 focus:ring-cyan-400 focus:border-cyan-400 outline-none transition-all"
                    placeholder="dr.smith@ars.lab"
                  />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-sm font-semibold text-gray-300 mb-2 uppercase tracking-wider">
                      Access Cipher
                    </label>
                    <input
                      type="password"
                      value={registerPassword}
                      onChange={(e) => setRegisterPassword(e.target.value)}
                      required
                      className="w-full px-4 py-3 bg-slate-800/50 border border-slate-600 rounded-lg text-white placeholder-gray-500 focus:ring-2 focus:ring-cyan-400 focus:border-cyan-400 outline-none transition-all"
                      placeholder="••••••••"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-semibold text-gray-300 mb-2 uppercase tracking-wider">
                      Confirm Cipher
                    </label>
                    <input
                      type="password"
                      value={registerConfirmPassword}
                      onChange={(e) => setRegisterConfirmPassword(e.target.value)}
                      required
                      className="w-full px-4 py-3 bg-slate-800/50 border border-slate-600 rounded-lg text-white placeholder-gray-500 focus:ring-2 focus:ring-cyan-400 focus:border-cyan-400 outline-none transition-all"
                      placeholder="••••••••"
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full py-3 bg-gradient-to-r from-cyan-500 to-blue-500 hover:from-cyan-600 hover:to-blue-600 disabled:opacity-50 text-white font-semibold rounded-lg transition-all mt-6 uppercase tracking-wider"
                >
                  {loading ? 'Initializing...' : 'Create Credentials'}
                </button>

                <div className="relative my-6">
                  <div className="absolute inset-0 flex items-center">
                    <div className="w-full border-t border-slate-600"></div>
                  </div>
                  <div className="relative flex justify-center text-sm">
                    <span className="px-2 bg-slate-900/80 text-gray-400">OR ACCESS VIA</span>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={handleGoogleSignIn}
                  disabled={loading}
                  className="w-full py-3 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 border border-slate-600 text-white font-semibold rounded-lg transition-all flex items-center justify-center gap-2 uppercase tracking-wider"
                >
                  <svg className="w-5 h-5" viewBox="0 0 24 24">
                    <path fill="currentColor" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                    <path fill="currentColor" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                    <path fill="currentColor" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                    <path fill="currentColor" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                  </svg>
                  {loading ? 'Initializing...' : 'Continue with Google'}
                </button>
              </form>
            )}

            {/* Footer */}
            <div className="mt-8 pt-6 border-t border-slate-700">
              <p className="text-xs text-gray-500 text-center">
                <span className="inline-block">🔒 SECURE NODE: 0x4f2a</span>
                <span className="mx-2">•</span>
                <span className="inline-block">SYSTEM STATUS: OPTIMAL</span>
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
