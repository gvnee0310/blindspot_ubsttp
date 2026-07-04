import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '@/lib/api';
import type { Session } from '@/types';
import Button from '@/components/Button';
import Layout from '@/components/Layout';

function fmt(iso: string): string {
  try {
    return new Date(iso).toLocaleString(undefined, {
      month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit',
    });
  } catch {
    return iso;
  }
}

const LABEL: Record<string, string> = {
  hiring: 'Hiring',
  promotion: 'Promotion',
  review: 'Performance review',
};

export default function HistoryPage() {
  const [sessions, setSessions] = useState<Session[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listSessions().then(setSessions).catch(() => setError('Could not load your past runs.'));
  }, []);

  return (
    <Layout>
      <header className="mb-6 flex items-end justify-between">
        <div>
          <p className="eyebrow">Your history</p>
          <h1 className="mt-1 font-display text-2xl text-ink">Past runs</h1>
        </div>
        <Link to="/"><Button>New run</Button></Link>
      </header>

      {error && (
        <div className="rounded-xl2 border border-clay-500/30 bg-clay-100 p-4 text-sm text-clay-700">{error}</div>
      )}
      {!sessions && !error && <p className="text-sm text-ink-soft">Loading…</p>}

      {sessions && sessions.length === 0 && (
        <div className="rounded-xl2 border border-dashed border-ink-line bg-paper-sunk p-10 text-center">
          <p className="text-sm text-ink-soft">No runs yet — your first one will show up here.</p>
          <Link to="/" className="mt-4 inline-block"><Button>Start a run</Button></Link>
        </div>
      )}

      {sessions && sessions.length > 0 && (
        <ul className="space-y-2.5">
          {sessions.map((s) => (
            <li
              key={s.id}
              className="flex items-center justify-between gap-4 rounded-xl2 border border-ink-line bg-paper-raised p-4 shadow-card"
            >
              <div className="flex items-center gap-4">
                <span className={`h-2.5 w-2.5 rounded-full ${s.completed_at ? 'bg-balance-500' : 'bg-amber-500'}`} />
                <div>
                  <p className="font-medium text-ink">{LABEL[s.context] ?? s.context}</p>
                  <p className="font-mono text-xs text-ink-faint">
                    {fmt(s.started_at)} · {s.completed_at ? 'done' : 'in progress'}
                  </p>
                </div>
              </div>
              {s.completed_at ? (
                <Link to={`/debrief/${s.id}`}><Button variant="secondary">View debrief</Button></Link>
              ) : (
                <Link to={`/simulation/${s.id}`}><Button variant="secondary">Resume</Button></Link>
              )}
            </li>
          ))}
        </ul>
      )}
    </Layout>
  );
}
