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

  // If not authenticated, show login modal overlay with blurred dashboard behind
  if (!user) {
    return (
      <div className="relative min-h-screen">
        {/* Blurred content behind */}
        <div className="blur-sm pointer-events-none select-none">
          {children}
        </div>
        
        {/* Login modal overlay */}
        <div className="fixed inset-0 z-50">
          <LoginPage isModal={true} />
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
