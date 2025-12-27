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
  created_at: string;
  updated_at?: string;
}

export interface PersonaSet {
  id: number;
  name: string;
  description?: string;
  personas: Persona[];
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

