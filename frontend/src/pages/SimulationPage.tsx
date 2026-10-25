import { useState, useEffect, useRef } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  MessageSquare,
  Users,
  FileText,
  ArrowLeft,
  Plus,
  CheckCircle,
  Loader2,
  Sparkles,
  TrendingUp,
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
import PlaygroundCanvas from '../components/simulation/PlaygroundCanvas';
import PlaygroundRoom from '../components/simulation/PlaygroundRoom';
import PlaygroundDetails from '../components/simulation/PlaygroundDetails';
import PlaygroundSessionBar from '../components/simulation/PlaygroundSessionBar';
import PlaygroundSetup from '../components/simulation/PlaygroundSetup';
import PathChat from '../components/simulation/PathChat';
import BranchCompare from '../components/simulation/BranchCompare';
import { lineageOf, pathIsClosed, type NodeSelection } from '../components/simulation/lineage';
import { getStudyScope, setStudyScope, studyPath, useStudyTracker } from '../hooks/useStudyTracker';
import { useAuth } from '../context/AuthContext';

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
  const [selectedId, setSelectedId] = useState<NodeSelection>('root');
  const [compareArmed, setCompareArmed] = useState(false);
  const [compareId, setCompareId] = useState<number | null>(null);
  const selectedRef = useRef<NodeSelection>('root');
  const activeHeadRef = useRef<number | null>(null);

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
      const head = data.active_head_message_id ?? null;
      activeHeadRef.current = head;
      selectedRef.current = head ?? 'root';
      setSelectedId(selectedRef.current);
      setCompareId(null);
      setCompareArmed(false);
      setShowSetup(false);
      try {
        const history = await simulationsApi.getAgreementHistory(id);
        setAgreementHistory(history);
      } catch {
        setAgreementHistory(null);
      }
      if (data.status === 'completed' || data.status === 'stopped' || data.path_complete) {
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
    streamingMessageRef.current = null;

    const streamUrl = `${API_BASE_URL}/simulations/${currentSimulation.id}/stream`;
    const simulationId = currentSimulation.id;

    // Use fetch with ReadableStream for better error handling and CORS support
    const abortController = new AbortController();
    const token = getAuthToken();
    // Accumulate in the reader closure — React state/ref can lag behind the last chunks
    let streamedContent = '';
    let streamPersonaMeta: {
      persona_id: number;
      persona_name: string;
      persona_image_url?: string | null;
      turn_number: number;
    } | null = null;

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
            if (!line.startsWith('data: ')) continue;
            try {
              const data = JSON.parse(line.slice(6));

              if (data.type === 'start') {
                streamedContent = '';
                const personaImageUrl =
                  currentSimulation.participants.find((p) => p.persona_id === data.persona_id)
                    ?.persona_image_url || undefined;
                streamPersonaMeta = {
                  persona_id: data.persona_id,
                  persona_name: data.persona_name,
                  persona_image_url: personaImageUrl,
                  turn_number: data.turn_number,
                };
                const nextMsg: SimulationMessage = {
                  id: -1,
                  persona_id: data.persona_id,
                  persona_name: data.persona_name,
                  persona_image_url: personaImageUrl,
                  content: '',
                  turn_number: data.turn_number,
                  tokens: 0,
                  is_moderator_message: false,
                  parent_message_id: data.parent_message_id ?? activeHeadRef.current,
                  created_at: new Date().toISOString(),
                };
                streamingMessageRef.current = nextMsg;
                setStreamingMessage(nextMsg);
                setCurrentSimulation((prev) => (prev ? { ...prev, status: 'running' } : prev));
                continue;
              }

              if (data.type === 'chunk') {
                streamedContent += data.content || '';
                setStreamingMessage((prev) => {
                  const next: SimulationMessage | null = prev
                    ? { ...prev, content: streamedContent }
                    : streamPersonaMeta
                      ? {
                          id: -1,
                          persona_id: streamPersonaMeta.persona_id,
                          persona_name: streamPersonaMeta.persona_name,
                          persona_image_url: streamPersonaMeta.persona_image_url || undefined,
                          content: streamedContent,
                          turn_number: streamPersonaMeta.turn_number,
                          tokens: 0,
                          is_moderator_message: false,
                          created_at: new Date().toISOString(),
                        }
                      : null;
                  streamingMessageRef.current = next;
                  return next;
                });
                continue;
              }

              if (data.type === 'complete' && data.reason === 'path_closed') {
                setCurrentSimulation((prev) =>
                  prev
                    ? {
                        ...prev,
                        path_complete: true,
                        status: data.simulation_status ?? prev.status,
                        current_turn: data.current_turn ?? prev.current_turn,
                      }
                    : prev,
                );
                streamingMessageRef.current = null;
                setStreamingMessage(null);
                setRunning(false);
                closeStream();
                return;
              }

              if (data.type === 'complete') {
                const fullContent =
                  (typeof data.content === 'string' && data.content.length > 0
                    ? data.content
                    : streamedContent) ||
                  streamingMessageRef.current?.content ||
                  '';

                const finalized: SimulationMessage = {
                  id: data.message_id ?? streamingMessageRef.current?.id ?? Date.now(),
                  persona_id:
                    streamingMessageRef.current?.persona_id ??
                    streamPersonaMeta?.persona_id,
                  persona_name:
                    streamingMessageRef.current?.persona_name ||
                    streamPersonaMeta?.persona_name ||
                    'Unknown',
                  persona_image_url:
                    streamingMessageRef.current?.persona_image_url ||
                    streamPersonaMeta?.persona_image_url ||
                    undefined,
                  content: fullContent,
                  turn_number:
                    streamingMessageRef.current?.turn_number ??
                    streamPersonaMeta?.turn_number ??
                    0,
                  tokens: data.tokens ?? 0,
                  is_moderator_message: false,
                  is_human_message: false,
                  parent_message_id: data.parent_message_id ?? activeHeadRef.current,
                  created_at:
                    streamingMessageRef.current?.created_at || new Date().toISOString(),
                };

                const evalResult: AgreementEvaluation | undefined = data.agreement_evaluation;

                setCurrentSimulation((prev) => {
                  if (!prev) return prev;
                  const withoutTemp = prev.messages.filter((m) => m.id !== -1);
                  const already = withoutTemp.some((m) => m.id === finalized.id);
                  return {
                    ...prev,
                    status: data.simulation_status ?? prev.status,
                    current_turn: data.current_turn ?? prev.current_turn,
                    tokens_used: data.tokens_used ?? prev.tokens_used,
                    active_head_message_id: finalized.id,
                    path_complete: !!data.path_complete,
                    messages: already ? withoutTemp : [...withoutTemp, finalized],
                    latest_agreement_score:
                      evalResult?.overall_agreement_score ?? prev.latest_agreement_score,
                    agreement_reached: evalResult?.agreement_reached ?? prev.agreement_reached,
                  };
                });

                if (evalResult) {
                  setAgreementHistory((prev) => {
                    if (!prev) return null;
                    return { ...prev, evaluations: [...prev.evaluations, evalResult] };
                  });
                }

                streamingMessageRef.current = null;
                setStreamingMessage(null);
                setRunning(false);
                closeStream();
                loadSimulations();
                const parentId = data.parent_message_id ?? activeHeadRef.current;
                const followed =
                  selectedRef.current === 'root' ? parentId == null : selectedRef.current === parentId;
                if (followed && typeof finalized.id === 'number') {
                  selectedRef.current = finalized.id;
                  setSelectedId(finalized.id);
                }
                activeHeadRef.current = finalized.id;

                track('simulation_turn_message', {
                  simulation_id: simulationId,
                  turn_number: finalized.turn_number,
                  persona_id: finalized.persona_id,
                  is_human: false,
                  content: finalized.content,
                  chars: (finalized.content || '').length,
                  streamed: true,
                });

                if (
                  shouldAutoContinue &&
                  autoContinueRef.current &&
                  data.simulation_status === 'running' &&
                  !data.path_complete
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

        // Stream ended without a complete event — keep accumulated text
        if (streamedContent && streamingMessageRef.current) {
          const fallback = { ...streamingMessageRef.current, content: streamedContent };
          setCurrentSimulation((prev) => {
            if (!prev) return prev;
            return {
              ...prev,
              messages: [...prev.messages.filter((m) => m.id !== -1), fallback],
            };
          });
        }
        setStreamingMessage(null);
        setRunning(false);
      })
      .catch((error) => {
        if (error.name === 'AbortError') {
          // Stream was intentionally closed
          return;
        }
        console.error('Streaming fetch error:', error);
        alert(`Failed to stream simulation: ${error.message}`);
        setRunning(false);
        setStreamingMessage(null);
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

  const followHead = (simulation: { active_head_message_id?: number | null }) => {
    const head = simulation.active_head_message_id ?? null;
    activeHeadRef.current = head;
    if (head != null) {
      selectedRef.current = head;
      setSelectedId(head);
    }
  };

  const alignHead = async (target: number | null) => {
    if (!currentSimulation) return;
    activeHeadRef.current = target;
    if ((currentSimulation.active_head_message_id ?? null) === target) return;
    const updated = await simulationsApi.focus(currentSimulation.id, target);
    activeHeadRef.current = updated.active_head_message_id ?? null;
    setCurrentSimulation(updated);
  };

  const handleCanvasSelect = (id: NodeSelection) => {
    if (compareArmed && typeof id === 'number') {
      setCompareId(id);
      setCompareArmed(false);
      return;
    }
    selectedRef.current = id;
    setSelectedId(id);
  };

  const handleStartSimulation = async (autoContinue: boolean = true) => {
    if (!currentSimulation) return;
    const target = selectedRef.current === 'root' ? null : selectedRef.current;
    try {
      await alignHead(target);
    } catch (error: any) {
      alert(`Failed to focus this node: ${error.response?.data?.detail || error.message}`);
      return;
    }

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
      followHead(updated);
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
    const target = selectedRef.current === 'root' ? null : selectedRef.current;
    try {
      await alignHead(target);
      await simulationsApi.intervene(simId, text);
      track('simulation_intervention', {
        simulation_id: simId,
        message: text,
        chars: text.length,
      });
      setInterventionText('');
      let updated = await simulationsApi.getById(simId);
      setCurrentSimulation(updated);
      followHead(updated);

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
          followHead(updated);
          await loadSimulations();
          const last = updated.messages?.find((message: SimulationMessage) => message.id === updated.active_head_message_id)
            ?? updated.messages?.[updated.messages.length - 1];
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
    if (!currentSimulation || running) return;
    const target = selectedRef.current === 'root' ? null : selectedRef.current;
    try {
      await alignHead(target);
    } catch (error: any) {
      alert(`Failed to focus this node: ${error.response?.data?.detail || error.message}`);
      return;
    }

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
      followHead(updated);
      const last = updated.messages?.find((message: SimulationMessage) => message.id === updated.active_head_message_id)
        ?? updated.messages?.[updated.messages.length - 1];
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
    const target = selectedRef.current === 'root' ? null : selectedRef.current;
    try {
      await alignHead(target);
    } catch (error: any) {
      alert(`Failed to focus this node: ${error.response?.data?.detail || error.message}`);
      return;
    }

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
    const target = selectedRef.current === 'root' ? null : selectedRef.current;
    try {
      await alignHead(target);
    } catch (error: any) {
      alert(`Failed to focus this node: ${error.response?.data?.detail || error.message}`);
      return;
    }
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
    const target = selectedRef.current === 'root' ? null : selectedRef.current;
    try {
      await alignHead(target);
    } catch (error: any) {
      alert(`Failed to focus this node: ${error.response?.data?.detail || error.message}`);
      return;
    }
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

  const playgroundMessages = (() => {
    const base = currentSimulation?.messages ? [...currentSimulation.messages] : [];
    if (streamingMessage) base.push(streamingMessage);
    return base;
  })();
  const selectedHead = selectedId === 'root' ? null : selectedId;
  const pathAnchor = typeof selectedHead === 'number' && selectedHead > 0
    ? selectedHead
    : selectedId === -1
      ? (streamingMessage?.parent_message_id ?? null)
      : null;
  const pathMessages = lineageOf(playgroundMessages, pathAnchor);
  const streamingOnPath = !!streamingMessage && (
    selectedId === 'root'
      ? streamingMessage.parent_message_id == null
      : streamingMessage.parent_message_id === selectedId
  );
  const chatMessages = streamingOnPath && streamingMessage ? [...pathMessages, streamingMessage] : pathMessages;
  const selectedMessage = typeof selectedId === 'number'
    ? playgroundMessages.find((message) => message.id === selectedId) ?? null
    : null;
  const floorMessage = streamingOnPath && streamingMessage ? streamingMessage : selectedMessage;
  const selectedClosed = !!currentSimulation && (
    pathIsClosed({
      messages: playgroundMessages.filter((message) => message.id > 0),
      headId: selectedHead,
      numParticipants: currentSimulation.participants.length,
      maxTurns: currentSimulation.max_turns,
      maxTokens: currentSimulation.max_tokens,
      runUntilAgreement: currentSimulation.run_until_agreement,
      evaluations: agreementHistory?.evaluations,
    }) ||
    (!!currentSimulation.path_complete &&
      selectedHead != null &&
      selectedHead === currentSimulation.active_head_message_id)
  );
  const canScore = !!currentSimulation && (
    currentSimulation.status === 'completed' ||
    currentSimulation.status === 'stopped' ||
    !!currentSimulation.path_complete ||
    selectedClosed
  );

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
                ? `Signed in as ${user?.participant_code || user?.name || 'participant'} — set the room, then fork the discussion`
                : 'A hall with seats, one speaker on the floor, and threads that fork to the right'}
            </p>
          </div>
        </div>
        {currentSimulation && (
          <button
            onClick={handleNewSimulation}
            className="px-4 py-2 bg-stone-900 hover:bg-stone-800 text-white rounded-xl font-medium transition-all duration-200 flex items-center gap-2"
          >
            <Plus className="w-4 h-4" />
            New hall
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
            <PlaygroundSetup
              name={name}
              goal={goal}
              goalContext={goalContext}
              maxTurns={maxTurns}
              runUntilAgreement={runUntilAgreement}
              agreementThreshold={agreementThreshold}
              personaSets={personaSets}
              expandedSetIds={expandedSetIds}
              selectedPersonas={selectedPersonas}
              loading={loading}
              useStudyDefaults={useStudyDefaults}
              participantCode={user?.participant_code}
              studyOrderNote={isStudyMode}
              onName={setName}
              onGoal={setGoal}
              onGoalContext={setGoalContext}
              onMaxTurns={setMaxTurns}
              onRunUntilAgreement={setRunUntilAgreement}
              onAgreementThreshold={setAgreementThreshold}
              onToggleSet={(setId) => {
                setExpandedSetIds((prev) => {
                  const next = new Set(prev);
                  if (next.has(setId)) next.delete(setId);
                  else next.add(setId);
                  return next;
                });
              }}
              onTogglePersona={handlePersonaToggle}
              onRoleChange={handleRoleChange}
              onCreate={handleCreateSimulation}
            />
          ) : currentSimulation ? (
            <div className="space-y-4">
              <PlaygroundSessionBar
                simulation={currentSimulation}
                roundsOnPath={
                  currentSimulation.participants.length > 0
                    ? Math.floor(
                        pathMessages.filter((message) => message.persona_id != null && !message.is_human_message).length /
                          currentSimulation.participants.length,
                      )
                    : 0
                }
                isStudyMode={isStudyMode}
                running={running}
                streamingEnabled={streamingEnabled}
                autoContinue={autoContinue}
                evaluatingAgreement={evaluatingAgreement}
                evaluatingDiscussion={evaluatingDiscussion}
                generatingSummary={generatingSummary}
                showAgreementHistory={showAgreementHistory}
                showEvaluationScores={showEvaluationScores}
                hasAgreementHistory={!!agreementHistory && agreementHistory.evaluations.length > 0}
                hasEvaluation={!!evaluationScores?.has_evaluation}
                canScore={canScore}
                onStart={handleStartSimulation}
                onStop={handleStopSimulation}
                onStreaming={setStreamingEnabled}
                onAutoContinue={setAutoContinue}
                onOpenChats={() =>
                  navigate(
                    studySlug
                      ? studyPath(studySlug, `/simulations/${currentSimulation.id}/persona-chats`)
                      : `/simulations/${currentSimulation.id}/persona-chats`,
                  )
                }
                onEvaluateAgreement={handleEvaluateAgreement}
                onToggleAgreementHistory={() => setShowAgreementHistory((value) => !value)}
                onEvaluateDiscussion={handleEvaluateDiscussion}
                onGenerateSummary={handleGenerateSummary}
                onToggleEvaluation={() => setShowEvaluationScores((value) => !value)}
                onDownload={handleDownloadSimulation}
              />

              <PlaygroundRoom
                goal={currentSimulation.goal}
                running={running}
                facilitatorSpeaking={
                  !!floorMessage && (floorMessage.is_human_message || floorMessage.persona_id == null)
                }
                floorName={
                  floorMessage
                    ? (floorMessage.is_human_message || floorMessage.persona_id == null
                      ? 'Facilitator'
                      : floorMessage.persona_name)
                    : undefined
                }
                floorText={floorMessage?.content}
                seats={currentSimulation.participants.map((participant) => ({
                  id: participant.persona_id,
                  name: participant.persona_name,
                  imageUrl: participant.persona_image_url,
                  role: participant.role,
                  speaking: !!floorMessage
                    && !floorMessage.is_human_message
                    && floorMessage.persona_id === participant.persona_id,
                }))}
                onSeat={(personaId) => {
                  const latest = [...pathMessages].reverse().find((message) => message.persona_id === personaId);
                  if (latest) handleCanvasSelect(latest.id);
                }}
              />

              <div className="grid grid-cols-1 items-start gap-4 xl:grid-cols-[minmax(0,1fr)_320px]">
                <div className="flex min-w-0 flex-col gap-4">
                  <PlaygroundCanvas
                    goal={currentSimulation.goal}
                    messages={playgroundMessages}
                    selectedId={selectedId}
                    onSelect={handleCanvasSelect}
                    mapHeight={280}
                  />
                  {running && (
                    <div className="flex items-center text-sm text-stone-500">
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Generating response...
                    </div>
                  )}
                </div>
                <PlaygroundDetails
                  goal={currentSimulation.goal}
                  goalContext={currentSimulation.goal_context}
                  selected={selectedId}
                  selectedMessage={selectedMessage}
                  crumbs={pathMessages}
                  pathClosed={selectedClosed || currentSimulation.status === 'stopped' || currentSimulation.status === 'completed'}
                  running={running}
                  intervening={intervening}
                  interventionText={interventionText}
                  onInterventionText={setInterventionText}
                  onIntervene={handleIntervene}
                  onNextTurn={handleNextTurn}
                  compareArmed={compareArmed}
                  onArmCompare={() => {
                    if (typeof selectedId === 'number') setCompareArmed(true);
                  }}
                />
              </div>
              <PathChat
                messages={chatMessages}
                participants={currentSimulation.participants}
                selectedId={selectedId}
                onSelect={handleCanvasSelect}
              />
              {compareId != null && typeof selectedId === 'number' && compareId !== selectedId && (
                <BranchCompare
                  messages={playgroundMessages.filter((message) => message.id > 0)}
                  leftId={selectedId}
                  rightId={compareId}
                  evaluations={agreementHistory?.evaluations ?? []}
                  onClose={() => setCompareId(null)}
                />
              )}

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
