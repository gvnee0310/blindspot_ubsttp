import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api } from '@/lib/api';
import type { BayesianOut, Debrief, DescriptiveOut, RevealItem, TimedSplitOut } from '@/types';
import Button from '@/components/Button';
import Layout from '@/components/Layout';

type Verdict = 'lean-favoured' | 'lean-overlooked' | 'balanced' | 'unclear';

// Turn **bold** markers from the backend into emphasised spans.
function renderBold(text: string) {
  return text.split(/(\*\*[^*]+\*\*)/g).map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return (
        <strong key={i} className="font-semibold text-ink">
          {part.slice(2, -2)}
        </strong>
      );
    }
    return <span key={i}>{part}</span>;
  });
}

function readVerdict(b: BayesianOut): Verdict {
  // Mirror the backend's ROPE decision rule exactly (narrative.classify_verdict):
  // a lean needs 85% of posterior mass beyond the balanced zone, not just past 0.5.
  if (b.n_observations < 3) return 'unclear';
  if (b.prob_p_above_60 >= 0.85) return 'lean-favoured';
  if (b.prob_p_below_40 >= 0.85) return 'lean-overlooked';
  if (b.prob_in_rope >= 0.5 && b.prob_in_rope > b.prior_prob_in_rope) return 'balanced';
  return 'unclear';
}

const VERDICT_COPY: Record<Verdict, { tag: string; tone: string; line: string }> = {
  'lean-favoured': {
    tag: 'A lean showed up',
    tone: 'clay',
    line: 'When two people looked the same on paper, you picked the favoured name more often than the other.',
  },
  'lean-overlooked': {
    tag: 'A lean showed up',
    tone: 'clay',
    line: 'When two people looked the same on paper, you picked the overlooked name more often than the other.',
  },
  balanced: {
    tag: 'Balanced run',
    tone: 'balance',
    line: 'You went by the work, not the name. The names barely moved your choices this time.',
  },
  unclear: {
    tag: 'Too close to call',
    tone: 'teal',
    line: "Your choices don't point clearly one way or the other yet. Another run would give a sharper read.",
  },
};

function BalanceDial({ b }: { b: BayesianOut }) {
  const toAngle = (p: number) => (p - 0.5) * 160;
  const needle = toAngle(b.posterior_mean);
  const arcFrom = toAngle(b.hdi_low);
  const arcTo = toAngle(b.hdi_high);
  const polar = (deg: number, r = 82) => {
    const rad = ((deg - 90) * Math.PI) / 180;
    return [100 + r * Math.cos(rad), 105 + r * Math.sin(rad)];
  };
  const [x1, y1] = polar(arcFrom);
  const [x2, y2] = polar(arcTo);
  const large = Math.abs(arcTo - arcFrom) > 180 ? 1 : 0;

  // The 95% range arc takes the colour of the side the needle sits on:
  // red/clay when leaning favoured (right), teal when leaning overlooked
  // (left), soft grey when it straddles the balanced middle.
  const rangeColor =
    b.hdi_low > 0.6 ? '#C56A4E' : b.hdi_high < 0.4 ? '#0E7C7B' : '#B7B2A6';

  const arc = (fromDeg: number, toDeg: number) => {
    const [ax, ay] = polar(fromDeg);
    const [bx, by] = polar(toDeg);
    const lg = Math.abs(toDeg - fromDeg) > 180 ? 1 : 0;
    return `M ${ax} ${ay} A 82 82 0 ${lg} 1 ${bx} ${by}`;
  };

  return (
    <svg viewBox="0 0 200 122" className="w-full max-w-xs" role="img"
      aria-label={`Dial pointing ${b.posterior_mean > 0.6 ? 'toward favoured' : b.posterior_mean < 0.4 ? 'toward overlooked' : 'to balanced'}`}>
      {/* base track */}
      <path d="M 18 105 A 82 82 0 0 1 182 105" fill="none" stroke="#E4DFD4" strokeWidth="10" strokeLinecap="round" />
      {/* overlooked side (left) — teal */}
      <path d={arc(-80, -17)} fill="none" stroke="#C6E3E1" strokeWidth="10" strokeLinecap="round" />
      {/* balanced middle — green */}
      <path d={arc(-15, 15)} fill="none" stroke="#B7E0AF" strokeWidth="10" strokeLinecap="round" />
      {/* favoured side (right) — red/clay */}
      <path d={arc(17, 80)} fill="none" stroke="#EBC4B6" strokeWidth="10" strokeLinecap="round" />
      {/* 95% range highlight, coloured by the side it lands on */}
      <path
        d={`M ${x1} ${y1} A 82 82 0 ${large} 1 ${x2} ${y2}`}
        fill="none" stroke={rangeColor} strokeWidth="4" strokeLinecap="round" opacity="0.95"
      />
      <text x="14" y="120" fill="#0A5F5E" fontSize="8" fontWeight="600" fontFamily="Inter">overlooked</text>
      <text x="86" y="120" fill="#3E7A38" fontSize="8" fontWeight="600" fontFamily="Inter">balanced</text>
      <text x="150" y="120" fill="#9E4E36" fontSize="8" fontWeight="600" fontFamily="Inter">favoured</text>
      <g className="animate-needle" style={{ transformOrigin: '100px 105px', ['--to' as string]: `${needle}deg` }}>
        <line x1="100" y1="105" x2="100" y2="34" stroke="#1A1D21" strokeWidth="2.5" strokeLinecap="round" />
        <circle cx="100" cy="105" r="6" fill="#1A1D21" />
        <circle cx="100" cy="105" r="2.5" fill="#FBF9F4" />
      </g>
    </svg>
  );
}

const TONE: Record<string, { bg: string; text: string; chip: string }> = {
  clay: { bg: 'bg-clay-100', text: 'text-clay-700', chip: 'bg-clay-500' },
  balance: { bg: 'bg-balance-100', text: 'text-balance-700', chip: 'bg-balance-500' },
  teal: { bg: 'bg-teal-50', text: 'text-teal-700', chip: 'bg-teal-600' },
};

export default function DebriefPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const [d, setD] = useState<Debrief | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!sessionId) return;
    api.getDebrief(Number(sessionId)).then(setD).catch(() => setError('Could not load your debrief.'));
  }, [sessionId]);

  if (error)
    return (
      <Layout>
        <div className="rounded-xl2 border border-clay-500/30 bg-clay-100 p-4 text-sm text-clay-700">{error}</div>
      </Layout>
    );

  if (!d)
    return (
      <Layout>
        <div className="flex flex-col items-center gap-3 py-20 text-center">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-ink-line border-t-teal-600" />
          <p className="text-sm text-ink-soft">Reading your run…</p>
          <p className="text-xs text-ink-faint">The first debrief takes a few seconds to compute.</p>
        </div>
      </Layout>
    );

  const verdict = readVerdict(d.bayesian);
  const copy = VERDICT_COPY[verdict];
  const tone = TONE[copy.tone];

  return (
    <Layout>
      <section className="animate-rise overflow-hidden rounded-xl2 border border-ink-line bg-paper-raised shadow-card">
        <div className="grid gap-6 p-6 md:grid-cols-[1fr_auto] md:items-center md:p-8">
          <div>
            <span className={`inline-flex items-center gap-1.5 rounded-full ${tone.bg} px-3 py-1 text-xs font-semibold ${tone.text}`}>
              <span className={`h-1.5 w-1.5 rounded-full ${tone.chip}`} />
              {copy.tag}
            </span>
            <h1 className="mt-3 font-display text-2xl leading-tight text-ink md:text-3xl">{copy.line}</h1>
            <p className="mt-3 text-sm text-ink-soft">
              Based on {d.bayesian.n_observations} matched calls where two people were equally qualified.
            </p>
          </div>
          <div className="flex flex-col items-center">
            <BalanceDial b={d.bayesian} />
          </div>
        </div>
        {/* Plain-language key: what the two ends of the dial mean. */}
        <div className="grid gap-px border-t border-ink-line bg-ink-line sm:grid-cols-2">
          <div className="bg-paper-raised px-6 py-3">
            <p className="text-xs">
              <span className="font-semibold text-clay-700">Favoured</span>
              <span className="text-ink-soft">: the names that tend to get picked more often in real hiring studies. In Singapore that's usually Chinese names, men, or Western names, depending on the comparison.</span>
            </p>
          </div>
          <div className="bg-paper-raised px-6 py-3">
            <p className="text-xs">
              <span className="font-semibold text-teal-700">Overlooked</span>
              <span className="text-ink-soft">: the names on the other side of that research. They get passed over more often when everything else is equal.</span>
            </p>
          </div>
        </div>
      </section>

      <section className="mt-4 grid animate-rise gap-3 sm:grid-cols-3">
        <StatChip
          label="Balanced zone"
          value={`${Math.round(d.bayesian.prob_in_rope * 100)}%`}
          sub={`How likely it is that you have no real preference either way. ${
            d.bayesian.prob_in_rope > d.bayesian.prior_prob_in_rope
              ? `Up from ${Math.round(d.bayesian.prior_prob_in_rope * 100)}%, which was the starting point before you made any choices.`
              : `The starting point before any choices was ${Math.round(d.bayesian.prior_prob_in_rope * 100)}%.`
          }`}
        />
        <StatChip
          label="Lean toward favoured"
          value={`${Math.round(d.bayesian.prob_p_above_half * 100)}%`}
          sub="How likely it is that you lean toward the favoured names at all. 50% is a coin flip, meaning no evidence either way."
        />
        <StatChip
          label="Even match-ups"
          value={`${d.descriptive.overall.favoured}/${d.descriptive.overall.total}`}
          sub="On the calls where both people were exactly equal, how many went to the favoured name. Only fully tied pairs count here."
        />
      </section>

      <section className="mt-4 rounded-xl2 border border-ink-line bg-paper-raised p-6 shadow-card">
        <p className="eyebrow mb-3">What stood out</p>
        <ul className="space-y-3">
          {d.narrative.map((p, i) => (
            <li key={i} className="flex gap-3 text-[15px] leading-relaxed text-ink">
              <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-teal-600" />
              <span>{renderBold(p)}</span>
            </li>
          ))}
        </ul>
      </section>

      <TimedSplitView split={d.descriptive.timed_split} />

      {d.descriptive.by_dimension.length > 0 && <ByGroup descriptive={d.descriptive} />}

      <Reveal reveal={d.reveal} ties={d.descriptive.n_ties} />

      <HowItWorks b={d.bayesian} />

      <div className="mt-8 flex flex-wrap justify-end gap-3">
        <Link to="/history"><Button variant="secondary">Past runs</Button></Link>
        <Link to="/"><Button>Run another</Button></Link>
      </div>
    </Layout>
  );
}

function StatChip({ label, value, sub }: { label: string; value: string; sub: string }) {
  return (
    <div className="animate-rise rounded-xl2 border border-ink-line bg-paper-raised p-4 shadow-card">
      <p className="eyebrow">{label}</p>
      <p className="mt-1 font-mono text-2xl font-bold text-ink tabnum">{value}</p>
      <p className="mt-0.5 text-xs text-ink-faint">{sub}</p>
    </div>
  );
}

function TimedSplitView({ split }: { split: TimedSplitOut | null }) {
  if (!split || split.timed.total === 0) {
    return (
      <section className="mt-4 rounded-xl2 border border-ink-line bg-paper-raised p-6 shadow-card">
        <p className="eyebrow">Snap decisions</p>
        <h2 className="mt-1 font-display text-lg text-ink">With the clock vs without</h2>
        <p className="mt-2 text-sm text-ink-soft">
          The two timed scenes this run didn't land on matched pairs, so there's nothing clean to
          compare here yet. It fills in over another run or two.
        </p>
      </section>
    );
  }

  const un = split.untimed.total;
  const tn = split.timed.total;
  const up = split.untimed.proportion != null ? Math.round(split.untimed.proportion * 100) : null;
  const tp = split.timed.proportion != null ? Math.round(split.timed.proportion * 100) : null;
  const diff = split.difference != null ? Math.round(split.difference * 100) : null;

  const REL: Record<string, { label: string; cls: string }> = {
    firm: { label: 'Fairly reliable', cls: 'bg-balance-100 text-balance-700' },
    tentative: { label: 'Small sample, read with care', cls: 'bg-amber-100 text-amber-700' },
    too_thin: { label: 'Too little data to trust', cls: 'bg-clay-100 text-clay-700' },
  };
  const rel = REL[split.reliability] ?? REL.too_thin;

  return (
    <section className="mt-4 rounded-xl2 border border-ink-line bg-paper-raised p-6 shadow-card">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="eyebrow">Snap decisions</p>
          <h2 className="mt-1 font-display text-lg text-ink">With the clock vs without</h2>
        </div>
        <span className={`shrink-0 rounded-full px-2.5 py-1 text-xs font-semibold ${rel.cls}`}>
          {rel.label}
        </span>
      </div>
      <p className="mt-1 text-sm text-ink-soft">
        Two scenes ran on a 60-second timer. When people are rushed, they tend to go with their
        first instinct, which is where habits show up most. So it's worth checking whether you
        picked the favoured names more often when you were under time pressure.
      </p>

      {/* Two rates as opposing bars */}
      <div className="mt-4 space-y-3">
        <RateBar label="No timer" pct={up} count={split.untimed.favoured} total={un} tone="teal" />
        <RateBar label="On the timer" pct={tp} count={split.timed.favoured} total={tn} tone="clay" />
      </div>

      {/* The headline difference, stated honestly */}
      {diff != null && (
        <div className="mt-4 rounded-lg bg-paper-sunk px-4 py-3">
          {split.reliability === 'too_thin' ? (
            <p className="text-sm text-ink-soft">
              Your rate {diff > 0 ? 'went up' : diff < 0 ? 'went down' : 'stayed the same'}{' '}
              {diff !== 0 && (
                <><strong className="font-semibold text-ink">{Math.abs(diff)} points</strong>{' '}</>
              )}
              under the clock. But with only {tn} timed and {un} untimed call{tn + un === 1 ? '' : 's'},
              that comes down to{' '}
              <strong className="font-semibold text-ink">one or two picks</strong>. That isn't
              enough to call it a real pattern yet. Take it as something to watch, not a conclusion.
            </p>
          ) : (
            <>
              <p className="text-sm text-ink">
                Under time pressure, you picked the favoured name{' '}
                <strong className="font-semibold">
                  {diff > 0 ? `${diff} points more often` : diff < 0 ? `${Math.abs(diff)} points less often` : 'at the same rate'}
                </strong>
                .
              </p>
              {split.diff_ci_low != null && split.diff_ci_high != null && (
                <p className="mt-1 text-xs text-ink-faint">
                  The best single estimate is {diff > 0 ? '+' : ''}{diff}%, but the true figure
                  could reasonably fall anywhere from{' '}
                  <span className="font-mono tabnum">
                    {Math.round(split.diff_ci_low * 100)}% to {Math.round(split.diff_ci_high * 100)}%
                  </span>
                  {split.diff_ci_low <= 0 && split.diff_ci_high >= 0
                    ? '. That range still includes zero, so "no real change" is possible. A few more runs would narrow it down.'
                    : '. The whole range points the same way, which is a real signal worth noting.'}
                </p>
              )}
            </>
          )}
        </div>
      )}
    </section>
  );
}

function RateBar({
  label, pct, count, total, tone,
}: { label: string; pct: number | null; count: number; total: number; tone: 'teal' | 'clay' }) {
  const bar = tone === 'clay' ? 'bg-clay-500' : 'bg-teal-600';
  return (
    <div>
      <div className="mb-1 flex items-baseline justify-between text-sm">
        <span className="font-medium text-ink">{label}</span>
        <span className="font-mono text-xs text-ink-faint tabnum">
          {count}/{total}{pct != null && <span className="ml-1 text-ink">({pct}%)</span>}
        </span>
      </div>
      <div className="h-3 w-full overflow-hidden rounded-full bg-paper-sunk">
        <div className={`h-full rounded-full ${bar} transition-all`} style={{ width: `${pct ?? 0}%` }} />
      </div>
    </div>
  );
}

function ByGroup({ descriptive }: { descriptive: DescriptiveOut }) {
  return (
    <section className="mt-4 rounded-xl2 border border-ink-line bg-paper-raised p-6 shadow-card">
      <p className="eyebrow">Where it showed up</p>
      <h2 className="mt-1 font-display text-lg text-ink">Broken down by comparison</h2>
      <p className="mt-1 text-sm text-ink-soft">
        Each scene changed only one thing at a time and kept everything else the same. That's the
        only way to tell whether a choice was really about that one thing. So a gender scene shows
        two people of the same race, and a race scene shows two people of the same gender.
      </p>
      <div className="mt-4 space-y-4">
        {descriptive.by_dimension.map((dim) => {
          const pct = dim.n_trials ? (dim.n_favoured_a / dim.n_trials) * 100 : 50;
          const balanced = Math.abs(pct - 50) < 12;
          const held = HELD_CONSTANT[dim.dimension] ?? '';
          return (
            <div key={dim.dimension}>
              <div className="mb-1.5 flex items-center justify-between text-sm">
                <span className="font-medium text-ink">
                  {dim.group_a} vs {dim.group_b}
                  {held && <span className="ml-1.5 font-normal text-ink-faint">({held})</span>}
                </span>
                <span className="font-mono text-xs text-ink-faint tabnum">
                  {dim.n_favoured_a}/{dim.n_trials}
                </span>
              </div>
              <div className="relative h-7 overflow-hidden rounded-lg bg-paper-sunk">
                <div className="absolute left-1/2 top-0 z-10 h-full w-px bg-ink-line" />
                <div
                  className={`flex h-full items-center justify-end pr-2 text-[11px] font-semibold text-white transition-all ${
                    balanced ? 'bg-balance-500' : pct > 50 ? 'bg-clay-500' : 'bg-teal-600'
                  }`}
                  style={{ width: `${pct}%` }}
                >
                  {Math.round(pct)}%
                </div>
              </div>
              <div className="mt-1 flex justify-between text-[11px] text-ink-faint">
                <span>{dim.group_b}</span>
                <span>even</span>
                <span>{dim.group_a}</span>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}

const HELD_CONSTANT: Record<string, string> = {
  gender: 'same race',
  race: 'same gender',
  nationality: 'same gender',
};

function Reveal({ reveal, ties }: { reveal: RevealItem[]; ties: number }) {
  const [open, setOpen] = useState(false);
  const shown = open ? reveal : reveal.slice(0, 5);
  return (
    <section className="mt-4 rounded-xl2 border border-ink-line bg-ink p-6 text-paper shadow-card">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-teal-400">The reveal</p>
      <h2 className="mt-1 font-display text-lg text-paper">They were the same person</h2>
      <p className="mt-1 text-sm text-paper/70">
        Every comparison was a matched pair. Both people had the same experience and the same wins,
        just reworded so they didn't look identical. The only thing that changed was the name.
        {ties > 0 && ` You rated ${ties} of them exactly the same.`}
      </p>
      <ul className="mt-4 space-y-2">
        {shown.map((r, i) => (
          <li key={i} className="rounded-lg bg-paper/5 px-3.5 py-2.5 text-sm">
            <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5 text-paper/60">
              <span className="font-medium text-paper">{r.headline}</span>
              <span className="text-teal-400">·</span>
              <span>{r.privileged_names.join(', ')}</span>
              <span className="text-paper/30">vs</span>
              <span>{r.counterpart_names.join(', ')}</span>
            </div>
            <p className="mt-0.5 text-paper/90">{r.what_you_did}</p>
          </li>
        ))}
      </ul>
      {reveal.length > 5 && (
        <button onClick={() => setOpen((o) => !o)} className="mt-3 text-xs font-semibold text-teal-400 hover:underline">
          {open ? 'Show fewer' : `Show all ${reveal.length}`}
        </button>
      )}
    </section>
  );
}

function HowItWorks({ b }: { b: BayesianOut }) {
  const [open, setOpen] = useState(false);
  return (
    <section className="mt-4 rounded-xl2 border border-ink-line bg-paper-raised shadow-card">
      <button onClick={() => setOpen((o) => !o)} className="flex w-full items-center justify-between px-6 py-4 text-left">
        <span className="font-display text-base text-ink">How we worked this out</span>
        <span className={`font-mono text-ink-faint transition-transform ${open ? 'rotate-45' : ''}`}>+</span>
      </button>
      {open && (
        <div className="space-y-4 border-t border-ink-line px-6 py-5 text-sm leading-relaxed text-ink-soft">
          <div>
            <p className="font-semibold text-ink">We start by assuming nothing.</p>
            <p className="mt-1">
              Before you made a single choice, the model gave you the benefit of the doubt. It began
              at a 50/50 starting point, with no assumption that you lean one way or the other.
            </p>
          </div>
          <div>
            <p className="font-semibold text-ink">Each matched call adjusts the estimate.</p>
            <p className="mt-1">
              Every time two equally qualified people differed only by name, your pick moved the
              estimate a little. A few scenes were harder, because the person with the favoured name
              was actually the <em>weaker</em> candidate. Picking that person says more than a normal
              call, so it counts for more.
            </p>
          </div>
          <div>
            <p className="font-semibold text-ink">The result is a range, not a single verdict.</p>
            <p className="mt-1">
              One run is still a small sample, so instead of a single number we show a range of what's
              likely. That's the light band on the dial. Your most likely value is{' '}
              <span className="font-mono text-ink tabnum">{Math.round(b.posterior_mean * 100)}%</span>{' '}
              toward the favoured side, and the honest range runs from{' '}
              <span className="font-mono text-ink tabnum">
                {Math.round(b.hdi_low * 100)}% to {Math.round(b.hdi_high * 100)}%
              </span>. The balanced zone is the green stretch near the middle.
            </p>
          </div>
          <p className="rounded-lg bg-paper-sunk px-3 py-2 text-xs text-ink-faint">
            For anyone who wants the technical detail: this uses Bayesian inference, with a logistic
            model fit in PyMC. The centre band on the dial is a region of practical equivalence, and
            the light arc is the 95% highest-density interval. Doing more runs narrows it.
          </p>
        </div>
      )}
    </section>
  );
}
