import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8080/api/v1';

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Documents API
export const documentsApi = {
  process: async (file: File, documentType: 'context' | 'interview') => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('document_type', documentType);
    
    const response = await api.post('/documents/process', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  getAll: async (documentType?: 'context' | 'interview') => {
    const params = documentType ? { document_type: documentType } : {};
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
    outputFormat: string = 'json'
  ) => {
    const response = await api.post('/personas/generate-set', {
      num_personas: numPersonas,
      context_details: contextDetails,
      interview_topic: interviewTopic,
      user_study_design: userStudyDesign,
      include_ethical_guardrails: includeEthicalGuardrails,
      output_format: outputFormat,
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

export default api;

