import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, Loader2, MessageSquare, Users } from 'lucide-react';
import { personasApi, simulationsApi } from '../services/api';
import { Persona, Simulation, SimulationMessage } from '../types';
import { getPersonaImageUrl } from '../utils/imageUtils';
import { studyPath } from '../hooks/useStudyTracker';

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

const isHumanMessage = (m: SimulationMessage) =>
  m.is_human_message ?? (m.persona_id == null);

export default function SimulationPersonaChatsPage() {
  const navigate = useNavigate();
  const { slug: studySlug, simulationId, personaId } = useParams<{
    slug?: string;
    simulationId: string;
    personaId?: string;
    personaSlug?: string;
  }>();

  const simBase = studySlug
    ? studyPath(studySlug, `/simulations/${simulationId}`)
    : `/simulations/${simulationId}`;

  const [simulation, setSimulation] = useState<Simulation | null>(null);
  const [loadingSimulation, setLoadingSimulation] = useState(false);

  const [selectedPersonaId, setSelectedPersonaId] = useState<number | null>(null);
  const [selectedPersona, setSelectedPersona] = useState<Persona | null>(null);
  const [loadingPersona, setLoadingPersona] = useState(false);

  const slugify = (s: string) =>
    (s || 'persona')
      .toLowerCase()
      .trim()
      .replace(/['"]/g, '')
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/(^-|-$)+/g, '') || 'persona';

  useEffect(() => {
    const run = async () => {
      if (!simulationId) return;
      setLoadingSimulation(true);
      try {
        const data = await simulationsApi.getById(parseInt(simulationId));
        setSimulation(data);
        const fromUrl = personaId ? parseInt(personaId) : null;
        const first = data.participants?.[0]?.persona_id;
        const initial = (fromUrl && !Number.isNaN(fromUrl)) ? fromUrl : (first ?? null);
        if (initial) setSelectedPersonaId(initial);
      } catch (e) {
        console.error('Failed to load simulation:', e);
        setSimulation(null);
      } finally {
        setLoadingSimulation(false);
      }
    };
    run();
  }, [simulationId, personaId]);

  useEffect(() => {
    const run = async () => {
      if (!selectedPersonaId) {
        setSelectedPersona(null);
        return;
      }
      setLoadingPersona(true);
      try {
        const p = await personasApi.getPersona(selectedPersonaId);
        setSelectedPersona(p);

        // Keep URL in sync with selected persona (include name slug).
        if (simulationId) {
          const slug = slugify(p.persona_data?.name || p.name || 'persona');
          navigate(
            `${simBase}/persona-chats/${selectedPersonaId}/${encodeURIComponent(slug)}`,
            { replace: true }
          );
        }
      } catch (e) {
        console.error('Failed to load persona:', e);
        setSelectedPersona(null);
      } finally {
        setLoadingPersona(false);
      }
    };
    run();
  }, [selectedPersonaId, simulationId]);

  const selectedParticipant = useMemo(() => {
    if (!simulation || !selectedPersonaId) return null;
    return simulation.participants.find(p => p.persona_id === selectedPersonaId) ?? null;
  }, [simulation, selectedPersonaId]);

  const personaMessages = useMemo(() => {
    if (!simulation || !selectedPersonaId) return [];
    return simulation.messages
      .filter(m => !isHumanMessage(m) && m.persona_id === selectedPersonaId)
      .slice()
      .sort(
        (a, b) =>
          (a.turn_number - b.turn_number) ||
          (new Date(a.created_at).getTime() - new Date(b.created_at).getTime())
      );
  }, [simulation, selectedPersonaId]);

  const renderValue = (v: any): string => {
    if (v === null || v === undefined) return '';
    if (typeof v === 'string') return v;
    if (typeof v === 'number' || typeof v === 'boolean') return String(v);
    if (Array.isArray(v)) return v.map(renderValue).filter(Boolean).join(', ');
    if (typeof v === 'object') {
      if ('text' in v || 'description' in v || 'content' in v) {
        return String((v as any).text || (v as any).description || (v as any).content || '');
      }
      try {
        return JSON.stringify(v);
      } catch {
        return String(v);
      }
    }
    return String(v);
  };

  if (loadingSimulation) {
    return (
      <div className="glass-card rounded-2xl p-8 flex items-center gap-3 text-stone-600">
        <Loader2 className="w-5 h-5 animate-spin" />
        Loading simulation…
      </div>
    );
  }

  if (!simulation) {
    return (
      <div className="glass-card rounded-2xl p-10 text-center text-stone-600">
        Simulation not found.
      </div>
    );
  }

  return (
    <div className="px-4 py-6 sm:px-0">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4 min-w-0">
          <button
            onClick={() => navigate(studySlug ? studyPath(studySlug, `/simulations/${simulation.id}`) : `/simulations/${simulation.id}`)}
            className="p-2 rounded-lg bg-stone-50 hover:bg-stone-100 transition-colors"
            title="Back to simulation"
          >
            <ArrowLeft className="w-5 h-5 text-stone-900" />
          </button>
          <div className="min-w-0">
            <h2 className="text-2xl sm:text-3xl font-bold text-stone-900 mb-1 truncate">
              Personas + Chats
            </h2>
            <p className="text-stone-600 text-sm sm:text-lg truncate">
              {simulation.name} • {simulation.goal}
            </p>
          </div>
        </div>
      </div>

      {/* Persona pills */}
      <div className="glass-card rounded-2xl p-4 mb-6">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-sm text-stone-500 mr-1 flex items-center gap-1">
            <Users className="w-4 h-4" /> Personas:
          </span>
          {simulation.participants.map(p => (
            <button
              key={p.id}
              type="button"
              onClick={() => setSelectedPersonaId(p.persona_id)}
              className={`flex items-center gap-2 rounded-full px-3 py-1.5 border transition-colors ${
                selectedPersonaId === p.persona_id
                  ? 'bg-stone-900 text-white border-stone-900'
                  : 'bg-stone-50 text-stone-900 border-stone-200 hover:bg-stone-100'
              }`}
              title="Select persona"
            >
              <PersonaAvatar
                name={p.persona_name}
                imageUrl={p.persona_image_url}
                personaId={p.persona_id}
                size="sm"
                showBorder={false}
              />
              <span className="text-sm font-medium">{p.persona_name}</span>
              {p.role && (
                <span className={`text-xs ${selectedPersonaId === p.persona_id ? 'text-white/70' : 'text-stone-400'}`}>
                  ({p.role})
                </span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* 55/45 layout */}
      <div className="flex flex-col lg:flex-row gap-6">
        {/* Left: Persona profile */}
        <div className="glass-card rounded-2xl p-5 lg:w-[55%] w-full">
          {loadingPersona ? (
            <div className="flex items-center gap-2 text-stone-600">
              <Loader2 className="w-4 h-4 animate-spin" />
              Loading persona…
            </div>
          ) : !selectedPersona ? (
            <div className="text-stone-600">Select a persona to view their profile.</div>
          ) : (
            (() => {
              const personaData = selectedPersona.persona_data || ({} as any);
              const demographics = personaData.demographics || {};
              const background =
                personaData.background ||
                personaData.detailed_description ||
                personaData.personal_background ||
                personaData.background_and_personal_history ||
                personaData.other_information ||
                '';
              const goals = Array.isArray(personaData.goals) ? personaData.goals : [];
              const frustrations = Array.isArray(personaData.frustrations) ? personaData.frustrations : [];

              return (
                <div>
                  <div className="flex items-start gap-4 mb-5">
                    <PersonaAvatar
                      name={selectedPersona.name}
                      imageUrl={selectedPersona.image_url}
                      personaId={selectedPersona.id}
                      size="lg"
                    />
                    <div className="min-w-0 flex-1">
                      <h3 className="text-2xl font-bold text-stone-900">
                        {personaData.name || selectedPersona.name}
                      </h3>
                      <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-sm text-stone-500">
                        {(demographics.occupation || personaData.occupation) && (
                          <span>{renderValue(demographics.occupation || personaData.occupation)}</span>
                        )}
                        {(demographics.location || personaData.location) && (
                          <span>• {renderValue(demographics.location || personaData.location)}</span>
                        )}
                        {(demographics.age || personaData.age) && (
                          <span>• {renderValue(demographics.age || personaData.age)} yrs</span>
                        )}
                        {(demographics.gender || personaData.gender) && (
                          <span>• {renderValue(demographics.gender || personaData.gender)}</span>
                        )}
                      </div>
                      {selectedParticipant?.persona_set_name && (
                        <div className="mt-2 text-xs text-stone-400">
                          From: <span className="italic">{selectedParticipant.persona_set_name}</span>
                        </div>
                      )}
                      {personaData.quote && (
                        <div className="mt-3 p-3 bg-stone-50 border border-stone-200 rounded-xl text-stone-700 italic">
                          “{renderValue(personaData.quote)}”
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="space-y-5">
                    <div>
                      <h4 className="text-sm font-semibold text-stone-900 uppercase tracking-wide mb-2">Background</h4>
                      <p className="text-sm text-stone-700 leading-relaxed whitespace-pre-wrap">
                        {renderValue(background) || 'No background information available.'}
                      </p>
                    </div>
                    <div>
                      <h4 className="text-sm font-semibold text-stone-900 uppercase tracking-wide mb-2">Goals</h4>
                      {goals.length ? (
                        <ul className="list-disc list-inside space-y-1 text-sm text-stone-700">
                          {goals.map((g: any, idx: number) => (
                            <li key={idx}>{renderValue(g)}</li>
                          ))}
                        </ul>
                      ) : (
                        <p className="text-sm text-stone-400">No goals listed.</p>
                      )}
                    </div>
                    <div>
                      <h4 className="text-sm font-semibold text-stone-900 uppercase tracking-wide mb-2">Frustrations</h4>
                      {frustrations.length ? (
                        <ul className="list-disc list-inside space-y-1 text-sm text-stone-700">
                          {frustrations.map((f: any, idx: number) => (
                            <li key={idx}>{renderValue(f)}</li>
                          ))}
                        </ul>
                      ) : (
                        <p className="text-sm text-stone-400">No frustrations listed.</p>
                      )}
                    </div>
                  </div>
                </div>
              );
            })()
          )}
        </div>

        {/* Right: Messages from persona */}
        <div className="glass-card rounded-2xl overflow-hidden flex flex-col min-h-[520px] max-h-[75vh] lg:w-[45%] w-full">
          <div className="px-5 py-4 border-b border-stone-200 flex items-center justify-between">
            <div className="flex items-center gap-2 text-stone-900 font-semibold">
              <MessageSquare className="w-4 h-4" />
              Messages
            </div>
            <div className="text-xs text-stone-400">{personaMessages.length} total</div>
          </div>

          <div className="flex-1 min-h-0 overflow-y-auto p-4 space-y-3">
            {!selectedPersonaId ? (
              <div className="text-stone-600 text-sm">Select a persona.</div>
            ) : personaMessages.length === 0 ? (
              <div className="text-stone-600 text-sm">No messages from this persona yet.</div>
            ) : (
              (() => {
                let lastTurn: number | null = null;
                return personaMessages.map(m => {
                  const showTurn = lastTurn !== m.turn_number;
                  lastTurn = m.turn_number;
                  return (
                    <div key={m.id}>
                      {showTurn && (
                        <div className="sticky top-0 z-10 -mx-4 px-4 py-2 bg-white/95 backdrop-blur border-y border-stone-100">
                          <span className="text-xs font-semibold text-stone-500">Turn {m.turn_number}</span>
                        </div>
                      )}
                      <div className="mt-2 rounded-2xl bg-stone-50 border border-stone-200 px-4 py-3">
                        <div className="flex items-center justify-between gap-2 mb-1">
                          <span className="text-xs font-semibold text-stone-700 whitespace-nowrap">
                            Turn {m.turn_number}
                          </span>
                          {m.persona_drift_score !== undefined && (
                            <span
                              className={`text-[11px] px-1.5 py-0.5 rounded-full ${
                                m.persona_drift_score > 0.6 ? 'bg-red-50 text-red-600' :
                                m.persona_drift_score > 0.3 ? 'bg-amber-50 text-amber-600' :
                                'bg-green-50 text-green-600'
                              }`}
                              title={`Persona drift: ${(m.persona_drift_score * 100).toFixed(0)}%`}
                            >
                              drift {(m.persona_drift_score * 100).toFixed(0)}%
                            </span>
                          )}
                        </div>
                        <p className="text-sm text-stone-800 leading-relaxed whitespace-pre-wrap">
                          {m.content}
                        </p>
                      </div>
                    </div>
                  );
                });
              })()
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

