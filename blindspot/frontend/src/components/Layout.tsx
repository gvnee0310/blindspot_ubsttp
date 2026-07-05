import type { ReactNode } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { clearAuth, getStoredUser } from '@/lib/api';

export default function Layout({ children }: { children: ReactNode }) {
  const user = getStoredUser();
  const navigate = useNavigate();
  const signOut = () => {
    clearAuth();
    navigate('/login', { replace: true });
  };

  return (
    <div className="min-h-screen bg-paper">
      <header className="sticky top-0 z-20 border-b border-ink-line/70 bg-paper/85 backdrop-blur">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
          <Link to="/" className="group flex items-center gap-2.5">
            <span className="grid h-7 w-7 place-items-center rounded-full border border-teal-600">
              <span className="h-2.5 w-2.5 rounded-full bg-teal-600 transition-transform group-hover:translate-x-0.5" />
            </span>
            <span className="font-display text-lg font-600 tracking-tight text-ink">
              Blindspot
            </span>
          </Link>
          {user && (
            <nav className="flex items-center gap-5 text-sm">
              <Link to="/history" className="text-ink-soft hover:text-ink">
                Past runs
              </Link>
              <span className="hidden text-ink-faint sm:inline">{user.display_name}</span>
              <button onClick={signOut} className="text-ink-soft hover:text-ink">
                Sign out
              </button>
            </nav>
          )}
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-6 py-10">{children}</main>
    </div>
  );
}
