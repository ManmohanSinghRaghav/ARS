import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './auth/AuthContext';
import ProtectedRoute from './auth/ProtectedRoute';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import RunDetailPage from './pages/RunDetailPage';
import HistoryPage from './pages/HistoryPage';
import SettingsPage from './pages/SettingsPage';
import Navbar from './components/Navbar';

function App() {
  const { user } = useAuth();

  return (
    <div className={`min-h-screen relative overflow-x-hidden ${user ? "ocean-bg text-[#f6f6fc] font-['Manrope',_sans-serif]" : "bg-gray-50"}`}>
      {user && <Navbar />}
      <main className={user ? "ml-32 mr-12 pt-24 pb-12" : ""}>
        <Routes>
        <Route path="/login" element={user ? <Navigate to="/" /> : <LoginPage />} />
        <Route path="/register" element={user ? <Navigate to="/" /> : <LoginPage />} />
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <DashboardPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/runs/:id"
          element={
            <ProtectedRoute>
              <RunDetailPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/history"
          element={
            <ProtectedRoute>
              <HistoryPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/settings"
          element={
            <ProtectedRoute>
              <SettingsPage />
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<Navigate to="/" />} />
      </Routes>
      </main>
    </div>
  );
}

export default App;
