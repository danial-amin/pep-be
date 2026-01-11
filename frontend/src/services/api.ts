import axios from 'axios';

// Get API URL from runtime config (injected at container startup) or build-time env var
const getApiUrl = (): string => {
  // Check for runtime config (injected via config.js)
  if (typeof window !== 'undefined' && (window as any).APP_CONFIG?.VITE_API_URL) {
    return (window as any).APP_CONFIG.VITE_API_URL;
  }
  // Fallback to build-time env var or default
  return import.meta.env.VITE_API_URL || 'http://localhost:8080/api/v1';
};

const API_URL = getApiUrl();

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

