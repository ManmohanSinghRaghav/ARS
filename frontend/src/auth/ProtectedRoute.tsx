import { useAuth } from './AuthContext';
import { ReactNode } from 'react';
import LoginPage from '../pages/LoginPage';

interface Props {
  children: ReactNode;
}

export default function ProtectedRoute({ children }: Props) {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  // If not authenticated, show login modal only
  if (!user) {
    return <LoginPage />;
  }

  return <>{children}</>;
}
