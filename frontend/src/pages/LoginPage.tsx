import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { ApiError, api, storeAuth } from '@/lib/api';
import Button from '@/components/Button';

type Mode = 'login' | 'register';

export default function LoginPage() {
  const navigate = useNavigate();
  const [mode, setMode] = useState<Mode>('register');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const token =
        mode === 'login'
          ? await api.login(email, password)
          : await api.register(email, displayName, password);
      storeAuth(token);
      navigate('/', { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : 'Something went wrong.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      {/* Left: the thesis */}
      <div className="relative hidden flex-col justify-between overflow-hidden bg-ink p-12 text-paper lg:flex">
        <div className="flex items-center gap-2.5">
          <span className="grid h-7 w-7 place-items-center rounded-full border border-teal-400">
            <span className="h-2.5 w-2.5 rounded-full bg-teal-400" />
          </span>
          <span className="font-display text-lg">Blindspot</span>
        </div>
        <div className="max-w-md">
          <h1 className="font-display text-4xl leading-[1.1] text-paper">
            You can't see your own blind spot.
          </h1>
          <p className="mt-4 text-paper/70">
            That's what makes it a blind spot. You'll make a series of everyday calls, like who to
            interview, who to promote, and how to rate someone's work. Then you'll see a pattern in
            your choices that's hard to notice in the moment.
          </p>
        </div>
        <p className="font-mono text-xs text-paper/40">
          Every candidate is fictional. Nothing you do here is shared or scored against you.
        </p>
        {/* ambient instrument marks */}
        <div className="pointer-events-none absolute -right-24 top-1/3 h-72 w-72 rounded-full border border-paper/10" />
        <div className="pointer-events-none absolute -right-10 top-1/2 h-40 w-40 rounded-full border border-teal-400/20" />
      </div>

      {/* Right: the form */}
      <div className="flex items-center justify-center bg-paper px-6 py-16">
        <div className="w-full max-w-sm">
          <div className="mb-8 lg:hidden">
            <span className="font-display text-2xl">Blindspot</span>
          </div>
          <h2 className="font-display text-2xl text-ink">
            {mode === 'login' ? 'Welcome back' : 'Create your account'}
          </h2>
          <p className="mt-1 text-sm text-ink-soft">
            {mode === 'login'
              ? 'Pick up where you left off.'
              : 'Takes a few seconds. Use anything you like.'}
          </p>

          <form onSubmit={submit} className="mt-8 space-y-4">
            {mode === 'register' && (
              <Field label="Your name">
                <input
                  type="text"
                  required
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  className={inputCls}
                  placeholder="Alex"
                />
              </Field>
            )}
            <Field label="Email">
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className={inputCls}
                placeholder="you@example.com"
              />
            </Field>
            <Field label="Password">
              <input
                type="password"
                required
                minLength={8}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className={inputCls}
                placeholder="At least 8 characters"
              />
            </Field>

            {error && (
              <p className="rounded-lg bg-clay-100 px-3 py-2 text-sm text-clay-700">{error}</p>
            )}

            <Button type="submit" disabled={busy} className="w-full">
              {busy ? 'One moment…' : mode === 'login' ? 'Sign in' : 'Start'}
            </Button>
          </form>

          <p className="mt-6 text-center text-sm text-ink-soft">
            {mode === 'login' ? 'New here?' : 'Already have an account?'}{' '}
            <button
              onClick={() => {
                setMode(mode === 'login' ? 'register' : 'login');
                setError(null);
              }}
              className="font-semibold text-teal-700 hover:underline"
            >
              {mode === 'login' ? 'Create an account' : 'Sign in'}
            </button>
          </p>
        </div>
      </div>
    </div>
  );
}

const inputCls =
  'block w-full rounded-lg border border-ink-line bg-paper-raised px-3.5 py-2.5 text-sm text-ink placeholder:text-ink-faint focus:border-teal-400 focus:outline-none focus:ring-1 focus:ring-teal-400';

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-sm font-medium text-ink-soft">{label}</span>
      {children}
    </label>
  );
}
