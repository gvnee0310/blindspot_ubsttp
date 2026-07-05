import { useMemo, useState } from 'react';
import type { DecisionChoice, PerformanceCalibrationPayload } from '@/types';
import CandidateCard from '@/components/CandidateCard';
import Button from '@/components/Button';
import { SceneHeader, StickyBar } from './InboxTriage';

interface Props {
  payload: PerformanceCalibrationPayload;
  onSubmit: (choice: DecisionChoice, elapsedMs: number) => void;
}

export default function PerformanceCalibration({ payload, onSubmit }: Props) {
  const [ratings, setRatings] = useState<Record<string, number | undefined>>({});
  const startedAt = useMemo(() => Date.now(), []);
  const scale = payload.rating_scale;

  const allRated =
    payload.candidates.length > 0 && payload.candidates.every((c) => ratings[c.id] !== undefined);

  const submit = () => {
    const cleaned: Record<string, number> = {};
    for (const [k, v] of Object.entries(ratings)) if (v !== undefined) cleaned[k] = v;
    onSubmit({ ratings: cleaned }, Date.now() - startedAt);
  };

  return (
    <div>
      <SceneHeader role={payload.role} instruction={payload.instruction} pill="Rate each 1–5" />

      <div className="grid gap-4 md:grid-cols-2">
        {payload.candidates.map((c) => (
          <div key={c.id} className="space-y-3 rounded-xl2 border border-ink-line bg-paper-raised p-4 shadow-card">
            <CandidateCard candidate={c} readonly />
            <div className="border-t border-ink-line pt-3">
              <p className="mb-2 text-xs font-semibold text-ink-soft">Your rating</p>
              <div className="flex gap-1.5">
                {Array.from({ length: scale.max - scale.min + 1 }, (_, i) => scale.min + i).map(
                  (val, i) => {
                    const active = ratings[c.id] === val;
                    return (
                      <button
                        key={val}
                        type="button"
                        title={scale.labels[i]}
                        onClick={() => setRatings((p) => ({ ...p, [c.id]: val }))}
                        className={[
                          'flex h-11 flex-1 flex-col items-center justify-center rounded-lg border text-sm font-bold transition-all',
                          active
                            ? 'border-teal-600 bg-teal-600 text-white shadow-sm'
                            : 'border-ink-line bg-paper text-ink-soft hover:border-teal-400 hover:text-ink',
                        ].join(' ')}
                      >
                        {val}
                      </button>
                    );
                  },
                )}
              </div>
              {ratings[c.id] !== undefined && (
                <p className="mt-2 text-xs text-ink-faint">
                  {scale.labels[(ratings[c.id] as number) - scale.min]}
                </p>
              )}
            </div>
          </div>
        ))}
      </div>

      <StickyBar>
        <span className="text-sm text-ink-soft">
          {allRated ? 'Both rated. Continue when ready.' : 'Give each person a score.'}
        </span>
        <Button onClick={submit} disabled={!allRated}>
          Continue
        </Button>
      </StickyBar>
    </div>
  );
}
