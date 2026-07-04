import { useMemo, useState } from 'react';
import type { DecisionChoice, PromotionRankingPayload } from '@/types';
import CandidateCard from '@/components/CandidateCard';
import Button from '@/components/Button';
import { SceneHeader, StickyBar } from './InboxTriage';

interface Props {
  payload: PromotionRankingPayload;
  onSubmit: (choice: DecisionChoice, elapsedMs: number, justification: string) => void;
}

export default function PromotionRanking({ payload, onSubmit }: Props) {
  const initial = useMemo(() => payload.candidates.map((c) => c.id), [payload.candidates]);
  const [order, setOrder] = useState<string[]>(initial);
  const [why, setWhy] = useState('');
  const startedAt = useMemo(() => Date.now(), []);
  const byId = useMemo(
    () => Object.fromEntries(payload.candidates.map((c) => [c.id, c])),
    [payload.candidates],
  );

  const move = (idx: number, dir: -1 | 1) => {
    const j = idx + dir;
    if (j < 0 || j >= order.length) return;
    setOrder((prev) => {
      const next = [...prev];
      [next[idx], next[j]] = [next[j], next[idx]];
      return next;
    });
  };

  const canSubmit = !payload.requires_justification || why.trim().length >= 15;

  return (
    <div>
      <SceneHeader
        role={payload.role}
        instruction={payload.instruction}
        pill="Drag order with ↑ ↓"
      />

      <ol className="space-y-3">
        {order.map((id, idx) => {
          const c = byId[id];
          if (!c) return null;
          return (
            <li key={id} className="flex items-stretch gap-3">
              <div className="flex flex-col justify-center gap-1">
                <IconBtn label="up" disabled={idx === 0} onClick={() => move(idx, -1)}>
                  ↑
                </IconBtn>
                <IconBtn
                  label="down"
                  disabled={idx === order.length - 1}
                  onClick={() => move(idx, 1)}
                >
                  ↓
                </IconBtn>
              </div>
              <div className="flex-1">
                <CandidateCard candidate={c} readonly rank={idx + 1} />
              </div>
            </li>
          );
        })}
      </ol>

      {payload.requires_justification && (
        <div className="mt-5 rounded-xl2 border border-ink-line bg-paper-raised p-5 shadow-card">
          <label htmlFor="why" className="block font-display text-base text-ink">
            Why {byId[order[0]]?.name.split(' ')[0]} first?
          </label>
          <p className="mt-1 text-xs text-ink-soft">
            A sentence or two (at least 15 characters). This is just for your own reflection — it
            isn't graded.
          </p>
          <textarea
            id="why"
            value={why}
            onChange={(e) => setWhy(e.target.value)}
            rows={3}
            maxLength={2000}
            placeholder="e.g. Strongest delivery record and clearest impact of the three."
            className={`mt-3 block w-full rounded-lg border bg-paper px-3.5 py-2.5 text-sm text-ink placeholder:text-ink-faint focus:outline-none focus:ring-1 ${
              why.trim().length > 0 && why.trim().length < 15
                ? 'border-clay-500 focus:border-clay-500 focus:ring-clay-500'
                : 'border-ink-line focus:border-teal-400 focus:ring-teal-400'
            }`}
          />
          <div className="mt-1.5 flex items-center justify-between text-xs">
            <span className={why.trim().length < 15 ? 'text-clay-700' : 'text-balance-700'}>
              {why.trim().length < 15
                ? `${15 - why.trim().length} more character${15 - why.trim().length === 1 ? '' : 's'} to go`
                : 'Looks good'}
            </span>
            <span className="font-mono text-ink-faint tabnum">{why.trim().length}/15</span>
          </div>
        </div>
      )}

      <StickyBar>
        <span className="text-sm text-ink-soft">
          {canSubmit
            ? 'Ready when you are.'
            : payload.requires_justification && why.trim().length < 15
              ? 'Add a short note on your top pick to continue.'
              : 'Add a quick note on your top pick.'}
        </span>
        <Button
          onClick={() => onSubmit({ ranking: order }, Date.now() - startedAt, why.trim())}
          disabled={!canSubmit}
        >
          Continue
        </Button>
      </StickyBar>
    </div>
  );
}

function IconBtn({
  children,
  onClick,
  disabled,
  label,
}: {
  children: React.ReactNode;
  onClick: () => void;
  disabled?: boolean;
  label: string;
}) {
  return (
    <button
      type="button"
      aria-label={label}
      onClick={onClick}
      disabled={disabled}
      className="grid h-8 w-8 place-items-center rounded-lg border border-ink-line bg-paper-raised font-mono text-ink-soft transition-colors hover:border-teal-400 hover:text-teal-700 disabled:opacity-30"
    >
      {children}
    </button>
  );
}
