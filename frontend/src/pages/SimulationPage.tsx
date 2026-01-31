import { useState, useEffect, useRef } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  Play,
  Pause,
  SkipForward,
  MessageSquare,
  Users,
  Target,
  Clock,
  Zap,
  FileText,
  ArrowLeft,
  Plus,
  X,
  CheckCircle,
  Loader2,
  Sparkles
} from 'lucide-react';
import { simulationsApi, personasApi } from '../services/api';
import { Simulation, SimulationMessage, PersonaSet, Persona, SimulationListItem } from '../types';
import { getPersonaImageUrl } from '../utils/imageUtils';

// Persona Avatar Component
function PersonaAvatar({
  name,
  imageUrl,
  size = 'md',
  showBorder = true
}: {
  name: string;
  imageUrl?: string | null;
  size?: 'sm' | 'md' | 'lg';
  showBorder?: boolean;
}) {
  const [imageError, setImageError] = useState(false);
  const sizeClasses = {
    sm: 'w-8 h-8 text-sm',
    md: 'w-12 h-12 text-lg',
    lg: 'w-16 h-16 text-xl'
  };

  if (imageUrl && !imageError) {
    return (
      <img
        src={getPersonaImageUrl(imageUrl) || ''}
        alt={name}
        className={`${sizeClasses[size]} object-cover rounded-full ${showBorder ? 'border-2 border-white/30' : ''}`}
        onError={() => setImageError(true)}
      />
    );
  }

  return (
    <div className={`${sizeClasses[size]} rounded-full ${showBorder ? 'border-2 border-white/30' : ''} bg-gradient-to-br from-purple-400 to-pink-400 flex items-center justify-center`}>
      <span className="text-white font-bold">
        {name.charAt(0).toUpperCase()}
      </span>
    </div>
  );
}

// Message Bubble Component
function MessageBubble({ message, isLeft }: { message: SimulationMessage; isLeft: boolean }) {
  return (
    <div className={`flex ${isLeft ? 'justify-start' : 'justify-end'} mb-4`}>
      <div className={`flex ${isLeft ? 'flex-row' : 'flex-row-reverse'} items-start gap-3 max-w-[80%]`}>
        <PersonaAvatar
          name={message.persona_name}
          imageUrl={message.persona_image_url}
          size="sm"
        />
        <div className={`${isLeft ? 'bg-white/20' : 'bg-purple-500/30'} rounded-2xl px-4 py-3`}>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-sm font-semibold text-white">{message.persona_name}</span>
            <span className="text-xs text-white/50">Turn {message.turn_number}</span>
          </div>
          <p className="text-white/90 text-sm leading-relaxed">{message.content}</p>
        </div>
      </div>
    </div>
  );
}

// Participant Card for Selection
function SelectablePersonaCard({
  persona,
  isSelected,
  role,
  onToggle,
  onRoleChange
}: {
  persona: Persona;
  isSelected: boolean;
  role: string;
  onToggle: () => void;
  onRoleChange: (role: string) => void;
}) {
  const personaData = persona.persona_data || {};
  const demographics = personaData.demographics || {};

  return (
    <div
      className={`glass-card rounded-xl p-4 border-2 transition-all duration-200 cursor-pointer ${
        isSelected
          ? 'border-purple-400 bg-purple-500/20'
          : 'border-white/20 hover:border-white/40'
      }`}
      onClick={onToggle}
    >
      <div className="flex items-center gap-3">
        <PersonaAvatar
          name={persona.name}
          imageUrl={persona.image_url}
          size="md"
        />
        <div className="flex-1 min-w-0">
          <h4 className="text-white font-semibold truncate">{personaData.name || persona.name}</h4>
          <p className="text-white/70 text-sm truncate">
            {demographics.occupation || 'No occupation'}
          </p>
        </div>
        <div className={`w-6 h-6 rounded-full flex items-center justify-center ${
          isSelected ? 'bg-purple-400' : 'bg-white/20'
        }`}>
          {isSelected && <CheckCircle className="w-4 h-4 text-white" />}
        </div>
      </div>

      {isSelected && (
        <div className="mt-3" onClick={e => e.stopPropagation()}>
          <input
            type="text"
            placeholder="Role (optional): e.g., moderator, critic"
            value={role}
            onChange={(e) => onRoleChange(e.target.value)}
            className="w-full px-3 py-2 text-sm bg-white/10 border border-white/20 rounded-lg text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-purple-400"
          />
        </div>
      )}
    </div>
  );
}

// Main Simulation Page
export default function SimulationPage() {
  const navigate = useNavigate();
  const { simulationId } = useParams<{ simulationId: string }>();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // State
  const [personaSets, setPersonaSets] = useState<PersonaSet[]>([]);
  const [simulations, setSimulations] = useState<SimulationListItem[]>([]);
  const [currentSimulation, setCurrentSimulation] = useState<Simulation | null>(null);
  const [loading, setLoading] = useState(false);
  const [running, setRunning] = useState(false);
  const [generatingSummary, setGeneratingSummary] = useState(false);

  // Setup form state
  const [showSetup, setShowSetup] = useState(!simulationId);
  const [selectedSetId, setSelectedSetId] = useState<number | null>(null);
  const [selectedPersonas, setSelectedPersonas] = useState<Map<number, string>>(new Map());
  const [name, setName] = useState('');
  const [goal, setGoal] = useState('');
  const [goalContext, setGoalContext] = useState('');
  const [maxTurns, setMaxTurns] = useState(20);
  const [maxTokens, setMaxTokens] = useState(8000);

  // Load data on mount
  useEffect(() => {
    loadPersonaSets();
    loadSimulations();
    if (simulationId) {
      loadSimulation(parseInt(simulationId));
    }
  }, [simulationId]);

  // Auto-scroll to bottom of messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [currentSimulation?.messages]);

  const loadPersonaSets = async () => {
    try {
      const data = await personasApi.getAllSets();
      setPersonaSets(data);
    } catch (error) {
      console.error('Failed to load persona sets:', error);
    }
  };

  const loadSimulations = async () => {
    try {
      const data = await simulationsApi.getAll();
      setSimulations(data);
    } catch (error) {
      console.error('Failed to load simulations:', error);
    }
  };

  const loadSimulation = async (id: number) => {
    setLoading(true);
    try {
      const data = await simulationsApi.getById(id);
      setCurrentSimulation(data);
      setShowSetup(false);
    } catch (error) {
      console.error('Failed to load simulation:', error);
    } finally {
      setLoading(false);
    }
  };

  const handlePersonaToggle = (personaId: number) => {
    const newSelected = new Map(selectedPersonas);
    if (newSelected.has(personaId)) {
      newSelected.delete(personaId);
    } else {
      newSelected.set(personaId, '');
    }
    setSelectedPersonas(newSelected);
  };

  const handleRoleChange = (personaId: number, role: string) => {
    const newSelected = new Map(selectedPersonas);
    newSelected.set(personaId, role);
    setSelectedPersonas(newSelected);
  };

  const handleCreateSimulation = async () => {
    if (selectedPersonas.size < 2) {
      alert('Please select at least 2 personas for the simulation');
      return;
    }
    if (!goal.trim()) {
      alert('Please enter a goal for the simulation');
      return;
    }

    setLoading(true);
    try {
      const participants = Array.from(selectedPersonas.entries()).map(([persona_id, role]) => ({
        persona_id,
        role: role || undefined
      }));

      const simulation = await simulationsApi.create({
        name: name || `Simulation - ${new Date().toLocaleString()}`,
        goal,
        goal_context: goalContext || undefined,
        participants,
        max_turns: maxTurns,
        max_tokens: maxTokens
      });

      setCurrentSimulation(simulation);
      setShowSetup(false);
      navigate(`/simulations/${simulation.id}`);
      await loadSimulations();
    } catch (error: any) {
      alert(`Failed to create simulation: ${error.response?.data?.detail || error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleStartSimulation = async (autoContinue: boolean = true) => {
    if (!currentSimulation) return;

    setRunning(true);
    try {
      const updated = await simulationsApi.start(currentSimulation.id, autoContinue);
      setCurrentSimulation(updated);
      await loadSimulations();
    } catch (error: any) {
      alert(`Failed to start simulation: ${error.response?.data?.detail || error.message}`);
    } finally {
      setRunning(false);
    }
  };

  const handleNextTurn = async () => {
    if (!currentSimulation) return;

    setRunning(true);
    try {
      const response = await simulationsApi.nextTurn(currentSimulation.id);
      // Reload full simulation to get updated state
      const updated = await simulationsApi.getById(currentSimulation.id);
      setCurrentSimulation(updated);
    } catch (error: any) {
      alert(`Failed to generate next turn: ${error.response?.data?.detail || error.message}`);
    } finally {
      setRunning(false);
    }
  };

  const handleStopSimulation = async () => {
    if (!currentSimulation) return;

    try {
      await simulationsApi.stop(currentSimulation.id);
      const updated = await simulationsApi.getById(currentSimulation.id);
      setCurrentSimulation(updated);
      await loadSimulations();
    } catch (error: any) {
      alert(`Failed to stop simulation: ${error.response?.data?.detail || error.message}`);
    }
  };

  const handleGenerateSummary = async () => {
    if (!currentSimulation) return;

    setGeneratingSummary(true);
    try {
      await simulationsApi.generateSummary(currentSimulation.id);
      const updated = await simulationsApi.getById(currentSimulation.id);
      setCurrentSimulation(updated);
    } catch (error: any) {
      alert(`Failed to generate summary: ${error.response?.data?.detail || error.message}`);
    } finally {
      setGeneratingSummary(false);
    }
  };

  const handleNewSimulation = () => {
    setCurrentSimulation(null);
    setShowSetup(true);
    setSelectedPersonas(new Map());
    setName('');
    setGoal('');
    setGoalContext('');
    navigate('/simulations');
  };

  const selectedSet = personaSets.find(s => s.id === selectedSetId);

  return (
    <div className="px-4 py-6 sm:px-0">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate('/personas')}
            className="p-2 rounded-lg bg-white/10 hover:bg-white/20 transition-colors"
          >
            <ArrowLeft className="w-5 h-5 text-white" />
          </button>
          <div>
            <h2 className="text-3xl font-bold text-white mb-1 drop-shadow-lg">
              Persona Simulation Playground
            </h2>
            <p className="text-white/80 text-lg">
              Watch your personas collaborate and discuss towards a common goal
            </p>
          </div>
        </div>
        {currentSimulation && (
          <button
            onClick={handleNewSimulation}
            className="px-4 py-2 bg-gradient-to-r from-purple-400 to-pink-400 hover:from-purple-500 hover:to-pink-500 text-white rounded-xl font-medium transition-all duration-200 flex items-center gap-2"
          >
            <Plus className="w-4 h-4" />
            New Simulation
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Left Sidebar - Simulations List */}
        <div className="lg:col-span-1">
          <div className="glass-card rounded-2xl overflow-hidden pastel-purple">
            <div className="px-4 py-3 border-b border-white/20">
              <h3 className="text-lg font-semibold text-white">Simulations</h3>
            </div>
            <div className="max-h-[600px] overflow-y-auto">
              {simulations.length === 0 ? (
                <div className="p-4 text-center text-white/60">
                  No simulations yet
                </div>
              ) : (
                simulations.map(sim => (
                  <div
                    key={sim.id}
                    onClick={() => loadSimulation(sim.id)}
                    className={`px-4 py-3 cursor-pointer hover:bg-white/10 transition-colors border-b border-white/10 ${
                      currentSimulation?.id === sim.id ? 'bg-white/20' : ''
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <h4 className="text-sm font-medium text-white truncate">{sim.name}</h4>
                      <span className={`text-xs px-2 py-0.5 rounded-full ${
                        sim.status === 'completed' ? 'bg-green-400/30 text-green-300' :
                        sim.status === 'running' ? 'bg-blue-400/30 text-blue-300' :
                        sim.status === 'stopped' ? 'bg-red-400/30 text-red-300' :
                        'bg-yellow-400/30 text-yellow-300'
                      }`}>
                        {sim.status}
                      </span>
                    </div>
                    <p className="text-xs text-white/60 truncate">{sim.goal}</p>
                    <div className="flex items-center gap-2 mt-1 text-xs text-white/50">
                      <Users className="w-3 h-3" />
                      <span>{sim.participant_count}</span>
                      <MessageSquare className="w-3 h-3 ml-2" />
                      <span>{sim.current_turn}/{sim.max_turns}</span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        {/* Main Content Area */}
        <div className="lg:col-span-3">
          {showSetup ? (
            /* Setup Form */
            <div className="glass-card rounded-2xl p-6 pastel-blue">
              <h3 className="text-xl font-semibold text-white mb-6 flex items-center gap-2">
                <Sparkles className="w-5 h-5" />
                Create New Simulation
              </h3>

              {/* Name and Goal */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                <div>
                  <label className="block text-sm font-medium text-white/90 mb-2">
                    Simulation Name
                  </label>
                  <input
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="e.g., Product Strategy Discussion"
                    className="w-full px-4 py-2 bg-white/20 border border-white/30 rounded-xl text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-white/50"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-white/90 mb-2">
                    <Target className="w-4 h-4 inline mr-1" />
                    Goal / Topic *
                  </label>
                  <input
                    type="text"
                    value={goal}
                    onChange={(e) => setGoal(e.target.value)}
                    placeholder="e.g., Discuss how to improve our mobile app UX"
                    className="w-full px-4 py-2 bg-white/20 border border-white/30 rounded-xl text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-white/50"
                  />
                </div>
              </div>

              <div className="mb-6">
                <label className="block text-sm font-medium text-white/90 mb-2">
                  Additional Context (Optional)
                </label>
                <textarea
                  value={goalContext}
                  onChange={(e) => setGoalContext(e.target.value)}
                  placeholder="Provide any additional context, constraints, or specific aspects to focus on..."
                  rows={3}
                  className="w-full px-4 py-2 bg-white/20 border border-white/30 rounded-xl text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-white/50"
                />
              </div>

              {/* Limits */}
              <div className="grid grid-cols-2 gap-4 mb-6">
                <div>
                  <label className="block text-sm font-medium text-white/90 mb-2">
                    <MessageSquare className="w-4 h-4 inline mr-1" />
                    Max Turns
                  </label>
                  <input
                    type="number"
                    value={maxTurns}
                    onChange={(e) => setMaxTurns(parseInt(e.target.value) || 20)}
                    min={4}
                    max={50}
                    className="w-full px-4 py-2 bg-white/20 border border-white/30 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-white/50"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-white/90 mb-2">
                    <Zap className="w-4 h-4 inline mr-1" />
                    Max Tokens
                  </label>
                  <input
                    type="number"
                    value={maxTokens}
                    onChange={(e) => setMaxTokens(parseInt(e.target.value) || 8000)}
                    min={1000}
                    max={16000}
                    step={1000}
                    className="w-full px-4 py-2 bg-white/20 border border-white/30 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-white/50"
                  />
                </div>
              </div>

              {/* Persona Selection */}
              <div className="mb-6">
                <label className="block text-sm font-medium text-white/90 mb-2">
                  <Users className="w-4 h-4 inline mr-1" />
                  Select Persona Set
                </label>
                <select
                  value={selectedSetId || ''}
                  onChange={(e) => {
                    setSelectedSetId(parseInt(e.target.value) || null);
                    setSelectedPersonas(new Map());
                  }}
                  className="w-full px-4 py-2 bg-white/20 border border-white/30 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-white/50"
                >
                  <option value="">Select a persona set...</option>
                  {personaSets.map(set => (
                    <option key={set.id} value={set.id}>
                      {set.name} ({set.personas.length} personas)
                    </option>
                  ))}
                </select>
              </div>

              {selectedSet && (
                <div className="mb-6">
                  <div className="flex items-center justify-between mb-3">
                    <label className="text-sm font-medium text-white/90">
                      Select Participants (2-8 personas)
                    </label>
                    <span className="text-sm text-white/60">
                      {selectedPersonas.size} selected
                    </span>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-h-[400px] overflow-y-auto pr-2">
                    {selectedSet.personas.map(persona => (
                      <SelectablePersonaCard
                        key={persona.id}
                        persona={persona}
                        isSelected={selectedPersonas.has(persona.id)}
                        role={selectedPersonas.get(persona.id) || ''}
                        onToggle={() => handlePersonaToggle(persona.id)}
                        onRoleChange={(role) => handleRoleChange(persona.id, role)}
                      />
                    ))}
                  </div>
                </div>
              )}

              {/* Create Button */}
              <button
                onClick={handleCreateSimulation}
                disabled={loading || selectedPersonas.size < 2 || !goal.trim()}
                className="w-full px-6 py-3 bg-gradient-to-r from-purple-400 via-pink-400 to-rose-400 hover:from-purple-500 hover:via-pink-500 hover:to-rose-500 disabled:opacity-50 text-white rounded-xl font-medium transition-all duration-200 flex items-center justify-center gap-2"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    Creating...
                  </>
                ) : (
                  <>
                    <Play className="w-5 h-5" />
                    Create Simulation
                  </>
                )}
              </button>
            </div>
          ) : currentSimulation ? (
            /* Simulation View */
            <div className="space-y-6">
              {/* Simulation Header */}
              <div className="glass-card rounded-2xl p-4 pastel-green">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-xl font-semibold text-white">{currentSimulation.name}</h3>
                    <p className="text-white/80 mt-1">{currentSimulation.goal}</p>
                  </div>
                  <div className="flex items-center gap-4">
                    {/* Status Badge */}
                    <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                      currentSimulation.status === 'completed' ? 'bg-green-400/30 text-green-300' :
                      currentSimulation.status === 'running' ? 'bg-blue-400/30 text-blue-300' :
                      currentSimulation.status === 'stopped' ? 'bg-red-400/30 text-red-300' :
                      'bg-yellow-400/30 text-yellow-300'
                    }`}>
                      {currentSimulation.status}
                    </span>

                    {/* Progress */}
                    <div className="text-right">
                      <div className="text-sm text-white/80">
                        <MessageSquare className="w-4 h-4 inline mr-1" />
                        {currentSimulation.current_turn} / {currentSimulation.max_turns} turns
                      </div>
                      <div className="text-xs text-white/60">
                        <Zap className="w-3 h-3 inline mr-1" />
                        {currentSimulation.tokens_used.toLocaleString()} / {currentSimulation.max_tokens.toLocaleString()} tokens
                      </div>
                    </div>
                  </div>
                </div>

                {/* Participants */}
                <div className="flex items-center gap-4 mt-4 pt-4 border-t border-white/20">
                  <span className="text-sm text-white/70">Participants:</span>
                  <div className="flex items-center gap-2 flex-wrap">
                    {currentSimulation.participants.map(p => (
                      <div key={p.id} className="flex items-center gap-2 bg-white/10 rounded-full px-3 py-1">
                        <PersonaAvatar name={p.persona_name} imageUrl={p.persona_image_url} size="sm" showBorder={false} />
                        <span className="text-sm text-white">{p.persona_name}</span>
                        {p.role && <span className="text-xs text-white/60">({p.role})</span>}
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Controls */}
              <div className="flex items-center gap-3">
                {currentSimulation.status === 'pending' && (
                  <>
                    <button
                      onClick={() => handleStartSimulation(true)}
                      disabled={running}
                      className="px-4 py-2 bg-gradient-to-r from-green-400 to-emerald-500 hover:from-green-500 hover:to-emerald-600 disabled:opacity-50 text-white rounded-xl font-medium transition-all duration-200 flex items-center gap-2"
                    >
                      {running ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                      Run Full Simulation
                    </button>
                    <button
                      onClick={() => handleStartSimulation(false)}
                      disabled={running}
                      className="px-4 py-2 bg-white/20 hover:bg-white/30 text-white rounded-xl font-medium transition-all duration-200 flex items-center gap-2"
                    >
                      <SkipForward className="w-4 h-4" />
                      Step by Step
                    </button>
                  </>
                )}

                {currentSimulation.status === 'running' && (
                  <>
                    <button
                      onClick={handleNextTurn}
                      disabled={running}
                      className="px-4 py-2 bg-gradient-to-r from-blue-400 to-indigo-500 hover:from-blue-500 hover:to-indigo-600 disabled:opacity-50 text-white rounded-xl font-medium transition-all duration-200 flex items-center gap-2"
                    >
                      {running ? <Loader2 className="w-4 h-4 animate-spin" /> : <SkipForward className="w-4 h-4" />}
                      Next Turn
                    </button>
                    <button
                      onClick={handleStopSimulation}
                      disabled={running}
                      className="px-4 py-2 bg-red-500/30 hover:bg-red-500/50 text-red-200 rounded-xl font-medium transition-all duration-200 flex items-center gap-2"
                    >
                      <Pause className="w-4 h-4" />
                      Stop
                    </button>
                  </>
                )}

                {(currentSimulation.status === 'completed' || currentSimulation.status === 'stopped') &&
                  currentSimulation.messages.length > 0 && !currentSimulation.summary && (
                  <button
                    onClick={handleGenerateSummary}
                    disabled={generatingSummary}
                    className="px-4 py-2 bg-gradient-to-r from-purple-400 to-pink-400 hover:from-purple-500 hover:to-pink-500 disabled:opacity-50 text-white rounded-xl font-medium transition-all duration-200 flex items-center gap-2"
                  >
                    {generatingSummary ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileText className="w-4 h-4" />}
                    Generate Summary
                  </button>
                )}
              </div>

              {/* Messages */}
              <div className="glass-card rounded-2xl p-4 pastel-pink min-h-[400px] max-h-[600px] overflow-y-auto">
                {currentSimulation.messages.length === 0 ? (
                  <div className="flex items-center justify-center h-64 text-white/60">
                    <div className="text-center">
                      <MessageSquare className="w-12 h-12 mx-auto mb-3 opacity-50" />
                      <p>No messages yet. Start the simulation to begin the conversation.</p>
                    </div>
                  </div>
                ) : (
                  <>
                    {currentSimulation.messages.map((msg, idx) => (
                      <MessageBubble
                        key={msg.id}
                        message={msg}
                        isLeft={idx % 2 === 0}
                      />
                    ))}
                    <div ref={messagesEndRef} />
                  </>
                )}

                {running && (
                  <div className="flex items-center justify-center py-4">
                    <Loader2 className="w-6 h-6 text-white/60 animate-spin" />
                    <span className="ml-2 text-white/60">Generating response...</span>
                  </div>
                )}
              </div>

              {/* Summary */}
              {currentSimulation.summary && (
                <div className="glass-card rounded-2xl p-6 pastel-purple">
                  <h4 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                    <FileText className="w-5 h-5" />
                    Simulation Summary
                  </h4>

                  <div className="mb-4">
                    <p className="text-white/90 leading-relaxed">{currentSimulation.summary}</p>
                  </div>

                  {currentSimulation.key_insights && currentSimulation.key_insights.length > 0 && (
                    <div className="mb-4">
                      <h5 className="text-sm font-semibold text-white uppercase tracking-wide mb-2">Key Insights</h5>
                      <ul className="space-y-2">
                        {currentSimulation.key_insights.map((insight, idx) => (
                          <li key={idx} className="flex items-start gap-2 text-white/80 text-sm">
                            <Sparkles className="w-4 h-4 text-yellow-300 flex-shrink-0 mt-0.5" />
                            {insight}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {currentSimulation.action_items && currentSimulation.action_items.length > 0 && (
                    <div>
                      <h5 className="text-sm font-semibold text-white uppercase tracking-wide mb-2">Action Items</h5>
                      <ul className="space-y-2">
                        {currentSimulation.action_items.map((item, idx) => (
                          <li key={idx} className="flex items-start gap-2 text-white/80 text-sm">
                            <CheckCircle className="w-4 h-4 text-green-300 flex-shrink-0 mt-0.5" />
                            {item}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </div>
          ) : (
            <div className="glass-card rounded-2xl p-12 text-center">
              <MessageSquare className="w-16 h-16 mx-auto mb-4 text-white/30" />
              <h3 className="text-xl font-semibold text-white mb-2">No Simulation Selected</h3>
              <p className="text-white/60 mb-6">Select an existing simulation or create a new one</p>
              <button
                onClick={() => setShowSetup(true)}
                className="px-6 py-3 bg-gradient-to-r from-purple-400 to-pink-400 hover:from-purple-500 hover:to-pink-500 text-white rounded-xl font-medium transition-all duration-200"
              >
                Create New Simulation
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
