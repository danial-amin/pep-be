export type DocumentType = 'context' | 'interview';

export interface Document {
  id: number;
  filename: string;
  document_type: DocumentType;
  content: string;
  processed_content?: string;
  vector_id?: string;
  created_at: string;
  updated_at?: string;
}

export interface DocumentProcessResponse {
  id: number;
  filename: string;
  document_type: DocumentType;
  processed: boolean;
  vector_id?: string;
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
