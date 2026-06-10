export type DocumentType = 'context' | 'interview';

export type DocumentProcessingStatus = 'pending' | 'processing' | 'completed' | 'failed';

export interface Document {
  id: number;
  filename: string;
  document_type: DocumentType;
  content?: string | null;  // null until background processing completes
  processed_content?: string | null;
  vector_id?: string | null;
  processing_status?: DocumentProcessingStatus;
  processing_error?: string | null;
  created_at: string;
  updated_at?: string;
}

export interface DocumentProcessResponse {
  id: number;
  filename: string;
  document_type: DocumentType;
  processed: boolean;
  processing_status?: DocumentProcessingStatus;
  processing_error?: string | null;
  vector_id?: string | null;
  created_at: string;
}

export interface PersonaBasic {
  name: string;
  age?: number;
  gender?: string;
  location?: string;
  occupation?: string;
  basic_description?: string;
  key_characteristics?: string[];
}

export interface PersonaData {
  name: string;
  age?: number;
  gender?: string;
  location?: string;
  occupation?: string;
  personal_background?: string;
  demographics?: Record<string, any>;
  psychographics?: Record<string, any>;
  behaviors?: Record<string, any>;
  goals_and_challenges?: string;
  technology_usage?: string;
  communication_preferences?: string;
  detailed_description?: string;
  [key: string]: any;
}

export interface Persona {
  id: number;
  persona_set_id: number;
  name: string;
  persona_data: PersonaData;
  image_url?: string;
  image_prompt?: string;
  similarity_score?: {
    average: number;
    max: number;
    min: number;
    scores: number[];
    num_matches: number;
    dummy?: boolean;
  };
  validation_status?: string;
  created_at: string;
  updated_at?: string;
}

export interface PersonaSet {
  id: number;
  name: string;
  description?: string;
  personas: Persona[];
  rqe_scores?: Array<{ cycle: number; rqe_score: number; average_similarity: number; timestamp?: string }>;
  diversity_score?: {
    rqe_score: number;
    average_similarity: number;
    min_similarity: number;
    max_similarity: number;
    std_similarity: number;
    num_personas: number;
  };
  validation_scores?: Array<{
    persona_id: number;
    persona_name: string;
    average_similarity: number;
    max_similarity: number;
    min_similarity: number;
    validation_status: string;
    dummy?: boolean;
  }>;
  generation_cycle?: number;
  status?: string;
  created_at: string;
  updated_at?: string;
}

export interface PersonaSetGenerateResponse {
  persona_set_id: number;
  personas: PersonaBasic[];
  status: string;
}

export interface PromptCompleteRequest {
  prompt: string;
  max_tokens?: number;
}

export interface PromptCompleteResponse {
  completed_text: string;
  context_used: number;
}

export interface Project {
  id: number;
  name: string;
  field_of_study?: string;
  core_objective?: string;
  includes_context: boolean;
  includes_interviews: boolean;
  created_at: string;
  updated_at?: string;
}

// Verification Types - Semantic Similarity Verification
export interface VerificationRequest {
  similarity_threshold?: number;
  use_indirect_similarity?: boolean;
  filter_low_similarity?: boolean;
  project_id?: number;
  force?: boolean;
}

export interface AttributeVerificationResult {
  direct_similarity: number;
  indirect_similarity?: number;
  combined_similarity: number;
  verified: boolean;
  threshold: number;
  source_chunks: string[];
  indirect_path?: Array<{ hop: number; text?: string; similarity: number }>;
}

export interface VerificationMetrics {
  average_direct_similarity: number;
  average_indirect_similarity: number;
  verification_rate: number;
  verified_attributes: number;
  filtered_attributes: number;
  total_attributes: number;
  threshold: number;
}

export interface PersonaVerificationResponse {
  persona_id: number;
  persona_name: string;
  verification_results: Record<string, AttributeVerificationResult>;
  original_persona_data: Record<string, any>;
  filtered_persona_data: Record<string, any>;
  metrics: VerificationMetrics;
  source_references: Record<string, Array<{ text: string; similarity: number }>>;
  validation_status: string;
}

export interface PersonaSetVerificationResponse {
  persona_set_id: number;
  persona_results: PersonaVerificationResponse[];
  aggregate_metrics: {
    average_verification_rate: number;
    average_direct_similarity: number;
    average_indirect_similarity?: number;
    fully_verified_personas: number;
    partially_verified_personas: number;
    successful_verifications?: number;
    total_personas: number;
    threshold: number;
  };
  status: string;
  verified_at: string;
}

export interface VerifiedPersonaResponse {
  persona_id: number;
  persona_name: string;
  verified_persona_data: Record<string, any>;
  verification_rate: number;
  threshold: number;
  source_references: Record<string, Array<{ text: string; similarity: number }>>;
}

// Simulation Types - Multi-persona conversation playground
export interface SimulationParticipantConfig {
  persona_id: number;
  role?: string;
}

export interface SimulationCreateRequest {
  name: string;
  goal: string;
  goal_context?: string;
  /** Personas may come from different persona sets — mix freely */
  participants: SimulationParticipantConfig[];
  max_duration_seconds?: number;
  max_tokens?: number;
  max_turns?: number;
  project_id?: number;
  /** Keep running beyond max_turns until agreement_threshold is reached */
  run_until_agreement?: boolean;
  /** 0.0–1.0 pairwise alignment score needed to stop when run_until_agreement=true */
  agreement_threshold?: number;
}

export interface SimulationMessage {
  id: number;
  persona_id?: number;  // null for human facilitator interventions
  persona_name: string;
  persona_image_url?: string;
  content: string;
  turn_number: number;
  tokens: number;
  is_moderator_message: boolean;
  is_human_message?: boolean;
  /** Populated asynchronously by evaluator; 0=on-persona, 1=fully drifted */
  persona_drift_score?: number;
  created_at: string;
}

export interface SimulationParticipant {
  id: number;
  persona_id: number;
  persona_name: string;
  persona_image_url?: string;
  /** Which persona set this participant came from */
  persona_set_id?: number;
  persona_set_name?: string;
  role?: string;
  messages_count: number;
  tokens_used: number;
}

export interface PersonaSummaryEntry {
  persona_id: number;
  persona_name: string;
  summary: string;
}

// ─── Agreement evaluation types ──────────────────────────────────────────────

export interface PersonaStanceDetail {
  persona_name: string;
  initial_stance: string;
  current_stance: string;
  /** 0.0 = unchanged, 1.0 = completely shifted from original */
  drift_score: number;
  /** Pairwise alignment with every other persona keyed by string persona_id */
  alignment_scores: Record<string, number>;
}

export interface AgreementEvaluation {
  id: number;
  simulation_id: number;
  turn_number: number;
  /** 0.0 = complete disagreement, 1.0 = full agreement */
  overall_agreement_score: number;
  agreement_reached: boolean;
  /** Keyed by string persona_id */
  persona_stances?: Record<string, PersonaStanceDetail>;
  evaluation_reasoning?: string;
  created_at: string;
}

export interface AgreementHistory {
  simulation_id: number;
  agreement_threshold: number;
  agreement_reached: boolean;
  evaluations: AgreementEvaluation[];
}

// ─── LLM-as-judge evaluation types ───────────────────────────────────────────

export interface JudgeScoreEntry {
  judge_model: string;
  level: 'persona' | 'discussion';
  simulation_id: number;
  target_id: number;
  persona_name?: string | null;
  item: string;
  item_type: 'likert' | 'categorical';
  response_code: number | null;
  response_label: string;
  justification: string;
  run_timestamp?: string | null;
}

export interface SimulationEvaluationScores {
  simulation_id: number;
  has_evaluation: boolean;
  judge_models: string[];
  last_evaluated_at?: string | null;
  scores: JudgeScoreEntry[];
}

export interface SimulationEvaluationResult {
  simulation_ids: number[];
  judge_models: string[];
  pass_count: number;
  temperature: number;
  persona_targets: number;
  attempted_runs: number;
  score_rows_written: number;
}

// ─────────────────────────────────────────────────────────────────────────────

export interface Simulation {
  id: number;
  name: string;
  goal: string;
  goal_context?: string;
  max_duration_seconds: number;
  max_tokens: number;
  max_turns: number;
  run_until_agreement: boolean;
  agreement_threshold: number;
  status: 'pending' | 'running' | 'completed' | 'stopped';
  /** Full rounds completed (every participant spoke once per round). */
  current_turn: number;
  tokens_used: number;
  /** Latest agreement snapshot score, if any evaluation has been run */
  latest_agreement_score?: number;
  agreement_reached: boolean;
  started_at?: string;
  completed_at?: string;
  summary?: string;
  persona_summaries?: PersonaSummaryEntry[];
  key_insights?: string[];
  action_items?: string[];
  participants: SimulationParticipant[];
  messages: SimulationMessage[];
  project_id?: number;
  created_at: string;
  updated_at?: string;
}

export interface SimulationListItem {
  id: number;
  name: string;
  goal: string;
  status: string;
  /** Full rounds completed. */
  current_turn: number;
  max_turns: number;
  tokens_used: number;
  max_tokens: number;
  participant_count: number;
  run_until_agreement: boolean;
  latest_agreement_score?: number;
  agreement_reached: boolean;
  started_at?: string;
  completed_at?: string;
  created_at: string;
}

export interface SimulationTurnResponse {
  message: SimulationMessage;
  simulation_status: string;
  current_turn: number;
  tokens_used: number;
  tokens_remaining: number;
  turns_remaining: number;
  is_complete: boolean;
  /** Populated when a full round just completed in run_until_agreement mode */
  agreement_evaluation?: AgreementEvaluation;
}

export interface SimulationSummary {
  simulation_id: number;
  persona_summaries: PersonaSummaryEntry[];
  summary?: string;
  key_insights: string[];
  action_items: string[];
  total_turns: number;
  total_tokens: number;
  duration_seconds?: number;
}
