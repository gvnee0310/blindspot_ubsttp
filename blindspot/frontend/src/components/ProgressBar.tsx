interface Props {
  current: number;
  total: number;
  label?: string;
}

export default function ProgressBar({ current, total, label }: Props) {
  return (
    <div className="w-full">
      {label && (
        <div className="mb-2 flex items-center justify-between">
          <span className="eyebrow">{label}</span>
          <span className="font-mono text-xs text-ink-faint tabnum">
            {current}/{total}
          </span>
        </div>
      )}
      <div className="flex gap-1.5" role="progressbar" aria-valuenow={current} aria-valuemax={total}>
        {Array.from({ length: total }, (_, i) => (
          <div
            key={i}
            className={`h-1.5 flex-1 rounded-full transition-colors duration-300 ${
              i < current ? 'bg-teal-600' : 'bg-ink-line'
            }`}
          />
        ))}
      </div>
    </div>
  );
}
