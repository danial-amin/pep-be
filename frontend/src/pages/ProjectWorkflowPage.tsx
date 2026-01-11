import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Upload, FileText, Users, Sparkles, Image as ImageIcon, BarChart3, CheckCircle, ArrowLeft } from 'lucide-react';
import { projectsApi, documentsApi, personasApi } from '../services/api';
import { Project, Document, PersonaSet } from '../types';
import { getPersonaImageUrl } from '../utils/imageUtils';

type WorkflowStep = 'upload' | 'create' | 'optimize' | 'expand' | 'reports';

export default function ProjectWorkflowPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const [project, setProject] = useState<Project | null>(null);
  const [currentStep, setCurrentStep] = useState<WorkflowStep>('upload');
  const [documents, setDocuments] = useState<Document[]>([]);
  const [selectedSet, setSelectedSet] = useState<PersonaSet | null>(null);
  const [uploading, setUploading] = useState(false);

  // Persona generation state
  const [numPersonas, setNumPersonas] = useState(3);
  const [contextDetails, setContextDetails] = useState('');
  const [interviewTopic, setInterviewTopic] = useState('');
  const [outputFormat, setOutputFormat] = useState('json');
  const [generating, setGenerating] = useState(false);
  const [expanding, setExpanding] = useState(false);
  const [generatingImages, setGeneratingImages] = useState(false);
  const [measuringDiversity, setMeasuringDiversity] = useState(false);

  useEffect(() => {
    if (projectId) {
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

  const loadDocuments = async () => {
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
  };

  const loadPersonaSets = async () => {
    if (!projectId) return;
    try {
      const allSets = await personasApi.getAllSets();
      // Filter persona sets for this project (if they have project_id in future)
      // For now, we'll show all sets
      if (allSets.length > 0 && !selectedSet) {
        setSelectedSet(allSets[0]);
      }
    } catch (error) {
      console.error('Failed to load persona sets:', error);
    }
  };

  const handleFileUpload = async (file: File, documentType: 'context' | 'interview') => {
    if (!projectId) return;
    setUploading(true);
    try {
      const response = await documentsApi.process(file, documentType, parseInt(projectId));
      await loadDocuments();
      if (response.vector_id) {
        alert('Document processed and stored in vector database successfully!');
      } else {
        alert('Document saved but vector storage failed. Check backend logs for details.');
      }
    } catch (error: any) {
      const errorMsg = error.response?.data?.detail || error.message;
      alert(`Failed to process document: ${errorMsg}`);
      console.error('Document processing error:', error);
    } finally {
      setUploading(false);
    }
  };

  const handleGenerateSet = async () => {
    if (!projectId) return;
    setGenerating(true);
    try {
      const response = await personasApi.generateSet(
        numPersonas,
        contextDetails || undefined,
        interviewTopic || undefined,
        undefined, // userStudyDesign - not used in simplified workflow
        true, // includeEthicalGuardrails - default to true
        outputFormat,
        parseInt(projectId)
      );
      await loadPersonaSets();
      const newSet = await personasApi.getSet(response.persona_set_id);
      setSelectedSet(newSet);
      setCurrentStep('optimize');
      alert('Persona set generated successfully!');
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
      await personasApi.measureDiversity(selectedSet.id);
      await loadPersonaSets();
      const updated = await personasApi.getSet(selectedSet.id);
      setSelectedSet(updated);
      alert('Diversity measured successfully!');
    } catch (error: any) {
      alert(`Failed to measure diversity: ${error.response?.data?.detail || error.message}`);
    } finally {
      setMeasuringDiversity(false);
    }
  };

  if (!project) {
    return <div className="px-4 py-6 text-white">Loading project...</div>;
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
            className="mb-2 inline-flex items-center text-white/80 hover:text-white transition-colors"
          >
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Projects
          </button>
          <h2 className="text-3xl font-bold text-white mb-2 drop-shadow-lg">{project.name}</h2>
          {project.field_of_study && (
            <p className="text-white/80">{project.field_of_study}</p>
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
                      ? 'bg-white/30 text-white'
                      : isCompleted
                      ? 'text-white/80 hover:text-white'
                      : 'text-white/50'
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
                  <div className={`flex-1 h-0.5 mx-2 ${isCompleted ? 'bg-white/30' : 'bg-white/10'}`} />
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
            <h3 className="text-2xl font-semibold text-white mb-6">Upload Documents</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {project.includes_context && (
                <div className="glass-card rounded-xl p-6 pastel-purple">
                  <FileText className="mx-auto h-12 w-12 text-white/90 mb-4" />
                  <h4 className="text-lg font-semibold text-white mb-2">Context Document</h4>
                  <p className="text-sm text-white/80 mb-4">Upload research, reports, or background information</p>
                  <label className="inline-flex items-center px-6 py-3 text-sm font-medium rounded-xl text-white bg-gradient-to-r from-purple-400 to-pink-400 hover:from-purple-500 hover:to-pink-500 cursor-pointer transition-all">
                    <Upload className="mr-2 h-4 w-4" />
                    {uploading ? 'Uploading...' : 'Upload File'}
                    <input
                      type="file"
                      className="hidden"
                      accept=".pdf,.docx,.txt,.md"
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
                <div className="glass-card rounded-xl p-6 pastel-pink">
                  <FileText className="mx-auto h-12 w-12 text-white/90 mb-4" />
                  <h4 className="text-lg font-semibold text-white mb-2">Interview Document</h4>
                  <p className="text-sm text-white/80 mb-4">Upload interview transcripts or user research</p>
                  <label className="inline-flex items-center px-6 py-3 text-sm font-medium rounded-xl text-white bg-gradient-to-r from-pink-400 to-rose-400 hover:from-pink-500 hover:to-rose-500 cursor-pointer transition-all">
                    <Upload className="mr-2 h-4 w-4" />
                    {uploading ? 'Uploading...' : 'Upload File'}
                    <input
                      type="file"
                      className="hidden"
                      accept=".pdf,.docx,.txt,.md"
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
                <h4 className="text-lg font-semibold text-white mb-4">Uploaded Documents</h4>
                <div className="space-y-2">
                  {documents.map((doc) => (
                    <div key={doc.id} className="flex items-center justify-between p-3 bg-white/10 rounded-lg">
                      <span className="text-white/90">{doc.filename}</span>
                      <span className={`px-3 py-1 text-xs rounded-full ${
                        doc.document_type === 'context' ? 'bg-purple-400/30' : 'bg-pink-400/30'
                      }`}>
                        {doc.document_type}
                      </span>
                    </div>
                  ))}
                </div>
                <button
                  onClick={() => setCurrentStep('create')}
                  className="mt-4 px-6 py-3 bg-gradient-to-r from-purple-400 to-pink-400 text-white rounded-xl hover:from-purple-500 hover:to-pink-500 transition-all"
                >
                  Continue to Create Personas
                </button>
              </div>
            )}
          </div>
        )}

        {currentStep === 'create' && (
          <div>
            <h3 className="text-2xl font-semibold text-white mb-6">Create Persona Set</h3>
            <div className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-white/90 mb-1">Number of Personas</label>
                  <input
                    type="number"
                    min="1"
                    max="10"
                    value={numPersonas}
                    onChange={(e) => setNumPersonas(parseInt(e.target.value) || 3)}
                    className="w-full px-3 py-2 bg-white/20 border border-white/30 rounded-xl text-white"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-white/90 mb-1">Output Format</label>
                  <select
                    value={outputFormat}
                    onChange={(e) => setOutputFormat(e.target.value)}
                    className="w-full px-3 py-2 bg-white/20 border border-white/30 rounded-xl text-white"
                  >
                    <option value="json">JSON</option>
                    <option value="profile">Profile</option>
                    <option value="chat">Chat</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-white/90 mb-1">Context Details (Optional)</label>
                <textarea
                  value={contextDetails}
                  onChange={(e) => setContextDetails(e.target.value)}
                  rows={3}
                  className="w-full px-3 py-2 bg-white/20 border border-white/30 rounded-xl text-white"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-white/90 mb-1">Interview Topic (Optional)</label>
                <input
                  type="text"
                  value={interviewTopic}
                  onChange={(e) => setInterviewTopic(e.target.value)}
                  className="w-full px-3 py-2 bg-white/20 border border-white/30 rounded-xl text-white"
                />
              </div>
              <button
                onClick={handleGenerateSet}
                disabled={generating || documents.length === 0}
                className="w-full px-6 py-3 bg-gradient-to-r from-purple-400 to-pink-400 text-white rounded-xl hover:from-purple-500 hover:to-pink-500 disabled:opacity-50 transition-all"
              >
                {generating ? 'Generating...' : 'Generate Personas'}
              </button>
            </div>
          </div>
        )}

        {currentStep === 'optimize' && selectedSet && (
          <div>
            <h3 className="text-2xl font-semibold text-white mb-6">Persona Set: {selectedSet.name}</h3>
            <div className="space-y-4">
              <div className="flex items-center space-x-4">
                <button
                  onClick={handleMeasureDiversity}
                  disabled={measuringDiversity}
                  className="px-4 py-2 bg-white/20 text-white rounded-lg hover:bg-white/30 disabled:opacity-50"
                >
                  {measuringDiversity ? 'Measuring...' : 'Measure Diversity'}
                </button>
                {selectedSet.diversity_score && (
                  <span className="text-white/90">
                    RQE: {(selectedSet.diversity_score.rqe_score * 100).toFixed(1)}%
                  </span>
                )}
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {selectedSet.personas.map((persona) => (
                  <div key={persona.id} className="glass-card rounded-xl p-4 pastel-blue">
                    <h4 className="text-lg font-semibold text-white mb-2">{persona.persona_data.name || persona.name}</h4>
                    <p className="text-sm text-white/80 line-clamp-3">
                      {persona.persona_data.basic_description || persona.persona_data.detailed_description || 'No description'}
                    </p>
                  </div>
                ))}
              </div>
              <button
                onClick={() => setCurrentStep('expand')}
                className="mt-4 px-6 py-3 bg-gradient-to-r from-purple-400 to-pink-400 text-white rounded-xl hover:from-purple-500 hover:to-pink-500 transition-all"
              >
                Continue to Expand & Images
              </button>
            </div>
          </div>
        )}

        {currentStep === 'expand' && selectedSet && (
          <div>
            <h3 className="text-2xl font-semibold text-white mb-6">Expand Personas & Generate Images</h3>
            <div className="space-y-4">
              <button
                onClick={handleExpand}
                disabled={expanding}
                className="w-full px-6 py-3 bg-gradient-to-r from-purple-400 to-pink-400 text-white rounded-xl hover:from-purple-500 hover:to-pink-500 disabled:opacity-50 transition-all"
              >
                {expanding ? 'Expanding...' : 'Expand All Personas'}
              </button>
              <button
                onClick={handleGenerateImages}
                disabled={generatingImages}
                className="w-full px-6 py-3 bg-gradient-to-r from-pink-400 to-rose-400 text-white rounded-xl hover:from-pink-500 hover:to-rose-500 disabled:opacity-50 transition-all"
              >
                {generatingImages ? 'Generating...' : 'Generate Images'}
              </button>
              {selectedSet.personas.map((persona) => (
                <div key={persona.id} className="glass-card rounded-xl p-4 pastel-pink">
                  <div className="flex items-center space-x-4">
                    {persona.image_url && (
                      <img
                        src={getPersonaImageUrl(persona.image_url) || ''}
                        alt={persona.name}
                        className="w-20 h-20 object-cover rounded-xl"
                      />
                    )}
                    <div>
                      <h4 className="text-lg font-semibold text-white">{persona.persona_data.name || persona.name}</h4>
                      {persona.persona_data.detailed_description && (
                        <p className="text-sm text-white/80 mt-2">{persona.persona_data.detailed_description}</p>
                      )}
                    </div>
                  </div>
                </div>
              ))}
              <button
                onClick={() => setCurrentStep('reports')}
                className="mt-4 px-6 py-3 bg-gradient-to-r from-purple-400 to-pink-400 text-white rounded-xl hover:from-purple-500 hover:to-pink-500 transition-all"
              >
                View Reports
              </button>
            </div>
          </div>
        )}

        {currentStep === 'reports' && selectedSet && (
          <div>
            <h3 className="text-2xl font-semibold text-white mb-6">Reports</h3>
            <button
              onClick={() => navigate(`/reports?set=${selectedSet.id}`)}
              className="px-6 py-3 bg-gradient-to-r from-purple-400 to-pink-400 text-white rounded-xl hover:from-purple-500 hover:to-pink-500 transition-all"
            >
              View Full Report
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
