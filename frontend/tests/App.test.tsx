import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import '@testing-library/jest-dom';
import App from '../src/App';
import { AuthProvider } from '../src/auth/AuthContext';

// ── Mocks ──
vi.mock('firebase/app', () => ({
  initializeApp: vi.fn(),
  getApps: vi.fn(() => []),
}));
vi.mock('firebase/analytics', () => ({
  getAnalytics: vi.fn(),
}));
vi.mock('firebase/auth', () => ({
  getAuth: vi.fn(() => ({ currentUser: null })),
  onAuthStateChanged: vi.fn((auth, callback) => {
    callback(null); // Simulate unauthenticated state
    return vi.fn(); // unsubscribe function
  }),
  signInWithEmailAndPassword: vi.fn(),
  signOut: vi.fn(),
}));

describe('Frontend App Rendering', () => {
  it('navigates to Login page if unauthenticated', () => {
    render(
      <AuthProvider>
        <MemoryRouter initialEntries={['/']}>
          <App />
        </MemoryRouter>
      </AuthProvider>
    );
    
    // AuthContext loads and navigates the empty user to /login
    // Check if the login screen is rendered via standard text lookups
    const heading = screen.getByRole('heading', { name: /login to ars/i });
    expect(heading).toBeInTheDocument();
  });
});
