import { useEffect, useMemo, useRef, useState } from 'react';
import type { DecisionChoice, InboxTriagePayload } from '@/types';
import CandidateCard from '@/components/CandidateCard';
import Button from '@/components/Button';

interface Props {
  payload: InboxTriagePayload;
  onSubmit: (choice: DecisionChoice, elapsedMs: number) => void;
}

export default function InboxTriage({ payload, onSubmit }: Props) {
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [remaining, setRemaining] = useState<number>(payload.timer_seconds ?? 0);
  const startedAt = useMemo(() => Date.now(), []);
  const submittedRef = useRef(false);
  const selectedRef = useRef(selected);
  selectedRef.current = selected;

  const timed = payload.timer_seconds != null;

  useEffect(() => {
    if (!timed || remaining <= 0) return;
    const t = setTimeout(() => setRemaining((r) => r - 1), 1000);
    return () => clearTimeout(t);
  }, [timed, remaining]);

  useEffect(() => {
    if (timed && remaining === 0 && !submittedRef.current) {
      submittedRef.current = true;
      onSubmit({ selected_ids: Array.from(selectedRef.current) }, Date.now() - startedAt);
    }
  }, [timed, remaining, onSubmit, startedAt]);

  const toggle = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else if (next.size < payload.select_count) next.add(id);
      return next;
    });
  };

  const canSubmit = selected.size === payload.select_count;
  const timerLow = timed && remaining <= 15;

  const submit = () => {
    if (submittedRef.current) return;
    submittedRef.current = true;
    onSubmit({ selected_ids: Array.from(selected) }, Date.now() - startedAt);
  };

  return (
    <div>
      <SceneHeader
        role={payload.role}
        instruction={payload.instruction}
        pill={`Pick ${payload.select_count}`}
        timed={timed}
        right={
          timed ? (
            <div className="text-right">
              <p className={`font-mono text-3xl font-bold tabnum ${timerLow ? 'animate-pulse text-clay-500' : 'text-ink'}`}>
                {remaining}s
              </p>
              <p className="text-[11px] text-ink-faint">on the clock</p>
            </div>
          ) : (
            <Counter n={selected.size} of={payload.select_count} />
          )
        }
      />
      {timed && (
        <div className="mb-5 h-1.5 w-full overflow-hidden rounded-full bg-ink-line">
          <div
            className={`h-full transition-all duration-1000 ease-linear ${timerLow ? 'bg-clay-500' : 'bg-amber-500'}`}
            style={{ width: `${(remaining / (payload.timer_seconds || 1)) * 100}%` }}
          />
        </div>
      )}

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {payload.candidates.map((c) => (
          <CandidateCard
            key={c.id}
            candidate={c}
            selected={selected.has(c.id)}
            onClick={() => toggle(c.id)}
          />
        ))}
      </div>

      <StickyBar>
        <span className="text-sm text-ink-soft">
          {selected.size === payload.select_count
            ? 'Looks good — lock it in.'
            : `Choose ${payload.select_count - selected.size} more.`}
        </span>
        <Button onClick={submit} disabled={!canSubmit}>
          Continue
        </Button>
      </StickyBar>
    </div>
  );
}

export function SceneHeader({
  role,
  instruction,
  pill,
  right,
  timed = false,
}: {
  role?: string;
  instruction: string;
  pill?: string;
  right?: React.ReactNode;
  timed?: boolean;
}) {
  return (
    <div
      className={[
        'mb-5 overflow-hidden rounded-xl2 border shadow-card',
        timed ? 'border-clay-500 ring-2 ring-clay-500/30' : 'border-ink-line',
      ].join(' ')}
    >
      {timed && (
        <div className="flex items-center gap-2 bg-clay-500 px-5 py-2 text-white">
          <span className="grid h-4 w-4 place-items-center">
            {/* stopwatch glyph */}
            <svg viewBox="0 0 16 16" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.6">
              <circle cx="8" cy="9" r="5.2" />
              <path d="M8 9V6M8 3.2V1.5M6.4 1.5h3.2" strokeLinecap="round" />
            </svg>
          </span>
          <span className="text-xs font-bold uppercase tracking-[0.14em]">
            Timed round — 60 seconds, decide fast
          </span>
        </div>
      )}
      <div className="flex items-start justify-between gap-4 bg-paper-raised p-5">
        <div className="min-w-0">
          {role && <p className="eyebrow mb-1">{role}</p>}
          <p className="font-display text-lg leading-snug text-ink">{instruction}</p>
          {pill && (
            <span
              className={[
                'mt-2 inline-block rounded-full px-2.5 py-0.5 text-xs font-semibold',
                timed ? 'bg-clay-100 text-clay-700' : 'bg-teal-50 text-teal-700',
              ].join(' ')}
            >
              {pill}
            </span>
          )}
        </div>
        {right && <div className="shrink-0">{right}</div>}
      </div>
    </div>
  );
}

function Counter({ n, of }: { n: number; of: number }) {
  return (
    <div className="text-right">
      <p className="font-mono text-3xl font-bold text-ink tabnum">
        {n}
        <span className="text-ink-faint">/{of}</span>
      </p>
      <p className="text-[11px] text-ink-faint">chosen</p>
    </div>
  );
}

export function StickyBar({ children }: { children: React.ReactNode }) {
  return (
    <div className="sticky bottom-4 mt-6 flex items-center justify-between gap-4 rounded-full border border-ink-line bg-paper-raised/90 px-5 py-3 shadow-lift backdrop-blur">
      {children}
    </div>
  );
}
