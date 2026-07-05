import type { CandidateProfile } from '@/types';

interface Props {
  candidate: CandidateProfile;
  selected?: boolean;
  onClick?: () => void;
  readonly?: boolean;
  rank?: number;
}

function initials(name: string): string {
  return name.split(/\s+/).map((p) => p[0]).slice(0, 2).join('').toUpperCase();
}

export default function CandidateCard({ candidate, selected, onClick, readonly, rank }: Props) {
  const interactive = !readonly && Boolean(onClick);
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={!interactive}
      aria-pressed={selected}
      className={[
        'group relative flex w-full flex-col gap-3 rounded-xl2 border bg-paper-raised p-4 text-left transition-all',
        interactive ? 'cursor-pointer hover:-translate-y-0.5 hover:shadow-card' : 'cursor-default',
        selected
          ? 'border-teal-600 shadow-card ring-1 ring-teal-600'
          : 'border-ink-line hover:border-teal-400',
      ].join(' ')}
    >
      {selected && (
        <span className="absolute -right-2 -top-2 grid h-6 w-6 place-items-center rounded-full bg-teal-600 text-xs font-bold text-white shadow-sm">
          ✓
        </span>
      )}
      {rank !== undefined && (
        <span className="absolute -left-2 -top-2 grid h-7 w-7 place-items-center rounded-full bg-ink text-xs font-bold text-paper shadow-sm">
          {rank}
        </span>
      )}
      <div className="flex items-center gap-3">
        <div
          className={[
            'grid h-11 w-11 shrink-0 place-items-center rounded-full font-mono text-sm font-semibold',
            selected ? 'bg-teal-600 text-white' : 'bg-teal-50 text-teal-700',
          ].join(' ')}
        >
          {initials(candidate.name)}
        </div>
        <div className="min-w-0">
          <p className="truncate font-semibold text-ink">{candidate.name}</p>
          <p className="truncate text-xs text-ink-soft">{candidate.headline}</p>
        </div>
      </div>
      <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-ink-soft">
        <span>
          <span className="font-mono font-semibold text-ink tabnum">
            {candidate.years_experience}
          </span>{' '}
          yrs
        </span>
        <span className="truncate">{candidate.education}</span>
      </div>
      <div className="flex flex-wrap gap-1">
        {candidate.skills.slice(0, 4).map((s) => (
          <span
            key={s}
            className="rounded-full bg-paper-sunk px-2 py-0.5 text-[11px] text-ink-soft"
          >
            {s}
          </span>
        ))}
      </div>
      <ul className="space-y-1 border-t border-ink-line pt-2.5 text-xs leading-relaxed text-ink-soft">
        {candidate.highlights.map((h, i) => (
          <li key={i} className="flex gap-1.5">
            <span className="mt-1 h-1 w-1 shrink-0 rounded-full bg-teal-400" />
            <span>{h}</span>
          </li>
        ))}
      </ul>
    </button>
  );
}
