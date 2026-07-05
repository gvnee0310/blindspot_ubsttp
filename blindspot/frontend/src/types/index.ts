// Types mirroring the backend Pydantic schemas. Keep in sync with
// backend/app/schemas.py.

export interface User {
  id: number;
  email: string;
  display_name: string;
}

export interface Token {
  access_token: string;
  token_type: 'bearer';
  user: User;
}

export type SessionContext = 'hiring' | 'promotion' | 'review';

export interface CandidateProfile {
  id: string;
  name: string;
  headline: string;
  years_experience: number;
  education: string;
  skills: string[];
  highlights: string[];
}

// --- Scene payloads ---

export interface InboxTriagePayload {
  role: string;
  instruction: string;
  candidates: CandidateProfile[];
  select_count: number;
  timer_seconds: number | null;
  variant_dimension_label?: string;
}

export interface RatingScale {
  min: number;
  max: number;
  labels: string[];
}

export interface PerformanceCalibrationPayload {
  role: string;
  instruction: string;
  candidates: CandidateProfile[];
  rating_scale: RatingScale;
  variant_dimension_label?: string;
}

export interface PromotionRankingPayload {
  role: string;
  instruction: string;
  candidates: CandidateProfile[];
  requires_justification: boolean;
  variant_dimension_label?: string;
}

export type ScenarioPayload =
  | InboxTriagePayload
  | PerformanceCalibrationPayload
  | PromotionRankingPayload;

export type SceneType =
  | 'inbox_triage'
  | 'performance_calibration'
  | 'promotion_ranking';

export interface Scenario {
  id: number;
  scene_type: SceneType | string;
  order_index: number;
  timed: boolean;
  payload: ScenarioPayload;
}

export interface Session {
  id: number;
  context: SessionContext;
  started_at: string;
  completed_at: string | null;
  scenarios: Scenario[];
}

// --- Decisions ---

export type DecisionChoice =
  | { selected_ids: string[] }
  | { ratings: Record<string, number> }
  | { ranking: string[] }
  | Record<string, unknown>;

export interface DecisionInput {
  scenario_id: number;
  choice: DecisionChoice;
  elapsed_ms?: number | null;
  justification?: string | null;
}

// --- Debrief ---

export interface SceneSummary {
  scene_type: string;
  description: string;
  favoured_privileged: boolean | null;
  elapsed_ms: number | null;
  research_citation: string;
}

export interface ProportionOut {
  favoured: number;
  total: number;
  proportion: number | null;
  ci_low: number | null;
  ci_high: number | null;
}

export interface SceneBreakdownOut {
  scene_type: string;
  n_decisions: number;
  n_favoured: number;
  n_against: number;
  n_ambiguous: number;
  proportion: ProportionOut;
  expected_rate: number | null;
}

export interface PairedComparisonOut {
  n_pairs: number;
  mean_difference: number;
  sd_difference: number | null;
  t_statistic: number | null;
  p_value: number | null;
  ci_low: number | null;
  ci_high: number | null;
}

export interface TimedSplitOut {
  untimed: ProportionOut;
  timed: ProportionOut;
  difference: number | null;
  diff_ci_low: number | null;
  diff_ci_high: number | null;
  reliability: 'firm' | 'tentative' | 'too_thin';
}

export interface DimensionBreakdownOut {
  dimension: string;
  group_a: string;
  group_b: string;
  n_favoured_a: number;
  n_trials: number;
}

export interface DescriptiveOut {
  overall: ProportionOut;
  by_scene: SceneBreakdownOut[];
  paired_ratings: PairedComparisonOut | null;
  n_ties: number;
  timed_split: TimedSplitOut | null;
  by_dimension: DimensionBreakdownOut[];
  n_conflict: number;
  n_conflict_overrode_merit: number;
}

export interface RevealItem {
  scene_type: string;
  headline: string;
  privileged_names: string[];
  counterpart_names: string[];
  what_you_did: string;
}

export interface BayesianOut {
  posterior_mean: number;
  hdi_low: number;
  hdi_high: number;
  prob_p_above_half: number;
  prob_p_above_60: number;
  prob_p_below_40: number;
  prob_in_rope: number;
  prior_prob_in_rope: number;
  rope_low: number;
  rope_high: number;
  n_observations: number;
  n_favoured: number;
  samples: number[];
}

export interface Debrief {
  session_id: number;
  headline: string;
  narrative: string[];
  scenes: SceneSummary[];
  descriptive: DescriptiveOut;
  bayesian: BayesianOut;
  reveal: RevealItem[];
}
