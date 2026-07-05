import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '@/lib/api';
import type { SessionContext } from '@/types';
import Layout from '@/components/Layout';

interface Ctx {
  value: SessionContext;
  title: string;
  sceneword: string;
  blurb: string;
  accent: string;
  ring: string;
  glyph: string;
}

const CONTEXTS: Ctx[] = [
  {
    value: 'hiring',
    title: 'Hiring',
    sceneword: 'Screening & final rounds',
    blurb: 'Sift a stack of applicants, then pick between finalists for a live opening.',
    accent: 'text-teal-700',
    ring: 'group-hover:border-teal-400',
    glyph: '◎',
  },
  {
    value: 'promotion',
    title: 'Promotion',
    sceneword: 'Who moves up',
    blurb: 'One slot, several people ready for it. Rank them and back your top pick.',
    accent: 'text-amber-700',
    ring: 'group-hover:border-amber-500',
    glyph: '▲',
  },
  {
    value: 'review',
    title: 'Performance review',
    sceneword: 'Rating the work',
    blurb: 'Score half-year write-ups and stack-rank your team for the bonus pool.',
    accent: 'text-clay-700',
    ring: 'group-hover:border-clay-500',
    glyph: '★',
  },
];

export default function HomePage() {
  const navigate = useNavigate();
  const [busy, setBusy] = useState<SessionContext | null>(null);

  const start = async (context: SessionContext) => {
    setBusy(context);
    try {
      const session = await api.createSession(context);
      navigate(`/simulation/${session.id}`);
    } catch {
      setBusy(null);
    }
  };

  return (
    <Layout>
      <section className="mb-10 max-w-2xl animate-rise">
        <p className="eyebrow">Choose a run</p>
        <h1 className="mt-2 font-display text-3xl leading-tight text-ink">
          See how you actually decide
        </h1>
        <p className="mt-3 text-ink-soft">
          Each run puts you in a manager's seat for about ten minutes. Make the calls the way you
          normally would. At the end, you'll see the pattern in your choices, and then find out
          what was really being tested.
        </p>
      </section>

      <div className="grid gap-4 md:grid-cols-3">
        {CONTEXTS.map((c, i) => (
          <button
            key={c.value}
            onClick={() => start(c.value)}
            disabled={busy !== null}
            style={{ animationDelay: `${i * 70}ms` }}
            className={`group flex animate-rise flex-col rounded-xl2 border border-ink-line bg-paper-raised p-6 text-left shadow-card transition-all hover:-translate-y-1 hover:shadow-lift disabled:cursor-wait disabled:opacity-60 ${c.ring}`}
          >
            <div className="flex items-start justify-between">
              <span className={`font-display text-2xl ${c.accent}`}>{c.glyph}</span>
              <span className="font-mono text-[11px] text-ink-faint">10 scenes</span>
            </div>
            <h2 className="mt-4 font-display text-xl text-ink">{c.title}</h2>
            <p className={`mt-0.5 text-xs font-semibold uppercase tracking-wide ${c.accent}`}>
              {c.sceneword ?? c.sceneword}
            </p>
            <p className="mt-3 flex-1 text-sm text-ink-soft">{c.blurb}</p>
            <span className="mt-5 inline-flex items-center gap-1.5 text-sm font-semibold text-ink group-hover:gap-2.5 group-hover:transition-all">
              {busy === c.value ? 'Setting up…' : 'Start run'}
              <span aria-hidden>→</span>
            </span>
          </button>
        ))}
      </div>

      <section className="mt-10 flex flex-wrap gap-x-8 gap-y-2 rounded-xl2 border border-ink-line bg-paper-sunk px-6 py-4 text-sm text-ink-soft">
        <span className="flex items-center gap-2">
          <Dot /> Everyone you see is made up
        </span>
        <span className="flex items-center gap-2">
          <Dot /> No score and no judgement, just a mirror
        </span>
        <span className="flex items-center gap-2">
          <Dot /> Your data stays yours
        </span>
      </section>
    </Layout>
  );
}

function Dot() {
  return <span className="h-1.5 w-1.5 rounded-full bg-teal-400" />;
}
