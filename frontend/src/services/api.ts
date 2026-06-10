import axios from 'axios';

// Get API URL from runtime config (injected at container startup) or build-time env var
export const getApiUrl = (): string => {
  // Check for runtime config (injected via config.js)
  if (typeof window !== 'undefined' && (window as any).APP_CONFIG?.VITE_API_URL) {
    return (window as any).APP_CONFIG.VITE_API_URL;
  }
  // Fallback to build-time env var or default
  return import.meta.env.VITE_API_URL || 'http://localhost:8080/api/v1';
};

const API_URL = getApiUrl();
export const API_BASE_URL = API_URL;

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Documents API
export const documentsApi = {
  process: async (file: File, documentType: 'context' | 'interview', projectId?: number) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('document_type', documentType);
    if (projectId !== undefined) {
      formData.append('project_id', projectId.toString());
    }
    
    const response = await api.post('/documents/process', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  getAll: async (projectId?: number, documentType?: 'context' | 'interview') => {
    const params: any = {};
    if (projectId) params.project_id = projectId;
    if (documentType) params.document_type = documentType;
    const response = await api.get('/documents/', { params });
    return response.data;
  },

  getById: async (id: number) => {
    const response = await api.get(`/documents/${id}`);
    return response.data;
  },

  /** Retry processing for a document stuck in pending/processing. */
  retry: async (id: number) => {
    const response = await api.post(`/documents/${id}/retry`);
    return response.data;
  },

  delete: async (id: number) => {
    await api.delete(`/documents/${id}`);
  },
};

// Personas API
export const personasApi = {
  generateSet: async (
    numPersonas: number = 3,
    contextDetails?: string,
    interviewTopic?: string,
    userStudyDesign?: string,
    includeEthicalGuardrails: boolean = true,
    outputFormat: string = 'json',
    projectId?: number
  ) => {
    const response = await api.post('/personas/generate-set', {
      num_personas: numPersonas,
      context_details: contextDetails,
      interview_topic: interviewTopic,
      user_study_design: userStudyDesign,
      include_ethical_guardrails: includeEthicalGuardrails,
      output_format: outputFormat,
      project_id: projectId,
    });
    return response.data;
  },

  expand: async (personaSetId: number) => {
    const response = await api.post(`/personas/${personaSetId}/expand`);
    return response.data;
  },

  generateImages: async (personaSetId: number) => {
    const response = await api.post(`/personas/${personaSetId}/generate-images`);
    return response.data;
  },

  saveSet: async (personaSetId: number, name?: string, description?: string) => {
    const params = new URLSearchParams();
    if (name) params.append('name', name);
    if (description) params.append('description', description);
    
    const response = await api.post(
      `/personas/${personaSetId}/save?${params.toString()}`
    );
    return response.data;
  },

  getAllSets: async () => {
    const response = await api.get('/personas/sets');
    return response.data;
  },

  getSet: async (personaSetId: number) => {
    const response = await api.get(`/personas/sets/${personaSetId}`);
    return response.data;
  },

  getPersona: async (personaId: number) => {
    const response = await api.get(`/personas/${personaId}`);
    return response.data;
  },

  measureDiversity: async (personaSetId: number) => {
    const response = await api.post(`/personas/${personaSetId}/measure-diversity`);
    return response.data;
  },

  validate: async (personaSetId: number) => {
    const response = await api.post(`/personas/${personaSetId}/validate`);
    return response.data;
  },

  getAnalytics: async (personaSetId: number) => {
    const response = await api.get(`/personas/${personaSetId}/analytics`);
    return response.data;
  },

  downloadJson: async (personaSetId: number) => {
    const response = await api.get(`/personas/${personaSetId}/download`, {
      responseType: 'blob',
    });
    return response.data;
  },

  loadDefaultPersonas: async () => {
    const response = await api.post('/personas/load-default-personas');
    return response.data;
  },

  generateImage: async (personaId: number) => {
    const response = await api.post(`/personas/persona/${personaId}/generate-image`);
    return response.data;
  },

  // Verification endpoints - Semantic similarity verification
  verifyPersona: async (
    personaId: number,
    options?: {
      similarity_threshold?: number;
      use_indirect_similarity?: boolean;
      filter_low_similarity?: boolean;
      project_id?: number;
    }
  ) => {
    const response = await api.post(`/personas/persona/${personaId}/verify`, options || {});
    return response.data;
  },

  verifyPersonaSet: async (
    personaSetId: number,
    options?: {
      similarity_threshold?: number;
      use_indirect_similarity?: boolean;
      filter_low_similarity?: boolean;
      project_id?: number;
      force?: boolean;
    }
  ) => {
    const response = await api.post(`/personas/${personaSetId}/verify`, options || {});
    return response.data;
  },

  getVerifiedPersona: async (
    personaId: number,
    similarity_threshold: number = 0.80,
    project_id?: number
  ) => {
    const params: any = { similarity_threshold };
    if (project_id) params.project_id = project_id;
    const response = await api.get(`/personas/persona/${personaId}/verified`, { params });
    return response.data;
  },
};

// Prompts API
export const promptsApi = {
  complete: async (prompt: string, maxTokens: number = 1000) => {
    const response = await api.post('/prompts/complete', {
      prompt,
      max_tokens: maxTokens,
    });
    return response.data;
  },
};

// Simulations API - Multi-persona conversation playground
export const simulationsApi = {
  create: async (request: {
    name: string;
    goal: string;
    goal_context?: string;
    /** Personas may come from different persona sets */
    participants: Array<{ persona_id: number; role?: string }>;
    max_duration_seconds?: number;
    max_tokens?: number;
    max_turns?: number;
    project_id?: number;
    /** Keep running beyond max_turns until agreement threshold is reached */
    run_until_agreement?: boolean;
    /** 0.0–1.0 pairwise alignment score required to stop */
    agreement_threshold?: number;
  }) => {
    const response = await api.post('/simulations/', request);
    return response.data;
  },

  getAll: async (projectId?: number, status?: string) => {
    const params: any = {};
    if (projectId) params.project_id = projectId;
    if (status) params.status = status;
    const response = await api.get('/simulations/', { params });
    return response.data;
  },

  getById: async (id: number) => {
    const response = await api.get(`/simulations/${id}`);
    return response.data;
  },

  start: async (id: number, autoContinue: boolean = true) => {
    const response = await api.post(`/simulations/${id}/start`, {
      auto_continue: autoContinue
    });
    return response.data;
  },

  nextTurn: async (id: number) => {
    const response = await api.post(`/simulations/${id}/next-turn`);
    return response.data;
  },

  /** Add a human facilitator intervention; next persona turn will address it with strong weight */
  intervene: async (id: number, content: string) => {
    const response = await api.post(`/simulations/${id}/intervene`, { content });
    return response.data;
  },

  stop: async (id: number) => {
    const response = await api.post(`/simulations/${id}/stop`);
    return response.data;
  },

  generateSummary: async (id: number) => {
    const response = await api.post(`/simulations/${id}/summary`);
    return response.data;
  },

  /** Get full simulation export (setup, conversations, summaries, agreement history) */
  getDownload: async (id: number) => {
    const response = await api.get(`/simulations/${id}/download`);
    return response.data;
  },

  delete: async (id: number) => {
    await api.delete(`/simulations/${id}`);
  },

  /**
   * Return the full time-series agreement history for a simulation.
   * Each entry is a snapshot taken after a complete round showing overall score,
   * per-persona drift, and pairwise alignment.
   */
  getAgreementHistory: async (id: number) => {
    const response = await api.get(`/simulations/${id}/agreement-history`);
    return response.data;
  },

  /**
   * Manually trigger an agreement evaluation at the current turn.
   * Works regardless of whether run_until_agreement is enabled.
   */
  evaluateAgreement: async (id: number) => {
    const response = await api.post(`/simulations/${id}/evaluate-agreement`);
    return response.data;
  },

  /** Run LLM-as-judge evaluation for a completed/stopped simulation */
  evaluate: async (id: number, force = false) => {
    const response = await api.post(`/simulations/${id}/evaluate`, { force });
    return response.data;
  },

  /** Get stored LLM-as-judge scores for a simulation */
  getEvaluationScores: async (id: number) => {
    const response = await api.get(`/simulations/${id}/evaluation-scores`);
    return response.data;
  },
};

// Projects API
export const projectsApi = {
  create: async (project: {
    name: string;
    field_of_study?: string;
    core_objective?: string;
    includes_context: boolean;
    includes_interviews: boolean;
  }) => {
    const response = await api.post('/projects/', project);
    return response.data;
  },

  getAll: async () => {
    const response = await api.get('/projects/');
    return response.data;
  },

  getById: async (id: number) => {
    const response = await api.get(`/projects/${id}`);
    return response.data;
  },

  update: async (id: number, project: {
    name?: string;
    field_of_study?: string;
    core_objective?: string;
    includes_context?: boolean;
    includes_interviews?: boolean;
  }) => {
    const response = await api.put(`/projects/${id}`, project);
    return response.data;
  },

  delete: async (id: number) => {
    await api.delete(`/projects/${id}`);
  },
};

export default api;

