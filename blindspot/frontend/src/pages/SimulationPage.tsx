import { useCallback, useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { api } from '@/lib/api';
import type { DecisionChoice, Scenario, Session } from '@/types';
import Layout from '@/components/Layout';
import ProgressBar from '@/components/ProgressBar';
import InboxTriage from '@/scenes/InboxTriage';
import PerformanceCalibration from '@/scenes/PerformanceCalibration';
import PromotionRanking from '@/scenes/PromotionRanking';

function renderScene(
  sc: Scenario,
  onDecision: (choice: DecisionChoice, ms: number, justification?: string) => void,
) {
  switch (sc.scene_type) {
    case 'inbox_triage':
      return <InboxTriage payload={sc.payload as never} onSubmit={(c, ms) => onDecision(c, ms)} />;
    case 'performance_calibration':
      return (
        <PerformanceCalibration payload={sc.payload as never} onSubmit={(c, ms) => onDecision(c, ms)} />
      );
    case 'promotion_ranking':
      return (
        <PromotionRanking
          payload={sc.payload as never}
          onSubmit={(c, ms, j) => onDecision(c, ms, j)}
        />
      );
    default:
      return null;
  }
}

export default function SimulationPage() {
  const navigate = useNavigate();
  const { sessionId } = useParams<{ sessionId: string }>();
  const [session, setSession] = useState<Session | null>(null);
  const [idx, setIdx] = useState(0);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!sessionId) return;
    api.getSession(Number(sessionId)).then(setSession).catch(() => setError('Could not load this run.'));
  }, [sessionId]);

  const onDecision = useCallback(
    async (choice: DecisionChoice, ms: number, justification?: string) => {
      if (!session) return;
      const sc = session.scenarios[idx];
      setWorking(true);
      try {
        await api.submitDecision({
          scenario_id: sc.id,
          choice,
          elapsed_ms: ms,
          justification: justification ?? null,
        });
        if (idx < session.scenarios.length - 1) {
          setIdx(idx + 1);
          window.scrollTo({ top: 0, behavior: 'smooth' });
        } else {
          await api.completeSession(session.id);
          navigate(`/debrief/${session.id}`);
        }
      } catch {
        setError('That didn\'t save. Try again.');
      } finally {
        setWorking(false);
      }
    },
    [session, idx, navigate],
  );

  if (error)
    return (
      <Layout>
        <div className="rounded-xl2 border border-clay-500/30 bg-clay-100 p-4 text-sm text-clay-700">
          {error}
        </div>
      </Layout>
    );

  if (!session)
    return (
      <Layout>
        <p className="text-sm text-ink-soft">Loading…</p>
      </Layout>
    );

  const total = session.scenarios.length;

  return (
    <Layout>
      <div className="mb-6">
        <ProgressBar current={idx + 1} total={total} label={`Scene ${idx + 1} of ${total}`} />
      </div>
      {working ? (
        <p className="text-sm text-ink-soft">Saving…</p>
      ) : (
        <div key={idx} className="animate-rise">
          {renderScene(session.scenarios[idx], onDecision)}
        </div>
      )}
    </Layout>
  );
}
