import { useState, useEffect } from 'react';
import { Plus, Sparkles, Image as ImageIcon, Eye, CheckCircle, Circle, BarChart3 } from 'lucide-react';
import { personasApi } from '../services/api';
import { PersonaSet, PersonaSetGenerateResponse, Persona } from '../types';
import { useNavigate } from 'react-router-dom';
import { getPersonaImageUrl } from '../utils/imageUtils';

// Simplified Persona Card Component (shows only image, name and background)
function ExpandedPersonaCard({ persona }: { persona: Persona }) {
  const personaData = persona.persona_data || {};
  const navigate = useNavigate();
  const [imageError, setImageError] = useState(false);

  return (
    <div className="glass-card rounded-2xl p-6 border border-white/20 pastel-blue">
      {/* Persona Image and Name */}
      <div className="flex items-center gap-4 mb-4">
        {persona.image_url && !imageError ? (
          <img
            src={getPersonaImageUrl(persona.image_url) || ''}
            alt={persona.name}
            className="w-20 h-20 object-cover rounded-xl border-4 border-white/30 shadow-lg flex-shrink-0"
            onError={() => setImageError(true)}
          />
        ) : (
          <div className="w-20 h-20 rounded-xl border-4 border-white/30 bg-white/10 flex items-center justify-center flex-shrink-0">
            <span className="text-white/40 text-2xl font-bold">
              {(personaData.name || persona.name).charAt(0).toUpperCase()}
            </span>
          </div>
        )}
        <div className="flex-1">
          <h4 className="text-2xl font-bold text-white mb-1">{personaData.name || persona.name}</h4>
        </div>
      </div>

      {/* Background */}
      <div className="mb-4">
        <h5 className="text-sm font-semibold text-white uppercase tracking-wide mb-2">Background</h5>
        <p className="text-sm text-white/90 leading-relaxed">
          {personaData.background || personaData.detailed_description || personaData.personal_background || 'No background information available.'}
        </p>
      </div>

      {/* Button to view expanded version */}
      <button
        onClick={() => navigate(`/personas/${persona.persona_set_id}/${persona.id}`)}
        className="w-full mt-4 px-4 py-2 bg-gradient-to-r from-purple-500 to-indigo-600 hover:from-purple-600 hover:to-indigo-700 text-white rounded-lg font-medium transition-all duration-200 shadow-lg transform hover:scale-105"
      >
        View Complete Persona
      </button>
    </div>
  );
}

export default function PersonasPage() {
  const navigate = useNavigate();
  const [personaSets, setPersonaSets] = useState<PersonaSet[]>([]);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [expanding, setExpanding] = useState<number | null>(null);
  const [generatingImages, setGeneratingImages] = useState<number | null>(null);
  const [measuringDiversity, setMeasuringDiversity] = useState<number | null>(null);
  const [validating, setValidating] = useState<number | null>(null);
  const [selectedSet, setSelectedSet] = useState<PersonaSet | null>(null);
  const [numPersonas, setNumPersonas] = useState(3);
  const [contextDetails, setContextDetails] = useState('');
  const [interviewTopic, setInterviewTopic] = useState('');
  const [userStudyDesign, setUserStudyDesign] = useState('');
  const [includeEthicalGuardrails, setIncludeEthicalGuardrails] = useState(true);
  const [outputFormat, setOutputFormat] = useState('json');
  const [showAdvanced, setShowAdvanced] = useState(false);

  useEffect(() => {
    loadPersonaSets();
  }, []);

  const loadPersonaSets = async () => {
    setLoading(true);
    try {
      const data = await personasApi.getAllSets();
      setPersonaSets(data);
    } catch (error) {
      console.error('Failed to load persona sets:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateSet = async () => {
    setGenerating(true);
    try {
      const response: PersonaSetGenerateResponse = await personasApi.generateSet(
        numPersonas,
        contextDetails || undefined,
        interviewTopic || undefined,
        userStudyDesign || undefined,
        includeEthicalGuardrails,
        outputFormat
      );
      await loadPersonaSets();
      const newSet = await personasApi.getSet(response.persona_set_id);
      setSelectedSet(newSet);
      alert('Persona set generated successfully!');
    } catch (error: any) {
      alert(`Failed to generate personas: ${error.response?.data?.detail || error.message}`);
    } finally {
      setGenerating(false);
    }
  };

  const handleExpand = async (personaSetId: number) => {
    setExpanding(personaSetId);
    try {
      await personasApi.expand(personaSetId);
      await loadPersonaSets();
      if (selectedSet?.id === personaSetId) {
        const updated = await personasApi.getSet(personaSetId);
        setSelectedSet(updated);
      }
      alert('Personas expanded successfully!');
    } catch (error: any) {
      alert(`Failed to expand personas: ${error.response?.data?.detail || error.message}`);
    } finally {
      setExpanding(null);
    }
  };

  const handleGenerateImages = async (personaSetId: number) => {
    setGeneratingImages(personaSetId);
    try {
      await personasApi.generateImages(personaSetId);
      await loadPersonaSets();
      if (selectedSet?.id === personaSetId) {
        const updated = await personasApi.getSet(personaSetId);
        setSelectedSet(updated);
      }
      alert('Images generated successfully!');
    } catch (error: any) {
      alert(`Failed to generate images: ${error.response?.data?.detail || error.message}`);
    } finally {
      setGeneratingImages(null);
    }
  };

  const handleViewSet = async (personaSetId: number) => {
    try {
      const set = await personasApi.getSet(personaSetId);
      setSelectedSet(set);
    } catch (error: any) {
      alert(`Failed to load persona set: ${error.response?.data?.detail || error.message}`);
    }
  };

  const handleViewExpanded = (setId: number, personaId?: number) => {
    if (personaId) {
      navigate(`/personas/${setId}/${personaId}`);
    } else {
      navigate(`/personas/${setId}`);
    }
  };

  const handleMeasureDiversity = async (personaSetId: number) => {
    setMeasuringDiversity(personaSetId);
    try {
      await personasApi.measureDiversity(personaSetId);
      await loadPersonaSets();
      if (selectedSet?.id === personaSetId) {
        const updated = await personasApi.getSet(personaSetId);
        setSelectedSet(updated);
      }
      alert('Diversity measured successfully!');
    } catch (error: any) {
      alert(`Failed to measure diversity: ${error.response?.data?.detail || error.message}`);
    } finally {
      setMeasuringDiversity(null);
    }
  };

  const handleValidate = async (personaSetId: number) => {
    setValidating(personaSetId);
    try {
      await personasApi.validate(personaSetId);
      await loadPersonaSets();
      if (selectedSet?.id === personaSetId) {
        const updated = await personasApi.getSet(personaSetId);
        setSelectedSet(updated);
      }
      alert('Validation completed successfully!');
    } catch (error: any) {
      alert(`Failed to validate: ${error.response?.data?.detail || error.message}`);
    } finally {
      setValidating(null);
    }
  };

  const handleViewReport = (personaSetId: number) => {
    navigate(`/reports?set=${personaSetId}`);
  };

  return (
    <div className="px-4 py-6 sm:px-0">
      <div className="mb-6">
        <h2 className="text-3xl font-bold text-white mb-2 drop-shadow-lg">Personas</h2>
        <p className="text-white/80 text-lg">Generate and manage user personas from your documents</p>
      </div>

      {/* Generate New Persona Set */}
      <div className="glass-card rounded-2xl p-6 mb-6 pastel-blue">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-xl font-semibold text-white">Generate New Persona Set</h3>
          <button
            onClick={async () => {
              try {
                setGenerating(true);
                const set = await personasApi.loadDefaultPersonas();
                await loadPersonaSets();
                if (set) {
                  setSelectedSet(set);
                  alert('Default personas loaded successfully!');
                } else {
                  alert('Default personas already exist or could not be loaded.');
                }
              } catch (error: any) {
                console.error('Error loading default personas:', error);
                const errorMessage = error.response?.data?.detail || error.message || 'Network error. Please check if the API is running.';
                alert(`Failed to load default personas: ${errorMessage}`);
              } finally {
                setGenerating(false);
              }
            }}
            disabled={generating}
            className="px-4 py-2 text-sm font-medium rounded-xl text-white bg-gradient-to-r from-purple-400 to-pink-400 hover:from-purple-500 hover:to-pink-500 disabled:opacity-50 transition-all duration-200 shadow-lg hover:shadow-xl hover:scale-105"
          >
            {generating ? 'Loading...' : 'Load Default Personas (Manual)'}
          </button>
        </div>
        
        {/* Basic Options */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          <div>
            <label className="block text-sm font-medium text-white/90 mb-1">
              Number of Personas
            </label>
            <input
              type="number"
              min="1"
              max="10"
              value={numPersonas}
              onChange={(e) => setNumPersonas(parseInt(e.target.value) || 3)}
              className="w-full px-3 py-2 bg-white/20 border border-white/30 rounded-xl text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-white/50"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-white/90 mb-1">
              Output Format
            </label>
            <select
              value={outputFormat}
              onChange={(e) => setOutputFormat(e.target.value)}
              className="w-full px-3 py-2 bg-white/20 border border-white/30 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-white/50"
            >
              <option value="json">JSON</option>
              <option value="profile">Profile</option>
              <option value="chat">Chat</option>
              <option value="proto">Proto</option>
              <option value="adhoc">Ad-hoc</option>
              <option value="engaging">Engaging</option>
              <option value="goal_based">Goal-based</option>
              <option value="role_based">Role-based</option>
              <option value="interactive">Interactive</option>
            </select>
          </div>
        </div>

        {/* Advanced Options Toggle */}
        <button
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="text-sm text-white/90 hover:text-white mb-4 font-medium transition-all duration-200"
        >
          {showAdvanced ? '▼ Hide' : '▶ Show'} Advanced Options
        </button>

        {/* Advanced Options */}
        {showAdvanced && (
          <div className="space-y-4 border-t border-white/20 pt-4">
            <div>
              <label className="block text-sm font-medium text-white/90 mb-1">
                Context Details (Optional)
              </label>
              <textarea
                value={contextDetails}
                onChange={(e) => setContextDetails(e.target.value)}
                placeholder="Additional context about the research, market, or domain..."
                rows={3}
                className="w-full px-3 py-2 bg-white/20 border border-white/30 rounded-xl text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-white/50"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-white/90 mb-1">
                Interview Topic (Optional)
              </label>
              <input
                type="text"
                value={interviewTopic}
                onChange={(e) => setInterviewTopic(e.target.value)}
                placeholder="e.g., user experience with mobile app, customer pain points..."
                className="w-full px-3 py-2 bg-white/20 border border-white/30 rounded-xl text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-white/50"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-white/90 mb-1">
                User Study Design (Optional)
              </label>
              <textarea
                value={userStudyDesign}
                onChange={(e) => setUserStudyDesign(e.target.value)}
                placeholder="Description of user study design, methodology, and research approach..."
                rows={3}
                className="w-full px-3 py-2 bg-white/20 border border-white/30 rounded-xl text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-white/50"
              />
            </div>

            <div className="flex items-center">
              <input
                type="checkbox"
                id="ethical-guardrails"
                checked={includeEthicalGuardrails}
                onChange={(e) => setIncludeEthicalGuardrails(e.target.checked)}
                className="h-4 w-4 text-purple-400 focus:ring-purple-300 border-white/30 rounded bg-white/20"
              />
              <label htmlFor="ethical-guardrails" className="ml-2 block text-sm text-white/90">
                Include Ethical and Fairness Guardrails
              </label>
            </div>
          </div>
        )}

        {/* Generate Button */}
        <div className="mt-4">
          <button
            onClick={handleGenerateSet}
            disabled={generating}
            className="w-full inline-flex items-center justify-center px-6 py-3 border border-transparent text-sm font-medium rounded-xl text-white bg-gradient-to-r from-purple-400 via-pink-400 to-rose-400 hover:from-purple-500 hover:via-pink-500 hover:to-rose-500 disabled:opacity-50 transition-all duration-200 shadow-lg hover:shadow-xl hover:scale-105"
          >
            <Plus className="mr-2 h-4 w-4" />
            {generating ? 'Generating...' : 'Generate Personas'}
          </button>
        </div>
      </div>

      {/* Workflow Steps */}
      {selectedSet && (
        <div className="glass-card rounded-2xl p-6 mb-6 pastel-green">
          <h3 className="text-xl font-semibold text-white mb-4">Persona Generation Workflow</h3>
          <div className="space-y-4">
            {/* Step 1: Generation */}
            <div className="flex items-start space-x-4">
              <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
                selectedSet.personas.length > 0 ? 'bg-green-400' : 'bg-white/20'
              }`}>
                {selectedSet.personas.length > 0 ? (
                  <CheckCircle className="h-5 w-5 text-white" />
                ) : (
                  <Circle className="h-5 w-5 text-white" />
                )}
              </div>
              <div className="flex-1">
                <h4 className="font-medium text-white">Step 1: Persona Set Generation</h4>
                <p className="text-sm text-white/80">Generate initial persona set with basic demographics</p>
                {selectedSet.personas.length > 0 && (
                  <p className="text-xs text-white/60 mt-1">✓ {selectedSet.personas.length} personas generated</p>
                )}
              </div>
            </div>

            {/* Step 2: Diversity Measurement */}
            <div className="flex items-start space-x-4">
              <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
                selectedSet.diversity_score ? 'bg-green-400' : 'bg-white/20'
              }`}>
                {selectedSet.diversity_score ? (
                  <CheckCircle className="h-5 w-5 text-white" />
                ) : (
                  <Circle className="h-5 w-5 text-white" />
                )}
              </div>
              <div className="flex-1">
                <h4 className="font-medium text-white">Step 2: Measure Diversity (RQE)</h4>
                <p className="text-sm text-white/80">Calculate RQE scores to measure persona set diversity</p>
                {selectedSet.diversity_score && (
                  <p className="text-xs text-white/60 mt-1">
                    ✓ RQE: {(selectedSet.diversity_score.rqe_score * 100).toFixed(1)}%
                  </p>
                )}
                {selectedSet.personas.length > 0 && !selectedSet.diversity_score && (
                  <button
                    onClick={() => handleMeasureDiversity(selectedSet.id)}
                    disabled={measuringDiversity === selectedSet.id}
                    className="mt-2 text-xs px-3 py-1 bg-white/20 text-white rounded-lg hover:bg-white/30 disabled:opacity-50"
                  >
                    {measuringDiversity === selectedSet.id ? 'Measuring...' : 'Measure Diversity'}
                  </button>
                )}
              </div>
            </div>

            {/* Step 3: Expansion */}
            <div className="flex items-start space-x-4">
              <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
                selectedSet.personas.some(p => p.persona_data.detailed_description) ? 'bg-green-400' : 'bg-white/20'
              }`}>
                {selectedSet.personas.some(p => p.persona_data.detailed_description) ? (
                  <CheckCircle className="h-5 w-5 text-white" />
                ) : (
                  <Circle className="h-5 w-5 text-white" />
                )}
              </div>
              <div className="flex-1">
                <h4 className="font-medium text-white">Step 3: Expand Personas</h4>
                <p className="text-sm text-white/80">Expand basic personas into full-fledged personas</p>
                {selectedSet.personas.length > 0 && (
                  <button
                    onClick={() => handleExpand(selectedSet.id)}
                    disabled={expanding === selectedSet.id}
                    className="mt-2 text-xs px-3 py-1 bg-white/20 text-white rounded-lg hover:bg-white/30 disabled:opacity-50"
                  >
                    {expanding === selectedSet.id ? 'Expanding...' : 'Expand All'}
                  </button>
                )}
              </div>
            </div>

            {/* Step 4: Validation */}
            <div className="flex items-start space-x-4">
              <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
                selectedSet.validation_scores ? 'bg-green-400' : 'bg-white/20'
              }`}>
                {selectedSet.validation_scores ? (
                  <CheckCircle className="h-5 w-5 text-white" />
                ) : (
                  <Circle className="h-5 w-5 text-white" />
                )}
              </div>
              <div className="flex-1">
                <h4 className="font-medium text-white">Step 4: Validate Against Transcripts</h4>
                <p className="text-sm text-white/80">Calculate cosine similarity with real interview data</p>
                {selectedSet.validation_scores && (
                  <div className="mt-1">
                    <p className="text-xs text-white/60">
                      ✓ {selectedSet.validation_scores.filter((v: any) => v.validation_status === 'validated').length} validated
                    </p>
                    {selectedSet.validation_scores.some((v: any) => v.dummy) && (
                      <p className="text-xs text-yellow-300 mt-1">
                        ⚠ Using simulated validation (no interview documents available)
                      </p>
                    )}
                  </div>
                )}
                {selectedSet.personas.length > 0 && (
                  <div className="flex space-x-2 mt-2">
                    <button
                      onClick={() => handleValidate(selectedSet.id)}
                      disabled={validating === selectedSet.id}
                      className="text-xs px-3 py-1 bg-white/20 text-white rounded-lg hover:bg-white/30 disabled:opacity-50"
                    >
                      {validating === selectedSet.id ? 'Validating...' : 'Validate'}
                    </button>
                    {selectedSet.validation_scores && (
                      <button
                        onClick={() => handleViewReport(selectedSet.id)}
                        className="text-xs px-3 py-1 bg-gradient-to-r from-purple-400 to-pink-400 text-white rounded-lg hover:from-purple-500 hover:to-pink-500"
                      >
                        <BarChart3 className="inline h-3 w-3 mr-1" />
                        View Report
                      </button>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Persona Sets List */}
        <div className="glass-card rounded-2xl overflow-hidden pastel-purple">
          <div className="px-6 py-4 border-b border-white/20">
            <h3 className="text-lg font-semibold text-white">Persona Sets</h3>
          </div>
          <div className="divide-y divide-white/10">
            {loading ? (
              <div className="px-6 py-8 text-center text-white/80">Loading...</div>
            ) : personaSets.length === 0 ? (
              <div className="px-6 py-8 text-center text-white/80">
                No persona sets found. Generate your first set above.
              </div>
            ) : (
              personaSets.map((set) => (
                <div key={set.id} className="px-6 py-4 hover:bg-white/10 transition-all duration-200">
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="text-sm font-medium text-white">
                      {set.name || `Persona Set #${set.id}`}
                    </h4>
                    <div className="flex items-center space-x-2">
                      <button
                        onClick={() => handleViewSet(set.id)}
                        className="text-white/80 hover:text-white transition-colors"
                        title="View in sidebar"
                      >
                        <Eye className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => handleViewExpanded(set.id)}
                        className="text-white/80 hover:text-white transition-colors"
                        title="View expanded"
                      >
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M18 3a3 3 0 0 0-3 3v12a3 3 0 0 0 3 3h3a1 1 0 0 0 1-1V4a1 1 0 0 0-1-1z"/>
                          <path d="M9 21H6a3 3 0 0 1-3-3V6a3 3 0 0 1 3-3h3"/>
                          <path d="M9 3v18"/>
                        </svg>
                      </button>
                    </div>
                  </div>
                  <p className="text-sm text-white/70 mb-3">
                    {set.description || 'No description'}
                  </p>
                  <div className="flex items-center space-x-2">
                    <span className="text-xs text-white/70">
                      {set.personas.length} persona{set.personas.length !== 1 ? 's' : ''}
                    </span>
                    <span className="text-xs text-white/50">•</span>
                    <span className="text-xs text-white/70">
                      {new Date(set.created_at).toLocaleDateString()}
                    </span>
                  </div>
                  <div className="mt-3 flex space-x-2">
                    <button
                      onClick={() => handleExpand(set.id)}
                      disabled={expanding === set.id}
                      className="text-xs px-3 py-1 bg-purple-400/30 text-white rounded-lg hover:bg-purple-400/40 disabled:opacity-50 transition-all duration-200 border border-purple-300/30"
                    >
                      <Sparkles className="inline h-3 w-3 mr-1" />
                      {expanding === set.id ? 'Expanding...' : 'Expand'}
                    </button>
                    <button
                      onClick={() => handleGenerateImages(set.id)}
                      disabled={generatingImages === set.id}
                      className="text-xs px-3 py-1 bg-pink-400/30 text-white rounded-lg hover:bg-pink-400/40 disabled:opacity-50 transition-all duration-200 border border-pink-300/30"
                    >
                      <ImageIcon className="inline h-3 w-3 mr-1" />
                      {generatingImages === set.id ? 'Generating...' : 'Images'}
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Selected Persona Set Details */}
        <div className="glass-card rounded-2xl overflow-hidden pastel-pink">
          <div className="px-6 py-4 border-b border-white/20">
            <h3 className="text-lg font-semibold text-white">Persona Details</h3>
          </div>
          <div className="p-6">
            {selectedSet ? (
              <div className="space-y-4">
                <div className="flex items-center justify-between mb-4">
                  <h4 className="text-lg font-semibold text-white">
                    {selectedSet.personas.length} Persona{selectedSet.personas.length !== 1 ? 's' : ''}
                  </h4>
                  <button
                    onClick={() => handleViewExpanded(selectedSet.id)}
                    className="px-4 py-2 bg-gradient-to-r from-purple-400 to-pink-400 text-white rounded-lg hover:from-purple-500 hover:to-pink-500 transition-all duration-200 flex items-center space-x-2"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M18 3a3 3 0 0 0-3 3v12a3 3 0 0 0 3 3h3a1 1 0 0 0 1-1V4a1 1 0 0 0-1-1z"/>
                      <path d="M9 21H6a3 3 0 0 1-3-3V6a3 3 0 0 1 3-3h3"/>
                      <path d="M9 3v18"/>
                    </svg>
                    <span>View Expanded</span>
                  </button>
                </div>
                <div className="space-y-6">
                  {selectedSet.personas.map((persona) => (
                    <ExpandedPersonaCard key={persona.id} persona={persona} />
                  ))}
                </div>
              </div>
            ) : (
              <div className="text-center text-white/80 py-8">
                Select a persona set to view details
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

