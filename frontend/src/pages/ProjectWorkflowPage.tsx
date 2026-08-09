import { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Upload, FileText, Users, Sparkles, Image as ImageIcon, BarChart3, CheckCircle, ArrowLeft, Trash2, Loader2, XCircle, Clock, RefreshCw } from 'lucide-react';
import { projectsApi, documentsApi, personasApi } from '../services/api';
import { Project, Document, PersonaSet } from '../types';
import { getPersonaImageUrl } from '../utils/imageUtils';

type WorkflowStep = 'upload' | 'create' | 'optimize' | 'expand' | 'reports';
const POLL_INTERVAL_MS = 3000;

/** Normalize status for display (backend may omit for legacy docs). */
function getDisplayStatus(doc: Document): 'pending' | 'processing' | 'completed' | 'failed' {
  const s = doc.processing_status;
  if (s === 'pending' || s === 'processing' || s === 'failed') return s;
  return 'completed';
}

export default function ProjectWorkflowPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const [project, setProject] = useState<Project | null>(null);
  const [currentStep, setCurrentStep] = useState<WorkflowStep>('upload');
  const [documents, setDocuments] = useState<Document[]>([]);
  const [personaSets, setPersonaSets] = useState<PersonaSet[]>([]);
  const [selectedSet, setSelectedSet] = useState<PersonaSet | null>(null);
  const [loadingSets, setLoadingSets] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [deletingDocumentId, setDeletingDocumentId] = useState<number | null>(null);
  const [retryingDocumentId, setRetryingDocumentId] = useState<number | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Persona generation state
  const [numPersonas, setNumPersonas] = useState(3);
  const [contextDetails, setContextDetails] = useState('');
  const [interviewTopic, setInterviewTopic] = useState('');
  const [outputFormat, setOutputFormat] = useState('json');
  const [stakeholderGroupsText, setStakeholderGroupsText] = useState('');
  const [autoIterate, setAutoIterate] = useState(true);
  const [rqeThreshold, setRqeThreshold] = useState(0.75);
  const [maxIterations, setMaxIterations] = useState(3);
  const [generating, setGenerating] = useState(false);
  const [expanding, setExpanding] = useState(false);
  const [generatingImages, setGeneratingImages] = useState(false);
  const [measuringDiversity, setMeasuringDiversity] = useState(false);

  useEffect(() => {
    if (projectId) {
      setSelectedSet(null);
      setPersonaSets([]);
      loadProject();
      loadDocuments();
      loadPersonaSets();
    }
  }, [projectId]);

  const loadProject = async () => {
    if (!projectId) return;
    try {
      const data = await projectsApi.getById(parseInt(projectId));
      setProject(data);
    } catch (error) {
      console.error('Failed to load project:', error);
    }
  };

  const loadDocuments = useCallback(async () => {
    if (!projectId) return;
    try {
      const data = await documentsApi.getAll(parseInt(projectId));
      setDocuments(data);
      // Auto-advance to create step if documents exist
      if (data.length > 0 && currentStep === 'upload') {
        setCurrentStep('create');
      }
    } catch (error) {
      console.error('Failed to load documents:', error);
    }
  }, [projectId, currentStep]);

  const hasProcessing = documents.some(
    (d) => getDisplayStatus(d) === 'pending' || getDisplayStatus(d) === 'processing'
  );

  useEffect(() => {
    if (!hasProcessing) {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
      return;
    }
    pollRef.current = setInterval(loadDocuments, POLL_INTERVAL_MS);
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [hasProcessing, loadDocuments]);

  const loadPersonaSets = useCallback(async () => {
    if (!projectId) return;
    setLoadingSets(true);
    try {
      const sets: PersonaSet[] = await personasApi.getAllSets(parseInt(projectId));
      setPersonaSets(sets);
      setSelectedSet((prev) => {
        if (prev && sets.some((s) => s.id === prev.id)) {
          return sets.find((s) => s.id === prev.id) ?? prev;
        }
        return sets.length > 0 ? sets[0] : null;
      });
    } catch (error) {
      console.error('Failed to load persona sets:', error);
      setPersonaSets([]);
    } finally {
      setLoadingSets(false);
    }
  }, [projectId]);

  const handleSelectExistingSet = (set: PersonaSet) => {
    setSelectedSet(set);
    setCurrentStep('optimize');
  };

  const handleFileUpload = async (file: File, documentType: 'context' | 'interview') => {
    if (!projectId) return;
    setUploading(true);
    try {
      const response = await documentsApi.process(file, documentType, parseInt(projectId));
      await loadDocuments();
      if (response.processing_status === 'completed' && response.vector_id) {
        alert('Document uploaded and processed successfully!');
      } else if (response.processing_status === 'failed' && response.processing_error) {
        alert(`Document uploaded but processing failed: ${response.processing_error}`);
      } else {
        alert('Document uploaded. Processing runs in the background; the list will update when ready.');
      }
    } catch (error: any) {
      const errorMsg = error.response?.data?.detail || error.message;
      alert(`Failed to upload document: ${errorMsg}`);
      console.error('Document upload error:', error);
    } finally {
      setUploading(false);
    }
  };

  const handleDeleteDocument = async (documentId: number) => {
    setDeletingDocumentId(documentId);
    try {
      await documentsApi.delete(documentId);
      await loadDocuments();
    } catch (error) {
      console.error('Error deleting document:', error);
      alert('Failed to delete document. Please try again.');
    } finally {
      setDeletingDocumentId(null);
    }
  };

  const handleRetryDocument = async (documentId: number) => {
    setRetryingDocumentId(documentId);
    try {
      await documentsApi.retry(documentId);
      await loadDocuments();
    } catch (error: any) {
      const msg = error.response?.data?.detail || error.message || 'Retry failed';
      alert(msg);
    } finally {
      setRetryingDocumentId(null);
    }
  };

  const handleGenerateSet = async () => {
    if (!projectId) return;
    setGenerating(true);
    try {
      const stakeholderGroups = stakeholderGroupsText
        .split(/[\n,]+/)
        .map((s) => s.trim())
        .filter(Boolean);
      const response = await personasApi.generateSet(
        stakeholderGroups.length > 0 ? stakeholderGroups.length : numPersonas,
        contextDetails || undefined,
        interviewTopic || undefined,
        undefined, // userStudyDesign - not used in simplified workflow
        true, // includeEthicalGuardrails - default to true
        outputFormat,
        parseInt(projectId),
        stakeholderGroups.length > 0 ? stakeholderGroups : undefined,
        {
          rqeThreshold,
          maxIterations,
          autoIterate,
        }
      );
      await loadPersonaSets();
      const newSet = await personasApi.getSet(response.persona_set_id);
      setSelectedSet(newSet);
      setCurrentStep('optimize');
      const rqePct =
        response.rqe_score != null ? `${(response.rqe_score * 100).toFixed(1)}%` : 'n/a';
      alert(
        `Persona set generated.\nRQE: ${rqePct}\nIterations: ${response.iterations_used ?? 1}/${maxIterations}`
      );
    } catch (error: any) {
      alert(`Failed to generate personas: ${error.response?.data?.detail || error.message}`);
    } finally {
      setGenerating(false);
    }
  };

  const handleExpand = async () => {
    if (!selectedSet) return;
    setExpanding(true);
    try {
      await personasApi.expand(selectedSet.id);
      await loadPersonaSets();
      const updated = await personasApi.getSet(selectedSet.id);
      setSelectedSet(updated);
      alert('Personas expanded successfully!');
    } catch (error: any) {
      alert(`Failed to expand personas: ${error.response?.data?.detail || error.message}`);
    } finally {
      setExpanding(false);
    }
  };

  const handleGenerateImages = async () => {
    if (!selectedSet) return;
    setGeneratingImages(true);
    try {
      await personasApi.generateImages(selectedSet.id);
      await loadPersonaSets();
      const updated = await personasApi.getSet(selectedSet.id);
      setSelectedSet(updated);
      alert('Images generated successfully!');
    } catch (error: any) {
      alert(`Failed to generate images: ${error.response?.data?.detail || error.message}`);
    } finally {
      setGeneratingImages(false);
    }
  };

  const handleMeasureDiversity = async () => {
    if (!selectedSet) return;
    setMeasuringDiversity(true);
    try {
      const result = await personasApi.measureDiversity(selectedSet.id);
      await loadPersonaSets();
      const updated = await personasApi.getSet(selectedSet.id);
      setSelectedSet(updated);
      const rqe = result?.metrics?.rqe_score;
      const rqePct = rqe != null ? `${(rqe * 100).toFixed(1)}%` : 'n/a';
      alert(`RQE measured: ${rqePct}`);
    } catch (error: any) {
      alert(`Failed to measure diversity: ${error.response?.data?.detail || error.message}`);
    } finally {
      setMeasuringDiversity(false);
    }
  };

  if (!project) {
    return <div className="px-4 py-6 text-stone-900">Loading project...</div>;
  }

  const steps = [
    { id: 'upload', label: 'Upload Data', icon: Upload },
    { id: 'create', label: 'Create Personas', icon: Users },
    { id: 'optimize', label: 'View & Optimize', icon: Sparkles },
    { id: 'expand', label: 'Expand & Images', icon: ImageIcon },
    { id: 'reports', label: 'Reports', icon: BarChart3 },
  ];

  return (
    <div className="px-4 py-6 sm:px-0">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <button
            onClick={() => navigate('/projects')}
            className="mb-2 inline-flex items-center text-stone-600 hover:text-stone-900 transition-colors"
          >
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Projects
          </button>
          <h2 className="text-3xl font-bold text-stone-900 mb-2 ">{project.name}</h2>
          {project.field_of_study && (
            <p className="text-stone-600">{project.field_of_study}</p>
          )}
        </div>
      </div>

      {/* Step Navigation */}
      <div className="glass-card rounded-2xl p-4 mb-6">
        <div className="flex items-center justify-between">
          {steps.map((step, index) => {
            const Icon = step.icon;
            const isActive = currentStep === step.id;
            const isCompleted = steps.findIndex(s => s.id === currentStep) > index;
            return (
              <div key={step.id} className="flex items-center flex-1">
                <button
                  onClick={() => setCurrentStep(step.id as WorkflowStep)}
                  className={`flex items-center space-x-2 px-4 py-2 rounded-lg transition-all ${
                    isActive
                      ? 'bg-stone-100 text-stone-900'
                      : isCompleted
                      ? 'text-stone-600 hover:text-stone-900'
                      : 'text-stone-400'
                  }`}
                >
                  {isCompleted ? (
                    <CheckCircle className="h-5 w-5" />
                  ) : (
                    <Icon className="h-5 w-5" />
                  )}
                  <span className="hidden sm:inline">{step.label}</span>
                </button>
                {index < steps.length - 1 && (
                  <div className={`flex-1 h-0.5 mx-2 ${isCompleted ? 'bg-stone-100' : 'bg-stone-50'}`} />
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Step Content */}
      <div className="glass-card rounded-2xl p-6">
        {currentStep === 'upload' && (
          <div>
            <h3 className="text-2xl font-semibold text-stone-900 mb-6">Upload Documents</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {project.includes_context && (
                <div className="glass-card rounded-xl p-6">
                  <FileText className="mx-auto h-12 w-12 text-stone-700 mb-4" />
                  <h4 className="text-lg font-semibold text-stone-900 mb-2">Context Document</h4>
                  <p className="text-sm text-stone-600 mb-4">Upload research, reports, or background information</p>
                  <label className="inline-flex items-center px-6 py-3 text-sm font-medium rounded-xl text-white bg-stone-900 hover:bg-stone-800 cursor-pointer transition-all">
                    <Upload className="mr-2 h-4 w-4" />
                    {uploading ? 'Uploading...' : 'Upload File'}
                    <input
                      type="file"
                      className="hidden"
                      accept=".pdf,.docx,.txt,.md,.csv"
                      onChange={(e) => {
                        const file = e.target.files?.[0];
                        if (file) handleFileUpload(file, 'context');
                      }}
                      disabled={uploading}
                    />
                  </label>
                </div>
              )}
              {project.includes_interviews && (
                <div className="glass-card rounded-xl p-6">
                  <FileText className="mx-auto h-12 w-12 text-stone-700 mb-4" />
                  <h4 className="text-lg font-semibold text-stone-900 mb-2">Interview Document</h4>
                  <p className="text-sm text-stone-600 mb-4">Upload interview transcripts or user research</p>
                  <label className="inline-flex items-center px-6 py-3 text-sm font-medium rounded-xl text-white bg-stone-900 hover:bg-stone-800 cursor-pointer transition-all">
                    <Upload className="mr-2 h-4 w-4" />
                    {uploading ? 'Uploading...' : 'Upload File'}
                    <input
                      type="file"
                      className="hidden"
                      accept=".pdf,.docx,.txt,.md,.csv"
                      onChange={(e) => {
                        const file = e.target.files?.[0];
                        if (file) handleFileUpload(file, 'interview');
                      }}
                      disabled={uploading}
                    />
                  </label>
                </div>
              )}
            </div>
            {documents.length > 0 && (
              <div className="mt-6">
                <div className="flex items-center justify-between gap-3 mb-4">
                  <h4 className="text-lg font-semibold text-stone-900">Uploaded Documents</h4>
                  <button
                    type="button"
                    onClick={() => loadDocuments()}
                    className="inline-flex items-center gap-2 px-3 py-2 rounded-xl bg-stone-100 hover:bg-stone-100 text-sm font-medium text-stone-900"
                    title="Refresh"
                  >
                    <RefreshCw className="h-4 w-4" />
                    Refresh
                  </button>
                </div>
                <div className="space-y-2">
                  {documents.map((doc) => (
                    <div key={doc.id} className="flex items-center justify-between gap-3 p-3 bg-stone-50 rounded-lg">
                      <span className="text-stone-700 truncate">{doc.filename}</span>
                      <div className="flex items-center gap-2">
                        {(() => {
                          const status = getDisplayStatus(doc);
                          if (status === 'pending') {
                            return (
                              <span className="flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded-full bg-amber-50 text-amber-700 border border-amber-200">
                                <Clock className="h-3.5 w-3.5" /> Queued
                              </span>
                            );
                          }
                          if (status === 'processing') {
                            return (
                              <span className="flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded-full bg-blue-50 text-blue-700 border border-blue-200">
                                <Loader2 className="h-3.5 w-3.5 animate-spin" /> Processing
                              </span>
                            );
                          }
                          if (status === 'failed') {
                            return (
                              <span className="flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded-full bg-red-50 text-red-700 border border-red-200">
                                <XCircle className="h-3.5 w-3.5" /> Failed
                              </span>
                            );
                          }
                          return (
                            <span className="flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded-full bg-green-50 text-green-700 border border-green-200">
                              <CheckCircle className="h-3.5 w-3.5" /> Ready
                            </span>
                          );
                        })()}
                        <span className={`px-3 py-1 text-xs rounded-full ${
                          doc.document_type === 'context' ? 'bg-violet-50 border border-violet-200 text-violet-700' : 'bg-pink-50 border border-pink-200 text-pink-700'
                        }`}>
                          {doc.document_type}
                        </span>
                        {(getDisplayStatus(doc) === 'pending' || getDisplayStatus(doc) === 'processing' || getDisplayStatus(doc) === 'failed') && (
                          <button
                            type="button"
                            onClick={() => handleRetryDocument(doc.id)}
                            disabled={retryingDocumentId === doc.id}
                            className="inline-flex items-center justify-center h-8 w-8 rounded-full text-stone-600 hover:text-stone-900 hover:bg-stone-50 disabled:opacity-50"
                            aria-label={`Retry processing ${doc.filename}`}
                            title="Retry processing"
                          >
                            {retryingDocumentId === doc.id ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                              <RefreshCw className="h-4 w-4" />
                            )}
                          </button>
                        )}
                        <button
                          type="button"
                          onClick={() => handleDeleteDocument(doc.id)}
                          disabled={deletingDocumentId === doc.id}
                          className="inline-flex items-center justify-center h-8 w-8 rounded-full text-stone-600 hover:text-stone-900 hover:bg-stone-50 disabled:opacity-50"
                          aria-label={`Delete ${doc.filename}`}
                          title="Delete document"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
                <button
                  onClick={() => setCurrentStep('create')}
                  className="mt-4 px-6 py-3 bg-stone-900 text-white rounded-xl  transition-all"
                >
                  Continue to Create Personas
                </button>
              </div>
            )}
          </div>
        )}

        {currentStep === 'create' && (
          <div>
            <h3 className="text-2xl font-semibold text-stone-900 mb-6">Create Persona Set</h3>

            <div className="mb-8">
              <div className="flex items-center justify-between gap-3 mb-3">
                <h4 className="text-lg font-semibold text-stone-900">Existing persona sets</h4>
                <button
                  type="button"
                  onClick={() => loadPersonaSets()}
                  disabled={loadingSets}
                  className="inline-flex items-center gap-2 px-3 py-2 rounded-xl bg-stone-100 hover:bg-stone-200 text-sm font-medium text-stone-900 disabled:opacity-50"
                  title="Refresh"
                >
                  {loadingSets ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
                  Refresh
                </button>
              </div>
              {loadingSets && personaSets.length === 0 ? (
                <p className="text-sm text-stone-500">Loading persona sets…</p>
              ) : personaSets.length === 0 ? (
                <p className="text-sm text-stone-500">
                  No persona sets for this project yet. Generate one below.
                </p>
              ) : (
                <div className="space-y-2">
                  {personaSets.map((set) => {
                    const isSelected = selectedSet?.id === set.id;
                    return (
                      <div
                        key={set.id}
                        className={`flex items-center justify-between gap-3 p-3 rounded-xl border ${
                          isSelected
                            ? 'border-stone-900 bg-stone-50'
                            : 'border-stone-200 bg-white'
                        }`}
                      >
                        <div className="min-w-0">
                          <p className="font-medium text-stone-900 truncate">{set.name}</p>
                          <p className="text-sm text-stone-500">
                            {set.personas?.length ?? 0} persona{(set.personas?.length ?? 0) !== 1 ? 's' : ''}
                            {set.status ? ` · ${set.status}` : ''}
                          </p>
                        </div>
                        <div className="flex items-center gap-2 shrink-0">
                          <button
                            type="button"
                            onClick={() => navigate(`/personas/${set.id}/profiles`)}
                            className="px-3 py-2 text-sm rounded-lg text-stone-700 hover:bg-stone-100"
                          >
                            All profiles
                          </button>
                          <button
                            type="button"
                            onClick={() => navigate(`/personas/${set.id}`)}
                            className="px-3 py-2 text-sm rounded-lg text-stone-700 hover:bg-stone-100"
                          >
                            View
                          </button>
                          <button
                            type="button"
                            onClick={() => handleSelectExistingSet(set)}
                            className="px-4 py-2 text-sm font-medium rounded-lg bg-stone-900 text-white hover:bg-stone-800"
                          >
                            Use this set
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            <div className="border-t border-stone-200 pt-6">
              <h4 className="text-lg font-semibold text-stone-900 mb-4">Generate a new set</h4>
              <div className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-stone-700 mb-1">Number of Personas</label>
                    <input
                      type="number"
                      min="1"
                      max="10"
                      value={numPersonas}
                      onChange={(e) => setNumPersonas(parseInt(e.target.value) || 3)}
                      className="w-full px-3 py-2 bg-white border border-stone-200 rounded-xl text-stone-900"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-stone-700 mb-1">Output Format</label>
                    <select
                      value={outputFormat}
                      onChange={(e) => setOutputFormat(e.target.value)}
                      className="w-full px-3 py-2 bg-white border border-stone-200 rounded-xl text-stone-900"
                    >
                      <option value="json">JSON</option>
                      <option value="profile">Profile</option>
                      <option value="chat">Chat</option>
                    </select>
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-stone-700 mb-1">
                    Stakeholder groups (optional)
                  </label>
                  <textarea
                    value={stakeholderGroupsText}
                    onChange={(e) => setStakeholderGroupsText(e.target.value)}
                    rows={3}
                    placeholder={"One group per line, e.g.\naffected_households\nbisp_programme_representatives\nlocal_humanitarian_workers"}
                    className="w-full px-3 py-2 bg-white border border-stone-200 rounded-xl text-stone-900 font-mono text-sm"
                  />
                  <p className="mt-1 text-xs text-stone-500">
                    When set, generates exactly one persona per group (overrides count above).
                    Use the corpus persona IDs when available. Iterative RQE still runs to differentiate roles.
                  </p>
                </div>
                <div className="rounded-xl border border-stone-200 bg-stone-50 p-4 space-y-3">
                  <div className="text-sm font-medium text-stone-900">Iterative RQE</div>
                  <label className="flex items-center gap-2 text-sm text-stone-700">
                    <input
                      type="checkbox"
                      checked={autoIterate}
                      onChange={(e) => setAutoIterate(e.target.checked)}
                    />
                    Auto-iterate until diversity threshold is met
                  </label>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs text-stone-600 mb-1">RQE threshold</label>
                      <input
                        type="number"
                        min={0}
                        max={1}
                        step={0.05}
                        value={rqeThreshold}
                        disabled={!autoIterate}
                        onChange={(e) => setRqeThreshold(parseFloat(e.target.value) || 0.75)}
                        className="w-full px-3 py-2 bg-white border border-stone-200 rounded-xl text-sm disabled:opacity-50"
                      />
                    </div>
                    <div>
                      <label className="block text-xs text-stone-600 mb-1">Max iterations</label>
                      <input
                        type="number"
                        min={1}
                        max={10}
                        value={maxIterations}
                        disabled={!autoIterate}
                        onChange={(e) => setMaxIterations(parseInt(e.target.value, 10) || 3)}
                        className="w-full px-3 py-2 bg-white border border-stone-200 rounded-xl text-sm disabled:opacity-50"
                      />
                    </div>
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-stone-700 mb-1">Context Details (Optional)</label>
                  <textarea
                    value={contextDetails}
                    onChange={(e) => setContextDetails(e.target.value)}
                    rows={3}
                    className="w-full px-3 py-2 bg-white border border-stone-200 rounded-xl text-stone-900"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-stone-700 mb-1">Interview Topic (Optional)</label>
                  <input
                    type="text"
                    value={interviewTopic}
                    onChange={(e) => setInterviewTopic(e.target.value)}
                    className="w-full px-3 py-2 bg-white border border-stone-200 rounded-xl text-stone-900"
                  />
                </div>
                <button
                  onClick={handleGenerateSet}
                  disabled={generating || documents.length === 0}
                  className="w-full px-6 py-3 bg-stone-900 text-white rounded-xl  disabled:opacity-50 transition-all"
                >
                  {generating ? 'Generating...' : 'Generate Personas'}
                </button>
              </div>
            </div>
          </div>
        )}

        {currentStep === 'optimize' && !selectedSet && (
          <div>
            <h3 className="text-2xl font-semibold text-stone-900 mb-4">View & Optimize</h3>
            <p className="text-stone-600 mb-4">
              {personaSets.length === 0
                ? 'No persona sets for this project yet. Generate one in Create Personas.'
                : 'Select a persona set to continue.'}
            </p>
            {personaSets.length > 0 ? (
              <div className="space-y-2 mb-4">
                {personaSets.map((set) => (
                  <button
                    key={set.id}
                    type="button"
                    onClick={() => handleSelectExistingSet(set)}
                    className="w-full text-left flex items-center justify-between gap-3 p-3 rounded-xl border border-stone-200 bg-white hover:border-stone-900"
                  >
                    <span className="font-medium text-stone-900">{set.name}</span>
                    <span className="text-sm text-stone-500">
                      {set.personas?.length ?? 0} persona{(set.personas?.length ?? 0) !== 1 ? 's' : ''}
                    </span>
                  </button>
                ))}
              </div>
            ) : (
              <button
                type="button"
                onClick={() => setCurrentStep('create')}
                className="px-6 py-3 bg-stone-900 text-white rounded-xl"
              >
                Go to Create Personas
              </button>
            )}
          </div>
        )}

        {currentStep === 'optimize' && selectedSet && (
          <div>
            {personaSets.length > 1 && (
              <div className="mb-4">
                <label className="block text-sm font-medium text-stone-700 mb-1">Persona set</label>
                <select
                  value={selectedSet.id}
                  onChange={(e) => {
                    const next = personaSets.find((s) => s.id === parseInt(e.target.value));
                    if (next) setSelectedSet(next);
                  }}
                  className="w-full max-w-md px-3 py-2 bg-white border border-stone-200 rounded-xl text-stone-900"
                >
                  {personaSets.map((set) => (
                    <option key={set.id} value={set.id}>
                      {set.name} ({set.personas?.length ?? 0})
                    </option>
                  ))}
                </select>
              </div>
            )}
            <h3 className="text-2xl font-semibold text-stone-900 mb-6">Persona Set: {selectedSet.name}</h3>
            <div className="space-y-4">
              <div className="flex items-center space-x-4">
                <button
                  onClick={handleMeasureDiversity}
                  disabled={measuringDiversity || (selectedSet.personas?.length ?? 0) < 2}
                  className="px-4 py-2 bg-stone-900 text-white rounded-lg hover:bg-stone-800 disabled:opacity-50"
                >
                  {measuringDiversity
                    ? 'Measuring…'
                    : selectedSet.diversity_score?.rqe_score != null ||
                        (selectedSet.diversity_score as { final_rqe?: number } | undefined)?.final_rqe !=
                          null
                      ? 'Re-measure RQE'
                      : 'Measure RQE'}
                </button>
                {selectedSet.diversity_score && (
                  <span className="text-stone-700">
                    RQE:{' '}
                    {(
                      (selectedSet.diversity_score.rqe_score ??
                        (selectedSet.diversity_score as { final_rqe?: number }).final_rqe ??
                        0) * 100
                    ).toFixed(1)}
                    %
                  </span>
                )}
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {selectedSet.personas.map((persona) => (
                  <div key={persona.id} className="glass-card rounded-xl p-4">
                    <h4 className="text-lg font-semibold text-stone-900 mb-2">{persona.persona_data.name || persona.name}</h4>
                    <p className="text-sm text-stone-600 line-clamp-3">
                      {(() => {
                        const getStringValue = (value: any): string | null => {
                          if (!value) return null;
                          if (typeof value === 'string') return value;
                          if (typeof value === 'object') {
                            if (Array.isArray(value)) return value.map(String).join(', ');
                            if ('text' in value || 'description' in value || 'content' in value) {
                              return String(value.text || value.description || value.content);
                            }
                            return JSON.stringify(value);
                          }
                          return String(value);
                        };
                        return getStringValue(persona.persona_data.basic_description) || 
                               getStringValue(persona.persona_data.detailed_description) || 
                               'No description';
                      })()}
                    </p>
                  </div>
                ))}
              </div>
              <button
                onClick={() => setCurrentStep('expand')}
                className="mt-4 px-6 py-3 bg-stone-900 text-white rounded-xl  transition-all"
              >
                Continue to Expand & Images
              </button>
            </div>
          </div>
        )}

        {(currentStep === 'expand' || currentStep === 'reports') && !selectedSet && (
          <div>
            <h3 className="text-2xl font-semibold text-stone-900 mb-4">
              {currentStep === 'expand' ? 'Expand & Images' : 'Reports'}
            </h3>
            <p className="text-stone-600 mb-4">
              {personaSets.length === 0
                ? 'No persona sets for this project yet. Generate one in Create Personas.'
                : 'Select a persona set to continue.'}
            </p>
            {personaSets.length > 0 ? (
              <div className="space-y-2">
                {personaSets.map((set) => (
                  <button
                    key={set.id}
                    type="button"
                    onClick={() => {
                      setSelectedSet(set);
                    }}
                    className="w-full text-left flex items-center justify-between gap-3 p-3 rounded-xl border border-stone-200 bg-white hover:border-stone-900"
                  >
                    <span className="font-medium text-stone-900">{set.name}</span>
                    <span className="text-sm text-stone-500">
                      {set.personas?.length ?? 0} persona{(set.personas?.length ?? 0) !== 1 ? 's' : ''}
                    </span>
                  </button>
                ))}
              </div>
            ) : (
              <button
                type="button"
                onClick={() => setCurrentStep('create')}
                className="px-6 py-3 bg-stone-900 text-white rounded-xl"
              >
                Go to Create Personas
              </button>
            )}
          </div>
        )}

        {currentStep === 'expand' && selectedSet && (
          <div>
            <h3 className="text-2xl font-semibold text-stone-900 mb-6">Expand Personas & Generate Images</h3>
            <div className="space-y-4">
              <button
                onClick={handleExpand}
                disabled={expanding}
                className="w-full px-6 py-3 bg-stone-900 text-white rounded-xl  disabled:opacity-50 transition-all"
              >
                {expanding ? 'Expanding...' : 'Expand All Personas'}
              </button>
              <button
                onClick={handleGenerateImages}
                disabled={generatingImages}
                className="w-full px-6 py-3 bg-stone-900 text-white rounded-xl  disabled:opacity-50 transition-all"
              >
                {generatingImages ? 'Generating...' : 'Generate Images'}
              </button>
              {selectedSet.personas.map((persona) => (
                <div key={persona.id} className="glass-card rounded-xl p-4">
                  <div className="flex items-center space-x-4">
                    {(persona.image_url || persona.id) && (
                      <img
                        src={getPersonaImageUrl(persona.image_url, persona.id) || ''}
                        alt={persona.name}
                        className="w-20 h-20 object-cover rounded-xl"
                      />
                    )}
                    <div>
                      <h4 className="text-lg font-semibold text-stone-900">{persona.persona_data.name || persona.name}</h4>
                      {persona.persona_data.detailed_description && (
                        <p className="text-sm text-stone-600 mt-2">
                          {typeof persona.persona_data.detailed_description === 'string' 
                            ? persona.persona_data.detailed_description 
                            : (typeof persona.persona_data.detailed_description === 'object' 
                              ? JSON.stringify(persona.persona_data.detailed_description) 
                              : String(persona.persona_data.detailed_description))}
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              ))}
              <button
                onClick={() => setCurrentStep('reports')}
                className="mt-4 px-6 py-3 bg-stone-900 text-white rounded-xl  transition-all"
              >
                View Reports
              </button>
            </div>
          </div>
        )}

        {currentStep === 'reports' && selectedSet && (
          <div>
            <h3 className="text-2xl font-semibold text-stone-900 mb-6">Reports</h3>
            <button
              onClick={() => navigate(`/reports?set=${selectedSet.id}`)}
              className="px-6 py-3 bg-stone-900 text-white rounded-xl  transition-all"
            >
              View Full Report
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
