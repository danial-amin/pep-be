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

const AUTH_TOKEN_KEY = 'pep_access_token';

export type AuthUser = {
  id: number;
  email: string;
  name: string;
  is_admin: boolean;
  is_active: boolean;
  created_at: string;
  is_study_participant?: boolean;
  study_id?: number | null;
  study_slug?: string | null;
  participant_code?: string | null;
};

export type InviteRecord = {
  id: number;
  email: string;
  token: string;
  invited_by_id: number;
  accepted_at?: string | null;
  expires_at: string;
  created_at: string;
  note?: string | null;
  accept_path?: string;
};

export const getAuthToken = (): string | null => {
  try {
    return localStorage.getItem(AUTH_TOKEN_KEY);
  } catch {
    return null;
  }
};

export const setAuthToken = (token: string) => {
  localStorage.setItem(AUTH_TOKEN_KEY, token);
};

export const clearAuthToken = () => {
  localStorage.removeItem(AUTH_TOKEN_KEY);
};

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use((config) => {
  const token = getAuthToken();
  if (token) {
    config.headers = config.headers || {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401) {
      const url = String(error?.config?.url || '');
      const isAuthPublic =
        url.includes('/auth/login') ||
        url.includes('/auth/accept-invite') ||
        (url.includes('/auth/invites/') && url.includes('/preview')) ||
        url.includes('/study/');
      if (!isAuthPublic) {
        clearAuthToken();
        if (typeof window !== 'undefined') {
          const path = window.location.pathname;
          if (path.startsWith('/login') || path.startsWith('/invite')) {
            return Promise.reject(error);
          }
          let studySlug: string | null = null;
          try {
            studySlug = localStorage.getItem('pep_study_slug');
          } catch {
            studySlug = null;
          }
          if (!studySlug && path.startsWith('/study/')) {
            studySlug = path.split('/')[2] || null;
          }
          // Default entry for this deployment is the user study, not /login
          window.location.href = `/study/${studySlug || 'policy-study'}`;
        }
      }
    }
    return Promise.reject(error);
  },
);

export const authApi = {
  login: async (email: string, password: string) => {
    const response = await api.post('/auth/login', { email, password });
    return response.data as { access_token: string; token_type: string; user: AuthUser };
  },

  me: async () => {
    const response = await api.get('/auth/me');
    return response.data as AuthUser;
  },

  previewInvite: async (token: string) => {
    const response = await api.get(`/auth/invites/${token}/preview`);
    return response.data as { email: string; expires_at: string; note?: string | null; valid: boolean };
  },

  acceptInvite: async (token: string, name: string, password: string) => {
    const response = await api.post('/auth/accept-invite', { token, name, password });
    return response.data as { access_token: string; token_type: string; user: AuthUser };
  },

  createInvite: async (email: string, note?: string, expiresInDays?: number) => {
    const response = await api.post('/auth/invites', {
      email,
      note,
      expires_in_days: expiresInDays,
    });
    return response.data as InviteRecord;
  },

  listInvites: async () => {
    const response = await api.get('/auth/invites');
    return response.data as InviteRecord[];
  },
};

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
    projectId?: number,
    stakeholderGroups?: string[],
    options?: {
      rqeThreshold?: number;
      maxIterations?: number;
      autoIterate?: boolean;
    }
  ) => {
    const response = await api.post('/personas/generate-set', {
      num_personas: numPersonas,
      context_details: contextDetails,
      interview_topic: interviewTopic,
      user_study_design: userStudyDesign,
      include_ethical_guardrails: includeEthicalGuardrails,
      output_format: outputFormat,
      project_id: projectId,
      ...(stakeholderGroups && stakeholderGroups.length > 0
        ? { stakeholder_groups: stakeholderGroups }
        : {}),
      rqe_threshold: options?.rqeThreshold ?? 0.75,
      max_iterations: options?.maxIterations ?? 3,
      auto_iterate: options?.autoIterate ?? true,
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

  getAllSets: async (projectId?: number) => {
    const params: Record<string, number> = {};
    if (projectId !== undefined) params.project_id = projectId;
    const response = await api.get('/personas/sets', { params });
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

// Persona Chat API — single persona or full persona-set conversations
export const personaChatApi = {
  createSession: async (personaId: number, projectId?: number, resume = true) => {
    const response = await api.post('/persona-chats/', {
      persona_id: personaId,
      project_id: projectId,
      resume,
    });
    return response.data;
  },

  createSetSession: async (personaSetId: number, projectId?: number, resume = true) => {
    const response = await api.post('/persona-chats/', {
      persona_set_id: personaSetId,
      project_id: projectId,
      resume,
    });
    return response.data;
  },

  getSession: async (sessionId: number) => {
    const response = await api.get(`/persona-chats/${sessionId}`);
    return response.data;
  },

  sendMessage: async (sessionId: number, message: string, strictMode = false) => {
    const response = await api.post(
      `/persona-chats/${sessionId}/messages`,
      { message, strict_mode: strictMode },
      { timeout: 180000 },
    );
    return response.data;
  },

  deleteSession: async (sessionId: number) => {
    await api.delete(`/persona-chats/${sessionId}`);
  },
};

export const analyticsApi = {
  recordProfileView: async (payload: {
    persona_set_id: number;
    view_type: 'persona' | 'set_profiles';
    duration_seconds: number;
    persona_id?: number | null;
    started_at?: string | null;
    ended_at?: string | null;
  }) => {
    const response = await api.post('/analytics/profile-views', payload);
    return response.data;
  },

  getProfileViews: async (personaSetId: number) => {
    const response = await api.get(`/analytics/persona-sets/${personaSetId}/profile-views`);
    return response.data;
  },
};

export type StudyPublicInfo = {
  slug: string;
  name: string;
  enabled: boolean;
  welcome_text?: string | null;
  persona_set_id: number;
  project_id?: number | null;
};

export const studyApi = {
  getPublic: async (slug: string): Promise<StudyPublicInfo> => {
    const response = await api.get(`/study/${slug}`);
    return response.data;
  },

  enter: async (slug: string, code: string) => {
    const response = await api.post(`/study/${slug}/enter`, { code });
    return response.data as {
      access_token: string;
      study: StudyPublicInfo;
      participant: { id: number; code: string; display_name?: string | null };
      user: AuthUser;
    };
  },

  getPersonas: async (slug: string) => {
    const response = await api.get(`/study/${slug}/personas`);
    return response.data as {
      study_slug: string;
      persona_set_id: number;
      project_id?: number | null;
      persona_order: number[];
      order_condition?: string | null;
      order_rotation_index?: number | null;
      order_groups?: string[] | null;
      has_order_rotations?: boolean;
      participant_code?: string | null;
      personas: Array<{
        id: number;
        persona_set_id: number;
        name: string;
        persona_data: Record<string, any>;
        image_url?: string | null;
        stakeholder_group?: string | null;
      }>;
    };
  },

  updatePersonaOrder: async (slug: string, personaOrder: number[]) => {
    const response = await api.put(`/study/${slug}/persona-order`, {
      persona_order: personaOrder,
    });
    return response.data;
  },

  recordEvent: async (
    slug: string,
    eventType: string,
    path?: string,
    payload?: Record<string, unknown>
  ) => {
    try {
      await api.post(`/study/${slug}/events`, {
        event_type: eventType,
        path,
        payload,
      });
    } catch {
      /* best-effort instrumentation */
    }
  },

  adminListStudies: async () => {
    const response = await api.get('/study/admin/studies');
    return response.data as Array<{
      id: number;
      slug: string;
      name: string;
      enabled: boolean;
      project_id?: number | null;
      persona_set_id: number;
      participant_count: number;
      event_count: number;
    }>;
  },

  adminGetStudy: async (slug: string) => {
    const response = await api.get(`/study/admin/studies/${slug}`);
    return response.data as {
      id: number;
      slug: string;
      name: string;
      enabled: boolean;
      project_id?: number | null;
      persona_set_id: number;
      persona_order?: number[] | null;
      order_rotations?: string[][] | null;
      allow_open_codes: boolean;
      max_participants: number;
      welcome_text?: string | null;
    };
  },

  adminUpdateStudy: async (
    slug: string,
    body: {
      name?: string;
      enabled?: boolean;
      project_id?: number | null;
      persona_set_id?: number;
      persona_order?: number[];
      order_rotations?: string[][] | null;
      allow_open_codes?: boolean;
      max_participants?: number;
      welcome_text?: string | null;
      rebuild_rotations?: boolean;
    }
  ) => {
    const response = await api.put(`/study/admin/studies/${slug}`, body);
    return response.data;
  },

  adminListParticipants: async (slug: string) => {
    const response = await api.get(`/study/admin/studies/${slug}/participants`);
    return response.data as Array<{
      id: number;
      code: string;
      display_name?: string | null;
      user_id?: number | null;
      created_at?: string | null;
      last_seen_at?: string | null;
      event_count: number;
      is_test: boolean;
    }>;
  },

  adminListEvents: async (slug: string, participantCode?: string, limit = 500) => {
    const response = await api.get(`/study/admin/studies/${slug}/events`, {
      params: {
        participant_code: participantCode || undefined,
        limit,
      },
    });
    return response.data as Array<{
      id: number;
      study_id: number;
      participant_id?: number | null;
      participant_code?: string | null;
      user_id?: number | null;
      event_type: string;
      path?: string | null;
      payload?: Record<string, unknown> | null;
      created_at?: string | null;
    }>;
  },
};

export default api;

