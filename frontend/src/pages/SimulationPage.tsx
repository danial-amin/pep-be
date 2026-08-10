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
  FileText,
  ArrowLeft,
  Plus,
  CheckCircle,
  Loader2,
  Sparkles,
  Download,
  TrendingUp,
  Activity,
  ChevronDown,
  ChevronRight,
  BarChart3
} from 'lucide-react';
import { simulationsApi, personasApi, studyApi, API_BASE_URL, getAuthToken } from '../services/api';
import {
  STUDY_SIMULATION_DEFAULT_CONTEXT,
  STUDY_SIMULATION_DEFAULT_GOAL,
  shouldUseStudySimulationDefaults,
} from '../studySimulationDefaults';
import {
  Simulation,
  SimulationMessage,
  PersonaSet,
  Persona,
  SimulationListItem,
  AgreementHistory,
  AgreementEvaluation,
  SimulationEvaluationScores,
} from '../types';
import { getPersonaImageUrl } from '../utils/imageUtils';
import { getStudyScope, setStudyScope, studyPath, useStudyTracker } from '../hooks/useStudyTracker';
import { useAuth } from '../context/AuthContext';

// Persona Avatar Component (use personaId when available so API serves from file or base64)
function PersonaAvatar({
  name,
  imageUrl,
  personaId,
  size = 'md',
  showBorder = true
}: {
  name: string;
  imageUrl?: string | null;
  personaId?: number;
  size?: 'sm' | 'md' | 'lg';
  showBorder?: boolean;
}) {
  const [imageError, setImageError] = useState(false);
  const sizeClasses = {
    sm: 'w-8 h-8 text-sm',
    md: 'w-12 h-12 text-lg',
    lg: 'w-16 h-16 text-xl'
  };
  const src = getPersonaImageUrl(imageUrl, personaId);

  if (src && !imageError) {
    return (
      <img
        src={src}
        alt={name}
        className={`${sizeClasses[size]} object-cover rounded-full ${showBorder ? 'border-2 border-stone-200' : ''}`}
        onError={() => setImageError(true)}
      />
    );
  }

  return (
    <div className={`${sizeClasses[size]} rounded-full ${showBorder ? 'border-2 border-stone-200' : ''} bg-stone-200 flex items-center justify-center`}>
      <span className="text-stone-600 font-semibold">
        {name.charAt(0).toUpperCase()}
      </span>
    </div>
  );
}

// Message Bubble Component
function MessageBubble({ message, isLeft }: { message: SimulationMessage; isLeft: boolean }) {
  const isHuman = message.is_human_message ?? (message.persona_id == null);
  const displayName = isHuman ? 'Facilitator (you)' : message.persona_name;

  if (isHuman) {
    return (
      <div className="flex justify-center mb-4">
        <div className="flex items-start gap-3 max-w-[85%]">
          <div className="rounded-2xl px-4 py-3 bg-amber-50 border border-amber-200 shadow-sm">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-sm font-semibold text-amber-700">{displayName}</span>
              <span className="text-xs text-amber-500">Intervention</span>
            </div>
            <p className="text-stone-900/95 text-sm leading-relaxed">{message.content}</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`flex ${isLeft ? 'justify-start' : 'justify-end'} mb-4`}>
      <div className={`flex ${isLeft ? 'flex-row' : 'flex-row-reverse'} items-start gap-3 max-w-[80%]`}>
        <PersonaAvatar
          name={message.persona_name}
          imageUrl={message.persona_image_url}
          personaId={message.persona_id ?? undefined}
          size="sm"
        />
        <div className={`${isLeft ? 'bg-stone-50 border border-stone-100' : 'bg-white border border-stone-200'} rounded-2xl px-4 py-3`}>
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <span className="text-sm font-semibold text-stone-900">{message.persona_name}</span>
            <span className="text-xs text-stone-400">Turn {message.turn_number}</span>
            {message.persona_drift_score !== undefined && (
              <span
                title={`Persona drift: ${(message.persona_drift_score * 100).toFixed(0)}% (0=on-persona, 100=fully drifted)`}
                className={`text-xs px-1.5 py-0.5 rounded-full ${
                  message.persona_drift_score > 0.6 ? 'bg-red-50 text-red-600' :
                  message.persona_drift_score > 0.3 ? 'bg-amber-50 text-amber-600' :
                  'bg-green-50 text-green-600'
                }`}
              >
                drift {(message.persona_drift_score * 100).toFixed(0)}%
              </span>
            )}
          </div>
          <p className="text-stone-700 text-sm leading-relaxed">{message.content}</p>
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
          ? 'border-stone-900 bg-stone-50'
          : 'border-stone-200 hover:border-stone-200'
      }`}
      onClick={onToggle}
    >
      <div className="flex items-center gap-3">
        <PersonaAvatar
          name={persona.name}
          imageUrl={persona.image_url}
          personaId={persona.id}
          size="md"
        />
        <div className="flex-1 min-w-0">
          <h4 className="text-stone-900 font-semibold truncate">{personaData.name || persona.name}</h4>
          <p className="text-stone-500 text-sm truncate">
            {demographics.occupation || 'No occupation'}
          </p>
        </div>
        <div className={`w-6 h-6 rounded-full flex items-center justify-center ${
          isSelected ? 'bg-stone-900' : 'bg-stone-100'
        }`}>
          {isSelected && <CheckCircle className="w-4 h-4 text-stone-900" />}
        </div>
      </div>

      {isSelected && (
        <div className="mt-3" onClick={e => e.stopPropagation()}>
          <input
            type="text"
            placeholder="Role (optional): e.g., moderator, critic"
            value={role}
            onChange={(e) => onRoleChange(e.target.value)}
            className="w-full px-3 py-2 text-sm bg-stone-50 border border-stone-200 rounded-lg text-stone-900 placeholder:text-stone-400 focus:outline-none focus:ring-2 focus:ring-purple-400"
          />
        </div>
      )}
    </div>
  );
}

// Main Simulation Page
export default function SimulationPage() {
  const navigate = useNavigate();
  const { slug: studySlugParam, simulationId } = useParams<{
    slug?: string;
    simulationId?: string;
  }>();
  const { user } = useAuth();
  const studySlug = studySlugParam || (user?.is_study_participant ? user.study_slug : null) || null;
  const isStudyMode = !!studySlugParam || !!user?.is_study_participant;
  const studyScope = getStudyScope();
  const { track } = useStudyTracker(studySlug);
  const useStudyDefaults = shouldUseStudySimulationDefaults(user?.participant_code);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const streamRef = useRef<AbortController | null>(null);
  const autoContinueRef = useRef(!isStudyMode);
  const streamingMessageRef = useRef<SimulationMessage | null>(null);

  // State
  const [personaSets, setPersonaSets] = useState<PersonaSet[]>([]);
  const [simulations, setSimulations] = useState<SimulationListItem[]>([]);
  const [currentSimulation, setCurrentSimulation] = useState<Simulation | null>(null);
  const [loading, setLoading] = useState(false);
  const [running, setRunning] = useState(false);
  const [generatingSummary, setGeneratingSummary] = useState(false);
  const [streamingMessage, setStreamingMessage] = useState<SimulationMessage | null>(null);
  const [autoContinue, setAutoContinue] = useState(!isStudyMode);
  const [streamingEnabled, setStreamingEnabled] = useState(true);
  const [interventionText, setInterventionText] = useState('');
  const [intervening, setIntervening] = useState(false);

  // Setup form state
  const [showSetup, setShowSetup] = useState(!simulationId);
  const [expandedSetIds, setExpandedSetIds] = useState<Set<number>>(new Set());
  const [selectedPersonas, setSelectedPersonas] = useState<Map<number, string>>(new Map());
  const [name, setName] = useState('');
  const [goal, setGoal] = useState('');
  const [goalContext, setGoalContext] = useState('');
  const [maxTurns, setMaxTurns] = useState(10);
  const [runUntilAgreement, setRunUntilAgreement] = useState(false);
  const [agreementThreshold, setAgreementThreshold] = useState(0.7);

  // Agreement state
  const [agreementHistory, setAgreementHistory] = useState<AgreementHistory | null>(null);
  const [showAgreementHistory, setShowAgreementHistory] = useState(false);
  const [evaluatingAgreement, setEvaluatingAgreement] = useState(false);

  // LLM-as-judge evaluation state
  const [evaluatingDiscussion, setEvaluatingDiscussion] = useState(false);
  const [evaluationScores, setEvaluationScores] = useState<SimulationEvaluationScores | null>(null);
  const [showEvaluationScores, setShowEvaluationScores] = useState(false);

  // Study mode: always proceed turn-by-turn (no auto-continue)
  useEffect(() => {
    if (isStudyMode) {
      setAutoContinue(false);
      autoContinueRef.current = false;
    }
  }, [isStudyMode]);

  // Prefill study scenario for PX / P01… participants on the create form
  useEffect(() => {
    if (!useStudyDefaults || !showSetup || !!simulationId) return;
    setGoal((prev) => (prev.trim() ? prev : STUDY_SIMULATION_DEFAULT_GOAL));
    setGoalContext((prev) => (prev.trim() ? prev : STUDY_SIMULATION_DEFAULT_CONTEXT));
  }, [useStudyDefaults, showSetup, simulationId, user?.participant_code]);

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
  }, [currentSimulation?.messages, streamingMessage?.content]);

  useEffect(() => {
    autoContinueRef.current = autoContinue;
  }, [autoContinue]);

  useEffect(() => {
    streamingMessageRef.current = streamingMessage;
  }, [streamingMessage]);

  useEffect(() => {
    return () => {
      if (streamRef.current) {
        streamRef.current.abort();
        streamRef.current = null;
      }
    };
  }, []);

  const loadPersonaSets = async () => {
    try {
      const projectId = isStudyMode ? studyScope?.projectId ?? undefined : undefined;
      const data = await personasApi.getAllSets(projectId);
      const scoped =
        isStudyMode && studyScope?.personaSetId
          ? data.filter((s: PersonaSet) => s.id === studyScope.personaSetId)
          : data;
      let effective = scoped.length > 0 ? scoped : data;

      // Study: reorder set personas to this participant's Latin-square order
      let studyOrder: number[] | null = null;
      if (isStudyMode && studySlug) {
        try {
          const studyPersonas = await studyApi.getPersonas(studySlug);
          studyOrder = studyPersonas.persona_order || null;
          if (studyOrder?.length && effective.length > 0) {
            const set = { ...effective[0] };
            const byId = new Map(set.personas.map((p: Persona) => [p.id, p]));
            const ordered = studyOrder.map((id) => byId.get(id)).filter(Boolean) as Persona[];
            const seen = new Set(studyOrder);
            ordered.push(...set.personas.filter((p: Persona) => !seen.has(p.id)));
            set.personas = ordered;
            effective = [set, ...effective.slice(1)];
          }
        } catch (e) {
          console.error('Failed to load study persona order:', e);
        }
      }

      setPersonaSets(effective);
      if (isStudyMode && effective.length > 0) {
        const set = effective[0];
        setExpandedSetIds(new Set([set.id]));
        // Insert into Map in Latin-square order so create() preserves speaking order
        const next = new Map<number, string>();
        const ids = studyOrder?.length
          ? [
              ...studyOrder.filter((id: number) => set.personas.some((p: Persona) => p.id === id)),
              ...set.personas.map((p: Persona) => p.id).filter((id: number) => !studyOrder!.includes(id)),
            ]
          : set.personas.map((p: Persona) => p.id);
        ids.forEach((id: number) => next.set(id, ''));
        setSelectedPersonas(next);
        if (studySlug) {
          setStudyScope({
            slug: studySlug,
            projectId: studyScope?.projectId ?? set.project_id ?? null,
            personaSetId: set.id,
          });
        }
      }
    } catch (error) {
      console.error('Failed to load persona sets:', error);
    }
  };

  const loadSimulations = async () => {
    try {
      const data = await simulationsApi.getAll(
        isStudyMode ? studyScope?.projectId ?? undefined : undefined
      );
      setSimulations(data);
    } catch (error) {
      console.error('Failed to load simulations:', error);
    }
  };

  const loadEvaluationScores = async (id: number) => {
    try {
      const data = await simulationsApi.getEvaluationScores(id);
      setEvaluationScores(data);
      if (data.has_evaluation) {
        setShowEvaluationScores(true);
      }
    } catch (error) {
      console.error('Failed to load evaluation scores:', error);
    }
  };

  const loadSimulation = async (id: number) => {
    if (streamRef.current) {
      streamRef.current.abort();
      streamRef.current = null;
    }
    setStreamingMessage(null);
    setLoading(true);
    try {
      const data = await simulationsApi.getById(id);
      setCurrentSimulation(data);
      setShowSetup(false);
      if (data.status === 'completed' || data.status === 'stopped') {
        await loadEvaluationScores(id);
      } else {
        setEvaluationScores(null);
        setShowEvaluationScores(false);
      }
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

  const closeStream = () => {
    if (streamRef.current) {
      streamRef.current.abort();
      streamRef.current = null;
    }
  };

  const startStreamingTurn = (shouldAutoContinue: boolean) => {
    if (!currentSimulation) return;

    closeStream();
    setRunning(true);
    setStreamingMessage(null);

    const streamUrl = `${API_BASE_URL}/simulations/${currentSimulation.id}/stream`;
    
    // Use fetch with ReadableStream for better error handling and CORS support
    const abortController = new AbortController();
    const token = getAuthToken();
    
    fetch(streamUrl, {
      signal: abortController.signal,
      headers: {
        'Accept': 'text/event-stream',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    })
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const reader = response.body?.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        if (!reader) {
          throw new Error('No response body');
        }

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6));

                if (data.type === 'start') {
                  setCurrentSimulation(prev => {
                    if (!prev) return prev;
                    const personaImageUrl = prev.participants.find(
                      p => p.persona_id === data.persona_id
                    )?.persona_image_url;

                    setStreamingMessage({
                      id: -1,
                      persona_id: data.persona_id,
                      persona_name: data.persona_name,
                      persona_image_url: personaImageUrl,
                      content: '',
                      turn_number: data.turn_number,
                      tokens: 0,
                      is_moderator_message: false,
                      created_at: new Date().toISOString()
                    });

                    return { ...prev, status: 'running' };
                  });
                  continue;
                }

                if (data.type === 'chunk') {
                  setStreamingMessage(prev =>
                    prev ? { ...prev, content: prev.content + data.content } : prev
                  );
                  continue;
                }

                if (data.type === 'complete') {
                  const finalized = streamingMessageRef.current
                    ? {
                        ...streamingMessageRef.current,
                        id: data.message_id ?? streamingMessageRef.current.id,
                        tokens: data.tokens ?? streamingMessageRef.current.tokens
                      }
                    : null;

                  const evalResult: AgreementEvaluation | undefined = data.agreement_evaluation;

                  setCurrentSimulation(prev => {
                    if (!prev) return prev;
                    return {
                      ...prev,
                      status: data.simulation_status ?? prev.status,
                      current_turn: data.current_turn ?? prev.current_turn,
                      tokens_used: data.tokens_used ?? prev.tokens_used,
                      messages: finalized ? [...prev.messages, finalized] : prev.messages,
                      latest_agreement_score: evalResult?.overall_agreement_score ?? prev.latest_agreement_score,
                      agreement_reached: evalResult?.agreement_reached ?? prev.agreement_reached
                    };
                  });

                  if (evalResult) {
                    setAgreementHistory(prev => {
                      if (!prev) return null;
                      return { ...prev, evaluations: [...prev.evaluations, evalResult] };
                    });
                  }

                  setStreamingMessage(null);
                  setRunning(false);
                  closeStream();
                  loadSimulations();

                  if (finalized) {
                    track('simulation_turn_message', {
                      simulation_id: currentSimulation.id,
                      turn_number: finalized.turn_number,
                      persona_id: finalized.persona_id,
                      is_human: finalized.is_human_message ?? finalized.persona_id == null,
                      content: finalized.content,
                      chars: (finalized.content || '').length,
                      streamed: true,
                    });
                  }

                  if (
                    shouldAutoContinue &&
                    autoContinueRef.current &&
                    data.simulation_status === 'running'
                  ) {
                    setTimeout(() => startStreamingTurn(true), 400);
                  }
                  return;
                }

                if (data.type === 'error') {
                  console.error('Streaming error:', data.message);
                  alert(data.message || 'Streaming error');
                  setRunning(false);
                  closeStream();
                  return;
                }
              } catch (parseError) {
                console.error('Failed to parse SSE data:', parseError, line);
              }
            }
          }
        }
      })
      .catch((error) => {
        if (error.name === 'AbortError') {
          // Stream was intentionally closed
          return;
        }
        console.error('Streaming fetch error:', error);
        alert(`Failed to stream simulation: ${error.message}`);
        setRunning(false);
        closeStream();
      });

    // Store abort controller for cleanup
    streamRef.current = abortController;
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
      // Preserve Map insertion order (= study Latin-square order in study mode)

      const simulation = await simulationsApi.create({
        name: name || `Simulation - ${new Date().toLocaleString()}`,
        goal,
        goal_context: goalContext || undefined,
        participants,
        max_turns: maxTurns,
        run_until_agreement: runUntilAgreement || undefined,
        agreement_threshold: runUntilAgreement ? agreementThreshold : undefined,
        project_id: isStudyMode ? studyScope?.projectId ?? undefined : undefined,
      });

      setCurrentSimulation(simulation);
      setShowSetup(false);
      track('simulation_create', {
        simulation_id: simulation.id,
        name: simulation.name,
        goal,
        goal_context: goalContext || null,
        max_turns: maxTurns,
        run_until_agreement: runUntilAgreement || false,
        participants,
        participant_count: participants.length,
        project_id: studyScope?.projectId,
        persona_set_id: studyScope?.personaSetId,
      });
      if (studySlug) {
        navigate(studyPath(studySlug, `/simulations/${simulation.id}`));
      } else {
        navigate(`/simulations/${simulation.id}`);
      }
      await loadSimulations();
    } catch (error: any) {
      alert(`Failed to create simulation: ${error.response?.data?.detail || error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleStartSimulation = async (autoContinue: boolean = true) => {
    if (!currentSimulation) return;

    track('simulation_start', {
      simulation_id: currentSimulation.id,
      auto_continue: autoContinue,
      streaming: streamingEnabled,
    });

    if (streamingEnabled) {
      startStreamingTurn(autoContinue);
      return;
    }

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

  const handleIntervene = async () => {
    if (!currentSimulation || !interventionText.trim() || running) return;
    setIntervening(true);
    const text = interventionText.trim();
    const simId = currentSimulation.id;
    try {
      await simulationsApi.intervene(simId, text);
      track('simulation_intervention', {
        simulation_id: simId,
        message: text,
        chars: text.length,
      });
      setInterventionText('');
      let updated = await simulationsApi.getById(simId);
      setCurrentSimulation(updated);

      // Intervention should immediately advance the discussion with a persona reply
      if (updated.status === 'pending' || updated.status === 'running') {
        track('simulation_next_turn', {
          simulation_id: simId,
          current_turn: updated.current_turn,
          streaming: streamingEnabled,
          after_intervention: true,
        });

        if (streamingEnabled) {
          setIntervening(false);
          startStreamingTurn(false);
          return;
        }

        setRunning(true);
        try {
          if (updated.status === 'pending') {
            updated = await simulationsApi.start(simId, false);
          } else {
            await simulationsApi.nextTurn(simId);
            updated = await simulationsApi.getById(simId);
          }
          setCurrentSimulation(updated);
          await loadSimulations();
          const last = updated.messages?.[updated.messages.length - 1];
          if (last) {
            track('simulation_turn_message', {
              simulation_id: simId,
              turn_number: last.turn_number,
              persona_id: last.persona_id,
              is_human: last.is_human_message ?? last.persona_id == null,
              content: last.content,
              chars: (last.content || '').length,
              after_intervention: true,
            });
          }
        } finally {
          setRunning(false);
        }
      }
    } catch (error: any) {
      alert(`Failed to add intervention: ${error.response?.data?.detail || error.message}`);
    } finally {
      setIntervening(false);
    }
  };

  const handleNextTurn = async () => {
    if (!currentSimulation) return;

    track('simulation_next_turn', {
      simulation_id: currentSimulation.id,
      current_turn: currentSimulation.current_turn,
      streaming: streamingEnabled,
    });

    if (streamingEnabled) {
      startStreamingTurn(false);
      return;
    }

    setRunning(true);
    try {
      await simulationsApi.nextTurn(currentSimulation.id);
      // Reload full simulation to get updated state
      const updated = await simulationsApi.getById(currentSimulation.id);
      setCurrentSimulation(updated);
      const last = updated.messages?.[updated.messages.length - 1];
      if (last) {
        track('simulation_turn_message', {
          simulation_id: currentSimulation.id,
          turn_number: last.turn_number,
          persona_id: last.persona_id,
          is_human: last.is_human_message ?? last.persona_id == null,
          content: last.content,
          chars: (last.content || '').length,
        });
      }
    } catch (error: any) {
      alert(`Failed to generate next turn: ${error.response?.data?.detail || error.message}`);
    } finally {
      setRunning(false);
    }
  };

  const handleDownloadSimulation = async () => {
    if (!currentSimulation) return;
    try {
      const data = await simulationsApi.getDownload(currentSimulation.id);
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `simulation-${currentSimulation.id}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (error: any) {
      alert(`Failed to download simulation: ${error.response?.data?.detail || error.message}`);
    }
  };

  const handleStopSimulation = async () => {
    if (!currentSimulation) return;

    closeStream();
    setStreamingMessage(null);
    setRunning(false);
    setAutoContinue(false);

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

  const handleEvaluateAgreement = async () => {
    if (!currentSimulation) return;
    setEvaluatingAgreement(true);
    try {
      await simulationsApi.evaluateAgreement(currentSimulation.id);
      const updated = await simulationsApi.getById(currentSimulation.id);
      setCurrentSimulation(updated);
      const history = await simulationsApi.getAgreementHistory(currentSimulation.id);
      setAgreementHistory(history);
      setShowAgreementHistory(true);
    } catch (error: any) {
      alert(`Failed to evaluate agreement: ${error.response?.data?.detail || error.message}`);
    } finally {
      setEvaluatingAgreement(false);
    }
  };

  const handleEvaluateDiscussion = async () => {
    if (!currentSimulation) return;
    const force = evaluationScores?.has_evaluation ?? false;
    if (force && !window.confirm('Re-run evaluation? Existing scores for this simulation will be replaced.')) {
      return;
    }
    setEvaluatingDiscussion(true);
    try {
      await simulationsApi.evaluate(currentSimulation.id, force);
      await loadEvaluationScores(currentSimulation.id);
      setShowEvaluationScores(true);
    } catch (error: any) {
      alert(`Failed to evaluate discussion: ${error.response?.data?.detail || error.message}`);
    } finally {
      setEvaluatingDiscussion(false);
    }
  };

  const handleNewSimulation = () => {
    closeStream();
    setStreamingMessage(null);
    setCurrentSimulation(null);
    setShowSetup(true);
    setSelectedPersonas(new Map());
    setExpandedSetIds(new Set());
    setName('');
    if (shouldUseStudySimulationDefaults(user?.participant_code)) {
      setGoal(STUDY_SIMULATION_DEFAULT_GOAL);
      setGoalContext(STUDY_SIMULATION_DEFAULT_CONTEXT);
    } else {
      setGoal('');
      setGoalContext('');
    }
    setRunUntilAgreement(false);
    setAgreementThreshold(0.7);
    setAgreementHistory(null);
    setShowAgreementHistory(false);
    setEvaluationScores(null);
    setShowEvaluationScores(false);
    navigate(studySlug ? studyPath(studySlug, '/simulations') : '/simulations');
  };

  const displayMessages = (() => {
    const base = currentSimulation?.messages ? [...currentSimulation.messages] : [];
    if (streamingMessage) base.push(streamingMessage);
    return base.sort((a, b) => {
      const aid = a.id == null || a.id < 0 ? Number.MAX_SAFE_INTEGER : a.id;
      const bid = b.id == null || b.id < 0 ? Number.MAX_SAFE_INTEGER : b.id;
      if (aid !== bid) return aid - bid;
      const at = a.created_at ? Date.parse(a.created_at) : 0;
      const bt = b.created_at ? Date.parse(b.created_at) : 0;
      return at - bt;
    });
  })();

  return (
    <div className="px-4 py-6 sm:px-0">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <button
            onClick={() =>
              navigate(studySlug ? studyPath(studySlug, '/profiles') : '/personas')
            }
            className="p-2 rounded-lg bg-stone-50 hover:bg-stone-100 transition-colors"
          >
            <ArrowLeft className="w-5 h-5 text-stone-900" />
          </button>
          <div>
            <h2 className="text-3xl font-bold text-stone-900 mb-1 ">
              {isStudyMode ? 'Study simulation' : 'Persona Simulation Playground'}
            </h2>
            <p className="text-stone-600 text-lg">
              {isStudyMode
                ? `Signed in as ${user?.participant_code || user?.name || 'participant'} — run a multi-persona discussion`
                : 'Watch your personas collaborate and discuss towards a common goal'}
            </p>
          </div>
        </div>
        {currentSimulation && (
          <button
            onClick={handleNewSimulation}
            className="px-4 py-2 bg-stone-900 hover:bg-stone-800 text-white rounded-xl font-medium transition-all duration-200 flex items-center gap-2"
          >
            <Plus className="w-4 h-4" />
            New Simulation
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Left Sidebar - Simulations List */}
        <div className="lg:col-span-1">
          <div className="glass-card rounded-2xl overflow-hidden">
            <div className="px-4 py-3 border-b border-stone-200">
              <h3 className="text-lg font-semibold text-stone-900">Simulations</h3>
            </div>
            <div className="max-h-[600px] overflow-y-auto">
              {simulations.length === 0 ? (
                <div className="p-4 text-center text-stone-400">
                  No simulations yet
                </div>
              ) : (
                simulations.map(sim => (
                  <div
                    key={sim.id}
                    onClick={() => {
                      if (studySlug) {
                        navigate(studyPath(studySlug, `/simulations/${sim.id}`));
                      } else {
                        void loadSimulation(sim.id);
                      }
                    }}
                    className={`px-4 py-3 cursor-pointer hover:bg-stone-50 transition-colors border-b border-stone-100 ${
                      currentSimulation?.id === sim.id ? 'bg-stone-100' : ''
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <h4 className="text-sm font-medium text-stone-900 truncate">{sim.name}</h4>
                      <span className={`text-xs px-2 py-0.5 rounded-full ${
                        sim.status === 'completed' ? 'bg-green-50 text-green-700' :
                        sim.status === 'running' ? 'bg-blue-50 text-blue-700' :
                        sim.status === 'stopped' ? 'bg-red-50 text-red-600' :
                        'bg-amber-50 text-amber-700'
                      }`}>
                        {sim.status}
                      </span>
                    </div>
                    <p className="text-xs text-stone-400 truncate">{sim.goal}</p>
                    <div className="flex items-center gap-2 mt-1 text-xs text-stone-400">
                      <Users className="w-3 h-3" />
                      <span>{sim.participant_count}</span>
                      <MessageSquare className="w-3 h-3 ml-2" />
                      <span>{sim.current_turn}/{sim.max_turns} rounds</span>
                      {sim.run_until_agreement && (
                        <span title="Run until agreement">
                          <TrendingUp className="w-3 h-3 ml-1 text-stone-400" />
                        </span>
                      )}
                    </div>
                    {sim.latest_agreement_score !== undefined && (
                      <div className="mt-1.5 flex items-center gap-2">
                        <div className="flex-1 bg-stone-50 rounded-full h-1">
                          <div
                            className={`h-1 rounded-full ${sim.agreement_reached ? 'bg-teal-400' : 'bg-purple-400'}`}
                            style={{ width: `${Math.min(sim.latest_agreement_score * 100, 100)}%` }}
                          />
                        </div>
                        <span className="text-xs text-stone-400">
                          {(sim.latest_agreement_score * 100).toFixed(0)}%
                          {sim.agreement_reached && ' ✓'}
                        </span>
                      </div>
                    )}
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
            <div className="glass-card rounded-2xl p-6">
              <h3 className="text-xl font-semibold text-stone-900 mb-6 flex items-center gap-2">
                <Sparkles className="w-5 h-5" />
                Create New Simulation
              </h3>

              {/* Name and Goal */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                <div>
                  <label className="block text-sm font-medium text-stone-700 mb-2">
                    Simulation Name
                  </label>
                  <input
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="e.g., Product Strategy Discussion"
                    className="w-full px-4 py-2 bg-white border border-stone-200 rounded-xl text-stone-900 placeholder:text-stone-400 focus:outline-none focus:ring-2 focus:ring-stone-900/20 focus:border-stone-400"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-stone-700 mb-2">
                    <Target className="w-4 h-4 inline mr-1" />
                    Goal / Topic *
                  </label>
                  <textarea
                    value={goal}
                    onChange={(e) => setGoal(e.target.value)}
                    placeholder="e.g., Discuss how to improve our mobile app UX"
                    rows={useStudyDefaults ? 3 : 2}
                    className="w-full px-4 py-2 bg-white border border-stone-200 rounded-xl text-stone-900 placeholder:text-stone-400 focus:outline-none focus:ring-2 focus:ring-stone-900/20 focus:border-stone-400"
                  />
                </div>
              </div>

              <div className="mb-6">
                <label className="block text-sm font-medium text-stone-700 mb-2">
                  Additional Context {useStudyDefaults ? '' : '(Optional)'}
                </label>
                <textarea
                  value={goalContext}
                  onChange={(e) => setGoalContext(e.target.value)}
                  placeholder="Provide any additional context, constraints, or specific aspects to focus on..."
                  rows={useStudyDefaults ? 12 : 3}
                  className="w-full px-4 py-2 bg-white border border-stone-200 rounded-xl text-stone-900 placeholder:text-stone-400 focus:outline-none focus:ring-2 focus:ring-stone-900/20 focus:border-stone-400"
                />
                {useStudyDefaults && (
                  <p className="mt-1.5 text-xs text-stone-500">
                    Prefilled for study code {user?.participant_code}. You can edit if needed.
                  </p>
                )}
              </div>

              {/* Limits */}
              <div className="mb-6">
                <h4 className="text-sm font-medium text-stone-700 mb-3">
                  Simulation Limits
                </h4>
                <div className="grid grid-cols-1 gap-4">
                  <div>
                    <label className="block text-sm text-stone-500 mb-2">
                      <MessageSquare className="w-4 h-4 inline mr-1" />
                      Number of Turns
                    </label>
                    <select
                      value={maxTurns}
                      onChange={(e) => setMaxTurns(parseInt(e.target.value))}
                      className="w-full px-4 py-2 bg-white border border-stone-200 rounded-xl text-stone-900 focus:outline-none focus:ring-2 focus:ring-stone-900/20 focus:border-stone-400"
                    >
                      <option value={5}>5 turns</option>
                      <option value={10}>10 turns</option>
                      <option value={15}>15 turns</option>
                      <option value={20}>20 turns</option>
                      <option value={30}>30 turns</option>
                      <option value={50}>50 turns</option>
                    </select>
                  </div>
                </div>
                <p className="text-xs text-stone-400 mt-2">
                  One turn = every selected persona speaks once (one full round). Conversation stops only when the turn limit is reached.
                </p>
              </div>

              {/* Agreement Mode */}
              <div className="mb-6 p-4 bg-stone-50 rounded-xl border border-stone-200">
                <label className="flex items-center gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={runUntilAgreement}
                    onChange={(e) => setRunUntilAgreement(e.target.checked)}
                    className="accent-purple-400 w-4 h-4"
                  />
                  <div>
                    <span className="text-sm font-medium text-stone-900 flex items-center gap-1">
                      <TrendingUp className="w-4 h-4 inline" />
                      Run until agreement
                    </span>
                    <p className="text-xs text-stone-400 mt-0.5">
                      Continue beyond max turns until personas reach the alignment threshold
                    </p>
                  </div>
                </label>
                {runUntilAgreement && (
                  <div className="mt-4">
                    <label className="block text-sm text-stone-500 mb-2">
                      Agreement threshold: <span className="text-stone-900 font-semibold">{(agreementThreshold * 100).toFixed(0)}%</span>
                    </label>
                    <input
                      type="range"
                      min={0.1}
                      max={1.0}
                      step={0.05}
                      value={agreementThreshold}
                      onChange={(e) => setAgreementThreshold(parseFloat(e.target.value))}
                      className="w-full accent-purple-400"
                    />
                    <div className="flex justify-between text-xs text-stone-400 mt-1">
                      <span>10% (loose)</span>
                      <span>100% (full)</span>
                    </div>
                  </div>
                )}
              </div>

              {/* Persona Selection — pick from any set */}
              <div className="mb-6">
                <div className="flex items-center justify-between mb-3">
                  <label className="text-sm font-medium text-stone-700 flex items-center gap-1">
                    <Users className="w-4 h-4" />
                    Select Participants (2–12 personas, mix from any set)
                  </label>
                  <span className="text-sm text-stone-400">{selectedPersonas.size} selected</span>
                </div>

                {personaSets.length === 0 ? (
                  <p className="text-stone-400 text-sm">No persona sets found.</p>
                ) : (
                  <div className="space-y-3 max-h-[500px] overflow-y-auto pr-1">
                    {personaSets.map(set => {
                      const isExpanded = expandedSetIds.has(set.id);
                      const selectedInSet = set.personas.filter(p => selectedPersonas.has(p.id)).length;
                      return (
                        <div key={set.id} className="border border-stone-200 rounded-xl overflow-hidden">
                          <button
                            type="button"
                            onClick={() => {
                              const next = new Set(expandedSetIds);
                              isExpanded ? next.delete(set.id) : next.add(set.id);
                              setExpandedSetIds(next);
                            }}
                            className="w-full flex items-center justify-between px-4 py-3 bg-stone-50 hover:bg-stone-50 transition-colors text-left"
                          >
                            <span className="text-sm font-medium text-stone-900">
                              {set.name}
                              <span className="ml-2 text-stone-400 font-normal">({set.personas.length} personas)</span>
                              {selectedInSet > 0 && (
                                <span className="ml-2 text-xs bg-violet-50 text-violet-700 px-2 py-0.5 rounded-full">
                                  {selectedInSet} selected
                                </span>
                              )}
                            </span>
                            {isExpanded ? <ChevronDown className="w-4 h-4 text-stone-400" /> : <ChevronRight className="w-4 h-4 text-stone-400" />}
                          </button>
                          {isExpanded && (
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 p-3">
                              {set.personas.map(persona => (
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
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* Create Button */}
              <button
                onClick={handleCreateSimulation}
                disabled={loading || selectedPersonas.size < 2 || !goal.trim()}
                className="w-full px-6 py-3 bg-stone-900 hover:bg-stone-800 disabled:opacity-50 text-white rounded-xl font-medium transition-all duration-200 flex items-center justify-center gap-2"
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
              <div className="glass-card rounded-2xl p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-xl font-semibold text-stone-900">{currentSimulation.name}</h3>
                    <p className="text-stone-600 mt-1">{currentSimulation.goal}</p>
                  </div>
                  <div className="flex items-center gap-3 flex-wrap justify-end">
                    {/* Status Badge */}
                    <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                      currentSimulation.status === 'completed' ? 'bg-green-50 text-green-700' :
                      currentSimulation.status === 'running' ? 'bg-blue-50 text-blue-700' :
                      currentSimulation.status === 'stopped' ? 'bg-red-50 text-red-600' :
                      'bg-amber-50 text-amber-700'
                    }`}>
                      {currentSimulation.status}
                    </span>

                    {/* Agreement reached badge */}
                    {currentSimulation.agreement_reached && (
                      <span className="px-3 py-1 rounded-full text-sm font-medium bg-teal-50 text-teal-700 flex items-center gap-1">
                        <CheckCircle className="w-3.5 h-3.5" />
                        Agreement reached
                      </span>
                    )}

                    {/* Agreement mode indicator */}
                    {currentSimulation.run_until_agreement && !currentSimulation.agreement_reached && (
                      <span className="px-3 py-1 rounded-full text-sm bg-violet-50 text-violet-700 flex items-center gap-1">
                        <TrendingUp className="w-3.5 h-3.5" />
                        Until {(currentSimulation.agreement_threshold * 100).toFixed(0)}% agreement
                      </span>
                    )}

                    {/* Download JSON */}
                    {currentSimulation.status === 'completed' && (
                      <button
                        type="button"
                        onClick={handleDownloadSimulation}
                        className="px-3 py-1.5 rounded-xl bg-stone-100 hover:bg-stone-100 text-stone-900 text-sm font-medium transition-all duration-200 flex items-center gap-2"
                        title="Download simulation as JSON"
                      >
                        <Download className="w-4 h-4" />
                        Download JSON
                      </button>
                    )}

                    {/* Progress */}
                    <div className="text-right">
                      <div className="text-sm text-stone-600">
                        <MessageSquare className="w-4 h-4 inline mr-1" />
                        {currentSimulation.current_turn} / {currentSimulation.max_turns} rounds done
                      </div>
                      <div className="text-xs text-stone-400">
                        <Clock className="w-3 h-3 inline mr-1" />
                        {/* Turn-limit only; duration limit intentionally disabled */}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Participants */}
                <div className="flex items-center gap-4 mt-4 pt-4 border-t border-stone-200">
                  <span className="text-sm text-stone-500">Participants:</span>
                  <div className="flex items-center gap-2 flex-wrap">
                    {currentSimulation.participants.map(p => (
                      <div key={p.id} className="flex items-center gap-2 bg-stone-50 rounded-full px-3 py-1">
                        <PersonaAvatar name={p.persona_name} imageUrl={p.persona_image_url} personaId={p.persona_id} size="sm" showBorder={false} />
                        <span className="text-sm text-stone-900">{p.persona_name}</span>
                        {p.role && <span className="text-xs text-stone-400">({p.role})</span>}
                        {p.persona_set_name && (
                          <span className="text-xs text-stone-300 italic">{p.persona_set_name}</span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>

                {/* Agreement score bar */}
                {currentSimulation.latest_agreement_score !== undefined && (
                  <div className="mt-3 pt-3 border-t border-stone-200">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs text-stone-500 flex items-center gap-1">
                        <Activity className="w-3 h-3" />
                        Agreement score
                      </span>
                      <span className="text-xs text-stone-900 font-semibold">
                        {(currentSimulation.latest_agreement_score * 100).toFixed(0)}%
                        {currentSimulation.run_until_agreement && (
                          <span className="text-stone-400 font-normal ml-1">
                            / {(currentSimulation.agreement_threshold * 100).toFixed(0)}% target
                          </span>
                        )}
                      </span>
                    </div>
                    <div className="w-full bg-stone-50 rounded-full h-2">
                      <div
                        className={`h-2 rounded-full transition-all duration-500 ${
                          currentSimulation.agreement_reached ? 'bg-teal-400' :
                          currentSimulation.latest_agreement_score > 0.6 ? 'bg-green-400' :
                          currentSimulation.latest_agreement_score > 0.3 ? 'bg-yellow-400' :
                          'bg-red-400'
                        }`}
                        style={{ width: `${Math.min(currentSimulation.latest_agreement_score * 100, 100)}%` }}
                      />
                    </div>
                  </div>
                )}
              </div>

              {/* Controls */}
              <div className="flex items-center gap-3 flex-wrap">
                {currentSimulation.status === 'pending' && (
                  <>
                    {isStudyMode ? (
                      <button
                        onClick={() => handleStartSimulation(false)}
                        disabled={running}
                        className="px-4 py-2 bg-green-700 hover:bg-green-800 disabled:opacity-50 text-white rounded-xl font-medium transition-all duration-200 flex items-center gap-2"
                      >
                        {running ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                        Start (step by step)
                      </button>
                    ) : (
                      <>
                        <button
                          onClick={() => handleStartSimulation(autoContinue)}
                          disabled={running}
                          className="px-4 py-2 bg-green-700 hover:bg-green-800 disabled:opacity-50 text-stone-900 rounded-xl font-medium transition-all duration-200 flex items-center gap-2"
                        >
                          {running ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                          Run Full Simulation
                        </button>
                        <button
                          onClick={() => handleStartSimulation(false)}
                          disabled={running}
                          className="px-4 py-2 bg-stone-100 hover:bg-stone-100 text-stone-900 rounded-xl font-medium transition-all duration-200 flex items-center gap-2"
                        >
                          <SkipForward className="w-4 h-4" />
                          Step by Step
                        </button>
                      </>
                    )}
                  </>
                )}

                {currentSimulation.status === 'running' && (
                  <button
                    onClick={handleStopSimulation}
                    disabled={running}
                    className="px-4 py-2 bg-red-50 hover:bg-red-100 text-red-700 rounded-xl font-medium transition-all duration-200 flex items-center gap-2"
                  >
                    <Pause className="w-4 h-4" />
                    Stop
                  </button>
                )}

                {!isStudyMode && (
                  <div className="flex items-center gap-4 text-sm text-stone-500">
                    <label className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={streamingEnabled}
                        onChange={(e) => setStreamingEnabled(e.target.checked)}
                        className="accent-white"
                      />
                      Stream responses
                    </label>
                    <label className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={autoContinue}
                        onChange={(e) => setAutoContinue(e.target.checked)}
                        className="accent-white"
                      />
                      Auto-continue turns
                    </label>
                  </div>
                )}

                <button
                  type="button"
                  onClick={() =>
                    navigate(
                      studySlug
                        ? studyPath(studySlug, `/simulations/${currentSimulation.id}/persona-chats`)
                        : `/simulations/${currentSimulation.id}/persona-chats`
                    )
                  }
                  className="px-4 py-2 rounded-xl font-medium transition-all duration-200 flex items-center gap-2 bg-stone-100 text-stone-900 hover:bg-stone-100"
                  title="Open personas + chats view"
                >
                  <Users className="w-4 h-4" />
                  Personas + Chats
                </button>

                {currentSimulation.messages.length > 0 && (
                  <button
                    onClick={handleEvaluateAgreement}
                    disabled={evaluatingAgreement || running}
                    className="px-4 py-2 bg-stone-100 hover:bg-stone-100 disabled:opacity-50 text-stone-900 rounded-xl font-medium transition-all duration-200 flex items-center gap-2"
                    title="Evaluate agreement among personas at this point"
                  >
                    {evaluatingAgreement ? <Loader2 className="w-4 h-4 animate-spin" /> : <Activity className="w-4 h-4" />}
                    Evaluate Agreement
                  </button>
                )}

                {agreementHistory && agreementHistory.evaluations.length > 0 && (
                  <button
                    onClick={() => setShowAgreementHistory(v => !v)}
                    className="px-4 py-2 bg-stone-100 hover:bg-stone-100 text-stone-900 rounded-xl font-medium transition-all duration-200 flex items-center gap-2"
                  >
                    <TrendingUp className="w-4 h-4" />
                    {showAgreementHistory ? 'Hide' : 'Show'} History
                  </button>
                )}

                {(currentSimulation.status === 'completed' || currentSimulation.status === 'stopped') &&
                  currentSimulation.messages.length > 0 && (
                  <button
                    onClick={handleEvaluateDiscussion}
                    disabled={evaluatingDiscussion}
                    className="px-4 py-2 bg-teal-700 hover:bg-teal-800 disabled:opacity-50 text-white rounded-xl font-medium transition-all duration-200 flex items-center gap-2"
                    title="Score this discussion and every participating persona with LLM judges"
                  >
                    {evaluatingDiscussion ? <Loader2 className="w-4 h-4 animate-spin" /> : <BarChart3 className="w-4 h-4" />}
                    {evaluationScores?.has_evaluation ? 'Re-evaluate Discussion' : 'Evaluate Discussion'}
                  </button>
                )}

                {(currentSimulation.status === 'completed' || currentSimulation.status === 'stopped') &&
                  currentSimulation.messages.length > 0 &&
                  !(currentSimulation.persona_summaries?.length) && !currentSimulation.summary && (
                  <button
                    onClick={handleGenerateSummary}
                    disabled={generatingSummary}
                    className="px-4 py-2 bg-stone-900 hover:bg-stone-800 disabled:opacity-50 text-white rounded-xl font-medium transition-all duration-200 flex items-center gap-2"
                  >
                    {generatingSummary ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileText className="w-4 h-4" />}
                    Generate Summary
                  </button>
                )}

                {evaluationScores?.has_evaluation && (
                  <button
                    onClick={() => setShowEvaluationScores(v => !v)}
                    className="px-4 py-2 bg-stone-100 hover:bg-stone-100 text-stone-900 rounded-xl font-medium transition-all duration-200 flex items-center gap-2"
                  >
                    <BarChart3 className="w-4 h-4" />
                    {showEvaluationScores ? 'Hide' : 'Show'} Evaluation
                  </button>
                )}
              </div>

              {/* Chat area: messages scrollable, intervention box fixed at bottom */}
              <div className="glass-card rounded-2xl overflow-hidden flex flex-col min-h-[480px] max-h-[70vh]">
                {/* Messages - scrollable, takes remaining space */}
                <div className="flex-1 min-h-0 overflow-y-auto p-4">
                  {displayMessages.length === 0 ? (
                    <div className="flex items-center justify-center h-64 text-stone-400">
                      <div className="text-center">
                        <MessageSquare className="w-12 h-12 mx-auto mb-3 opacity-50" />
                        <p>No messages yet. Start the simulation to begin the conversation.</p>
                      </div>
                    </div>
                  ) : (
                    <>
                      {displayMessages.map((msg, idx) => (
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
                      <Loader2 className="w-6 h-6 text-stone-400 animate-spin" />
                      <span className="ml-2 text-stone-400">Generating response...</span>
                    </div>
                  )}
                </div>

                {/* Intervention + Next Turn - fixed at bottom under the chat */}
                {(currentSimulation.status === 'running' || currentSimulation.status === 'pending') && (
                  <div className="flex-shrink-0 p-4 pt-0 border-t border-stone-200">
                    <div className="flex gap-2 items-center flex-wrap">
                      <input
                        type="text"
                        value={interventionText}
                        onChange={(e) => setInterventionText(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && !running && handleIntervene()}
                        placeholder="Facilitator intervention (e.g., Let's focus on cost...)"
                        className="flex-1 min-w-[12rem] px-4 py-2.5 bg-white border border-stone-200 rounded-xl text-stone-900 placeholder:text-stone-400 focus:outline-none focus:ring-2 focus:ring-amber-400"
                        disabled={intervening || running}
                      />
                      <button
                        onClick={handleIntervene}
                        disabled={intervening || running || !interventionText.trim()}
                        className="px-4 py-2.5 bg-amber-100 hover:bg-amber-200 disabled:opacity-50 text-amber-800 rounded-xl font-medium transition-all duration-200 flex items-center gap-2 whitespace-nowrap"
                      >
                        {intervening || running ? <Loader2 className="w-4 h-4 animate-spin" /> : <MessageSquare className="w-4 h-4" />}
                        Intervene
                      </button>
                      {currentSimulation.status === 'running' && (
                        <button
                          onClick={handleNextTurn}
                          disabled={running}
                          className="px-4 py-2.5 bg-stone-900 hover:bg-stone-800 disabled:opacity-50 text-white rounded-xl font-medium transition-all duration-200 flex items-center gap-2 whitespace-nowrap"
                        >
                          {running ? <Loader2 className="w-4 h-4 animate-spin" /> : <SkipForward className="w-4 h-4" />}
                          Next Turn
                        </button>
                      )}
                    </div>
                    <p className="text-xs text-stone-400 mt-1.5">
                      {isStudyMode
                        ? 'Intervene posts your message and immediately runs the next persona turn.'
                        : 'Intervene posts your message and runs the next persona turn, which will address it.'}
                    </p>
                  </div>
                )}
              </div>

              {/* LLM-as-judge Evaluation Panel */}
              {showEvaluationScores && evaluationScores?.has_evaluation && (
                <div className="glass-card rounded-2xl p-6">
                  <div className="flex items-center justify-between mb-4">
                    <h4 className="text-lg font-semibold text-stone-900 flex items-center gap-2">
                      <BarChart3 className="w-5 h-5" />
                      Discussion Evaluation
                    </h4>
                    {evaluationScores.last_evaluated_at && (
                      <span className="text-sm text-stone-400">
                        {new Date(evaluationScores.last_evaluated_at).toLocaleString()}
                      </span>
                    )}
                  </div>

                  {evaluationScores.judge_models.map((model) => {
                    const discussionScores = evaluationScores.scores.filter(
                      s => s.judge_model === model && s.level === 'discussion'
                    );
                    const personaScores = evaluationScores.scores.filter(
                      s => s.judge_model === model && s.level === 'persona'
                    );
                    const personaIds = [...new Set(personaScores.map(s => s.target_id))];

                    return (
                      <div key={model} className="mb-6 last:mb-0">
                        <p className="text-sm font-medium text-stone-600 mb-3">{model}</p>

                        {discussionScores.length > 0 && (
                          <div className="bg-stone-50 rounded-xl p-4 mb-3">
                            <h5 className="text-sm font-semibold text-stone-900 mb-2">Discussion</h5>
                            <div className="space-y-2 max-h-48 overflow-y-auto">
                              {discussionScores.map((score) => (
                                <div key={`${model}-d-${score.item}`} className="text-sm">
                                  <div className="flex justify-between gap-2">
                                    <span className="text-stone-500">{score.item}</span>
                                    <span className="text-stone-900 font-medium text-right">
                                      {score.item_type === 'likert' && score.response_code != null
                                        ? `${score.response_code}/7`
                                        : score.response_label}
                                    </span>
                                  </div>
                                  <p className="text-xs text-stone-400 mt-0.5 line-clamp-2">{score.justification}</p>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {personaIds.map((personaId) => {
                          const scores = personaScores.filter(s => s.target_id === personaId);
                          const name = scores[0]?.persona_name || `Persona ${personaId}`;
                          return (
                            <div key={`${model}-p-${personaId}`} className="bg-stone-50 rounded-xl p-4 mb-3 last:mb-0">
                              <h5 className="text-sm font-semibold text-stone-900 mb-2">{name}</h5>
                              <div className="space-y-2 max-h-40 overflow-y-auto">
                                {scores.map((score) => (
                                  <div key={`${model}-p-${personaId}-${score.item}`} className="text-sm">
                                    <div className="flex justify-between gap-2">
                                      <span className="text-stone-500">{score.item}</span>
                                      <span className="text-stone-900 font-medium text-right">
                                        {score.item_type === 'likert' && score.response_code != null
                                          ? `${score.response_code}/7`
                                          : score.response_label}
                                      </span>
                                    </div>
                                  </div>
                                ))}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    );
                  })}
                </div>
              )}

              {/* Agreement History Panel */}
              {showAgreementHistory && agreementHistory && agreementHistory.evaluations.length > 0 && (
                <div className="glass-card rounded-2xl p-6">
                  <div className="flex items-center justify-between mb-4">
                    <h4 className="text-lg font-semibold text-stone-900 flex items-center gap-2">
                      <TrendingUp className="w-5 h-5" />
                      Agreement History
                    </h4>
                    <span className="text-sm text-stone-400">
                      Target: {(agreementHistory.agreement_threshold * 100).toFixed(0)}%
                      {agreementHistory.agreement_reached && (
                        <span className="ml-2 text-teal-600">✓ Reached</span>
                      )}
                    </span>
                  </div>

                  {/* Score timeline */}
                  <div className="space-y-3 max-h-[400px] overflow-y-auto pr-1">
                    {agreementHistory.evaluations.map((ev) => (
                      <div key={ev.id} className="bg-stone-50 rounded-xl p-3">
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-sm font-medium text-stone-900">Turn {ev.turn_number}</span>
                          <div className="flex items-center gap-2">
                            <span className="text-sm text-stone-900 font-semibold">
                              {(ev.overall_agreement_score * 100).toFixed(0)}%
                            </span>
                            {ev.agreement_reached && (
                              <span className="text-xs bg-teal-50 text-teal-700 px-2 py-0.5 rounded-full flex items-center gap-1">
                                <CheckCircle className="w-3 h-3" /> Reached
                              </span>
                            )}
                          </div>
                        </div>
                        <div className="w-full bg-stone-50 rounded-full h-2 mb-2">
                          <div
                            className={`h-2 rounded-full transition-all ${
                              ev.agreement_reached ? 'bg-teal-400' :
                              ev.overall_agreement_score > 0.6 ? 'bg-green-400' :
                              ev.overall_agreement_score > 0.3 ? 'bg-yellow-400' :
                              'bg-red-400'
                            }`}
                            style={{ width: `${Math.min(ev.overall_agreement_score * 100, 100)}%` }}
                          />
                        </div>
                        {ev.persona_stances && Object.keys(ev.persona_stances).length > 0 && (
                          <div className="mt-2 space-y-1">
                            {Object.values(ev.persona_stances).map((stance) => (
                              <div key={stance.persona_name} className="flex items-center justify-between text-xs text-stone-500">
                                <span className="truncate max-w-[60%]">{stance.persona_name}</span>
                                <span className={`${
                                  stance.drift_score > 0.6 ? 'text-red-600' :
                                  stance.drift_score > 0.3 ? 'text-amber-600' :
                                  'text-green-600'
                                }`}>
                                  drift {(stance.drift_score * 100).toFixed(0)}%
                                </span>
                              </div>
                            ))}
                          </div>
                        )}
                        {ev.evaluation_reasoning && (
                          <p className="text-xs text-stone-400 mt-2 italic line-clamp-2">{ev.evaluation_reasoning}</p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Summary - per persona then key insights & action items as before */}
              {(currentSimulation.persona_summaries?.length || currentSimulation.summary) && (
                <div className="glass-card rounded-2xl p-6">
                  <h4 className="text-lg font-semibold text-stone-900 mb-4 flex items-center gap-2">
                    <FileText className="w-5 h-5" />
                    Simulation Summary
                  </h4>

                  <div className="mb-4">
                    {currentSimulation.persona_summaries?.length ? (
                      currentSimulation.persona_summaries.map((entry) => (
                        <p key={entry.persona_id} className="text-stone-700 leading-relaxed mb-3">
                          <span className="font-semibold text-stone-900">{entry.persona_name}: </span>
                          {entry.summary}
                        </p>
                      ))
                    ) : (
                      <p className="text-stone-700 leading-relaxed">{currentSimulation.summary}</p>
                    )}
                  </div>

                  {currentSimulation.key_insights && currentSimulation.key_insights.length > 0 && (
                    <div className="mb-4">
                      <h5 className="text-sm font-semibold text-stone-900 uppercase tracking-wide mb-2">Key Insights</h5>
                      <ul className="space-y-2">
                        {currentSimulation.key_insights.map((insight, idx) => (
                          <li key={idx} className="flex items-start gap-2 text-stone-600 text-sm">
                            <Sparkles className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
                            {insight}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {currentSimulation.action_items && currentSimulation.action_items.length > 0 && (
                    <div>
                      <h5 className="text-sm font-semibold text-stone-900 uppercase tracking-wide mb-2">Action Items</h5>
                      <ul className="space-y-2">
                        {currentSimulation.action_items.map((item, idx) => (
                          <li key={idx} className="flex items-start gap-2 text-stone-600 text-sm">
                            <CheckCircle className="w-4 h-4 text-green-600 flex-shrink-0 mt-0.5" />
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
              <MessageSquare className="w-16 h-16 mx-auto mb-4 text-stone-900/30" />
              <h3 className="text-xl font-semibold text-stone-900 mb-2">No Simulation Selected</h3>
              <p className="text-stone-400 mb-6">Select an existing simulation or create a new one</p>
              <button
                onClick={() => setShowSetup(true)}
                className="px-6 py-3 bg-stone-900 hover:bg-stone-800 text-white rounded-xl font-medium transition-all duration-200"
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
