import { useState, useEffect, useRef, useMemo } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import {
  Bot,
  Send,
  Loader2,
  Shield,
  AlertCircle,
  RefreshCw,
  FolderOpen,
  Download,
  Users,
  User,
} from 'lucide-react';
import { personaChatApi, personasApi, projectsApi } from '../services/api';
import {
  Persona,
  PersonaSet,
  PersonaChatMessage,
  PersonaChatSession,
  Project,
} from '../types';
import { getPersonaImageUrl } from '../utils/imageUtils';
import PersonaProfileCard from '../components/PersonaProfileCard';

const PROJECT_STORAGE_KEY = 'persona-chat-project-id';
const MODE_STORAGE_KEY = 'persona-chat-mode';

type ChatMode = 'single' | 'set';

const sanitizeFilename = (name: string) =>
  name.replace(/[^a-z0-9]/gi, '_').toLowerCase() || 'persona';

const downloadFile = (content: string, filename: string, mimeType: string) => {
  const blob = new Blob([content], { type: mimeType });
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  window.URL.revokeObjectURL(url);
  document.body.removeChild(a);
};

function PersonaAvatar({
  name,
  imageUrl,
  personaId,
  size = 'md',
}: {
  name: string;
  imageUrl?: string | null;
  personaId?: number | null;
  size?: 'sm' | 'md';
}) {
  const [imageError, setImageError] = useState(false);
  const sizeClasses = { sm: 'w-8 h-8 text-sm', md: 'w-10 h-10 text-base' };
  const src = personaId != null ? getPersonaImageUrl(imageUrl, personaId) : null;

  if (src && !imageError) {
    return (
      <img
        src={src}
        alt={name}
        className={`${sizeClasses[size]} object-cover rounded-full border-2 border-stone-200`}
        onError={() => setImageError(true)}
      />
    );
  }

  return (
    <div className={`${sizeClasses[size]} rounded-full border-2 border-stone-200 bg-stone-200 flex items-center justify-center`}>
      <span className="text-stone-600 font-semibold">{name.charAt(0).toUpperCase()}</span>
    </div>
  );
}

function ChatBubble({
  message,
  fallbackPersonaName,
  fallbackPersonaImageUrl,
  fallbackPersonaId,
}: {
  message: PersonaChatMessage;
  fallbackPersonaName?: string;
  fallbackPersonaImageUrl?: string | null;
  fallbackPersonaId?: number | null;
}) {
  const isUser = message.role === 'user';

  if (isUser) {
    return (
      <div className="flex justify-end mb-4">
        <div className="bg-stone-900 text-white rounded-2xl px-4 py-3 max-w-[75%]">
          <p className="text-sm leading-relaxed whitespace-pre-wrap">{message.content}</p>
        </div>
      </div>
    );
  }

  const refused = message.refused;
  const name = message.persona_name || fallbackPersonaName || 'Persona';
  const imageUrl = message.persona_image_url ?? fallbackPersonaImageUrl;
  const personaId = message.persona_id ?? fallbackPersonaId;

  return (
    <div className="flex justify-start mb-4">
      <div className="flex items-start gap-3 max-w-[85%]">
        <PersonaAvatar name={name} imageUrl={imageUrl} personaId={personaId} size="sm" />
        <div
          className={`rounded-2xl px-4 py-3 ${
            refused ? 'bg-amber-50 border border-amber-200' : 'bg-white border border-stone-200'
          }`}
        >
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <span className="text-sm font-semibold text-stone-900">{name}</span>
            {refused && (
              <span className="text-xs px-1.5 py-0.5 rounded-full bg-amber-100 text-amber-700">
                {message.refusal_reason === 'jailbreak_attempt'
                  ? 'Blocked'
                  : message.refusal_reason === 'boundary_violation'
                    ? 'Boundary enforced'
                    : 'Out of scope'}
              </span>
            )}
            {message.retrieval_score != null &&
              !refused &&
              message.sources_used &&
              message.sources_used.length > 0 && (
                <span className="text-xs text-stone-400">
                  relevance {(message.retrieval_score * 100).toFixed(0)}%
                </span>
              )}
            {!refused && (!message.sources_used || message.sources_used.length === 0) && (
              <span className="text-xs text-stone-400">from profile</span>
            )}
          </div>
          <p className={`text-sm leading-relaxed whitespace-pre-wrap ${refused ? 'text-amber-800 italic' : 'text-stone-800'}`}>
            {message.content}
          </p>
          {message.sources_used && message.sources_used.length > 0 && (
            <p className="text-xs text-stone-400 mt-2">
              Grounded in {message.sources_used.length} evidence chunk
              {message.sources_used.length !== 1 ? 's' : ''}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

export default function PersonaChatPage() {
  const { personaId: personaIdParam } = useParams<{ personaId?: string }>();
  const [searchParams] = useSearchParams();
  const projectFromUrl = searchParams.get('project');

  const [chatMode, setChatMode] = useState<ChatMode>(() => {
    const stored = localStorage.getItem(MODE_STORAGE_KEY);
    return stored === 'set' ? 'set' : 'single';
  });

  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<number | null>(null);
  const [personaSets, setPersonaSets] = useState<PersonaSet[]>([]);
  const [loadingPersonas, setLoadingPersonas] = useState(false);

  const [selectedPersonaId, setSelectedPersonaId] = useState<number | null>(
    personaIdParam ? parseInt(personaIdParam, 10) : null
  );
  const [selectedSetId, setSelectedSetId] = useState<number | null>(null);

  const [session, setSession] = useState<PersonaChatSession | null>(null);
  const [messages, setMessages] = useState<PersonaChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [initializing, setInitializing] = useState(false);
  const [strictMode, setStrictMode] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // @ mention autocomplete
  const [mentionOpen, setMentionOpen] = useState(false);
  const [mentionQuery, setMentionQuery] = useState('');
  const [mentionIndex, setMentionIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    projectsApi
      .getAll()
      .then((data) => {
        setProjects(data);
        const urlProject = projectFromUrl ? parseInt(projectFromUrl, 10) : null;
        const stored = localStorage.getItem(PROJECT_STORAGE_KEY);
        const storedProject = stored ? parseInt(stored, 10) : null;
        const initial =
          (urlProject && data.some((p: Project) => p.id === urlProject) ? urlProject : null) ||
          (storedProject && data.some((p: Project) => p.id === storedProject) ? storedProject : null) ||
          (data.length > 0 ? data[0].id : null);
        setSelectedProjectId(initial);
      })
      .catch(() => setError('Failed to load projects'));
  }, [projectFromUrl]);

  useEffect(() => {
    if (!selectedProjectId) {
      setPersonaSets([]);
      return;
    }
    localStorage.setItem(PROJECT_STORAGE_KEY, String(selectedProjectId));
    setLoadingPersonas(true);
    personasApi
      .getAllSets(selectedProjectId)
      .then((sets) => {
        setPersonaSets(sets);
        const allIds = sets.flatMap((s: PersonaSet) => s.personas.map((p) => p.id));
        const setIds = sets.map((s: PersonaSet) => s.id);
        if (selectedPersonaId && !allIds.includes(selectedPersonaId)) {
          setSelectedPersonaId(null);
        }
        if (selectedSetId && !setIds.includes(selectedSetId)) {
          setSelectedSetId(null);
        }
        if (!selectedSetId && sets.length > 0 && chatMode === 'set') {
          setSelectedSetId(sets[0].id);
        }
      })
      .catch(() => setError('Failed to load personas for this project'))
      .finally(() => setLoadingPersonas(false));
  }, [selectedProjectId]);

  useEffect(() => {
    localStorage.setItem(MODE_STORAGE_KEY, chatMode);
    setSession(null);
    setMessages([]);
    setError(null);
    if (chatMode === 'set' && !selectedSetId && personaSets.length > 0) {
      setSelectedSetId(personaSets[0].id);
    }
  }, [chatMode]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const projectPersonas = useMemo(
    () => personaSets.flatMap((s) => s.personas.map((p) => ({ ...p, setName: s.name, setId: s.id }))),
    [personaSets]
  );

  const selectedPersona = projectPersonas.find((p) => p.id === selectedPersonaId);
  const selectedSet = personaSets.find((s) => s.id === selectedSetId);

  const setParticipants: Persona[] = selectedSet?.personas || [];

  const mentionCandidates = useMemo(() => {
    if (!mentionOpen || chatMode !== 'set') return [];
    const q = mentionQuery.toLowerCase();
    return setParticipants.filter((p) => {
      const name = ((p.persona_data as any)?.name || p.name || '').toLowerCase();
      return !q || name.includes(q);
    });
  }, [mentionOpen, mentionQuery, setParticipants, chatMode]);

  const startSingleSession = async (personaId: number, projectId: number) => {
    setInitializing(true);
    setError(null);
    setMessages([]);
    setSession(null);
    try {
      const newSession = await personaChatApi.createSession(personaId, projectId);
      setSession(newSession);
      setMessages(newSession.messages || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to start chat');
    } finally {
      setInitializing(false);
    }
  };

  const startSetSession = async (setId: number, projectId: number) => {
    setInitializing(true);
    setError(null);
    setMessages([]);
    setSession(null);
    try {
      const newSession = await personaChatApi.createSetSession(setId, projectId);
      setSession(newSession);
      setMessages(newSession.messages || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to start set chat');
    } finally {
      setInitializing(false);
    }
  };

  useEffect(() => {
    if (chatMode === 'single' && selectedPersonaId && selectedProjectId) {
      startSingleSession(selectedPersonaId, selectedProjectId);
    }
  }, [selectedPersonaId, selectedProjectId, chatMode]);

  useEffect(() => {
    if (chatMode === 'set' && selectedSetId && selectedProjectId) {
      startSetSession(selectedSetId, selectedProjectId);
    }
  }, [selectedSetId, selectedProjectId, chatMode]);

  const insertMention = (persona: Persona) => {
    const name = (persona.persona_data as any)?.name || persona.name;
    const el = inputRef.current;
    const cursor = el?.selectionStart ?? input.length;
    const before = input.slice(0, cursor);
    const after = input.slice(cursor);
    const atIdx = before.lastIndexOf('@');
    if (atIdx < 0) {
      setInput(`${input}@${name} `);
    } else {
      setInput(`${before.slice(0, atIdx)}@${name} ${after}`);
    }
    setMentionOpen(false);
    setMentionQuery('');
    setMentionIndex(0);
    requestAnimationFrame(() => inputRef.current?.focus());
  };

  const handleInputChange = (value: string) => {
    setInput(value);
    if (chatMode !== 'set') {
      setMentionOpen(false);
      return;
    }
    const el = inputRef.current;
    const cursor = el?.selectionStart ?? value.length;
    const before = value.slice(0, cursor);
    const match = before.match(/@([^@\s]*)$/);
    if (match) {
      setMentionOpen(true);
      setMentionQuery(match[1] || '');
      setMentionIndex(0);
    } else {
      setMentionOpen(false);
      setMentionQuery('');
    }
  };

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || !session || loading) return;

    const userText = input.trim();
    setInput('');
    setMentionOpen(false);
    setLoading(true);
    setError(null);

    const optimisticUser: PersonaChatMessage = {
      id: Date.now(),
      role: 'user',
      content: userText,
      refused: false,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, optimisticUser]);

    try {
      const reply = await personaChatApi.sendMessage(session.id, userText, strictMode);
      const assistantMsgs: PersonaChatMessage[] = (reply.replies?.length
        ? reply.replies
        : [
            {
              reply: reply.reply || "I don't know.",
              refused: reply.refused,
              persona_id: session.persona_id,
              persona_name: session.persona_name,
              persona_image_url: session.persona_image_url,
              retrieval_score: reply.retrieval_score,
              sources_used: reply.sources_used,
              refusal_reason: reply.refusal_reason,
              message_id: reply.message_id || Date.now() + 1,
            },
          ]
      ).map((r: any) => ({
        id: r.message_id,
        role: 'assistant' as const,
        content: r.reply,
        persona_id: r.persona_id,
        persona_name: r.persona_name,
        persona_image_url: r.persona_image_url,
        refused: r.refused,
        retrieval_score: r.retrieval_score,
        sources_used: r.sources_used,
        refusal_reason: r.refusal_reason,
        created_at: new Date().toISOString(),
      }));
      setMessages((prev) => [...prev, ...assistantMsgs]);
    } catch (err: any) {
      const detail = err.response?.data?.detail || err.message || 'Failed to send message';
      const timedOut = err.code === 'ECONNABORTED';
      setError(timedOut ? 'Request timed out — try again or address fewer personas with @.' : detail);
      setMessages((prev) => prev.filter((m) => m.id !== optimisticUser.id));
      setInput(userText);
    } finally {
      setLoading(false);
    }
  };

  const handleNewChat = () => {
    if (chatMode === 'single' && selectedPersonaId && selectedProjectId) {
      startSingleSession(selectedPersonaId, selectedProjectId);
    } else if (chatMode === 'set' && selectedSetId && selectedProjectId) {
      startSetSession(selectedSetId, selectedProjectId);
    }
  };

  const handleDownloadChat = (format: 'txt' | 'json') => {
    if (messages.length === 0) return;
    const project = projects.find((p) => p.id === selectedProjectId);
    const label =
      chatMode === 'set'
        ? sanitizeFilename(selectedSet?.name || session?.persona_name || 'set')
        : sanitizeFilename(selectedPersona?.name || session?.persona_name || 'persona');
    const timestamp = new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-');

    if (format === 'json') {
      downloadFile(
        JSON.stringify(
          {
            exported_at: new Date().toISOString(),
            mode: chatMode,
            persona: selectedPersona
              ? { id: selectedPersona.id, name: selectedPersona.name, set_name: selectedPersona.setName }
              : null,
            persona_set: selectedSet ? { id: selectedSet.id, name: selectedSet.name } : null,
            project: project ? { id: project.id, name: project.name } : null,
            session_id: session?.id ?? null,
            participants: session?.participants || [],
            messages,
          },
          null,
          2
        ),
        `persona_chat_${label}_${timestamp}.json`,
        'application/json'
      );
      return;
    }

    const lines = [
      'Persona Chat Transcript',
      '=======================',
      `Mode: ${chatMode}`,
      chatMode === 'set'
        ? `Persona set: ${selectedSet?.name || session?.persona_name}`
        : `Persona: ${selectedPersona?.name || session?.persona_name}`,
      `Project: ${project?.name ?? 'Unknown'}`,
      `Session ID: ${session?.id ?? 'N/A'}`,
      `Exported: ${new Date().toLocaleString()}`,
      '',
      '---',
      '',
    ];
    for (const msg of messages) {
      const speaker =
        msg.role === 'user' ? 'User' : msg.persona_name || selectedPersona?.name || 'Persona';
      const time = msg.created_at ? new Date(msg.created_at).toLocaleString() : '';
      lines.push(`[${time}] ${speaker}:`);
      lines.push(msg.content);
      if (msg.role === 'assistant' && msg.refused) {
        lines.push(`(refused — ${msg.refusal_reason ?? 'out of scope'})`);
      }
      lines.push('');
    }
    downloadFile(lines.join('\n'), `persona_chat_${label}_${timestamp}.txt`, 'text/plain');
  };

  const handleProjectChange = (projectId: number) => {
    setSelectedProjectId(projectId);
    setSelectedPersonaId(null);
    setSelectedSetId(null);
    setSession(null);
    setMessages([]);
    setError(null);
  };

  const activeTarget =
    chatMode === 'single' ? selectedPersona : selectedSet;

  return (
    <div className="px-4 py-6 sm:px-0">
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 rounded-xl bg-stone-900 flex items-center justify-center">
            <Bot className="w-5 h-5 text-white" />
          </div>
          <div>
            <h2 className="text-3xl font-bold text-stone-900">Persona Chat</h2>
            <p className="text-stone-500 text-sm">
              Chat with one persona or an entire set — answers from profile and study evidence
            </p>
          </div>
        </div>

        {/* Mode tabs */}
        <div className="flex items-center gap-2 mt-4">
          <div className="inline-flex rounded-xl border border-stone-200 bg-white p-1">
            <button
              type="button"
              onClick={() => setChatMode('single')}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                chatMode === 'single'
                  ? 'bg-stone-900 text-white'
                  : 'text-stone-600 hover:text-stone-900'
              }`}
            >
              <User className="w-3.5 h-3.5" />
              Single persona
            </button>
            <button
              type="button"
              onClick={() => setChatMode('set')}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                chatMode === 'set'
                  ? 'bg-stone-900 text-white'
                  : 'text-stone-600 hover:text-stone-900'
              }`}
            >
              <Users className="w-3.5 h-3.5" />
              Persona set
            </button>
          </div>
          <span className="inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-full bg-green-50 text-green-700 border border-green-200">
            <Shield className="w-3 h-3" />
            Strict knowledge control
          </span>
          {chatMode === 'set' && (
            <span className="text-xs text-stone-400">
              No @ → all reply · @Name → only that persona
            </span>
          )}
        </div>
      </div>

      <div
        className="grid grid-cols-1 xl:grid-cols-12 gap-6"
        style={{ minHeight: 'calc(100vh - 240px)' }}
      >
        {/* Left picker */}
        <div className="xl:col-span-2 glass-card rounded-2xl overflow-hidden flex flex-col max-h-[70vh] xl:max-h-none">
          <div className="px-4 py-3 border-b border-stone-200 space-y-3">
            <div>
              <label className="block text-xs font-medium text-stone-500 mb-1.5">Project</label>
              <div className="relative">
                <FolderOpen className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-stone-400 pointer-events-none" />
                <select
                  value={selectedProjectId ?? ''}
                  onChange={(e) => handleProjectChange(parseInt(e.target.value, 10))}
                  className="w-full pl-9 pr-3 py-2 text-sm bg-white border border-stone-200 rounded-xl text-stone-900 focus:outline-none focus:ring-2 focus:ring-stone-900/20"
                >
                  {projects.length === 0 && <option value="">No projects</option>}
                  {projects.map((project) => (
                    <option key={project.id} value={project.id}>
                      {project.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <h3 className="text-sm font-semibold text-stone-900">
              {chatMode === 'single' ? 'Personas' : 'Persona sets'}
              {chatMode === 'single' && projectPersonas.length > 0 && (
                <span className="ml-1.5 text-stone-400 font-normal">({projectPersonas.length})</span>
              )}
              {chatMode === 'set' && personaSets.length > 0 && (
                <span className="ml-1.5 text-stone-400 font-normal">({personaSets.length})</span>
              )}
            </h3>
          </div>
          <div className="flex-1 overflow-y-auto p-2">
            {loadingPersonas ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="w-5 h-5 animate-spin text-stone-400" />
              </div>
            ) : !selectedProjectId ? (
              <p className="text-sm text-stone-400 text-center py-8 px-2">Select a project first</p>
            ) : chatMode === 'single' ? (
              projectPersonas.length === 0 ? (
                <p className="text-sm text-stone-400 text-center py-8 px-2">
                  No personas in this project yet.
                </p>
              ) : (
                projectPersonas.map((persona) => (
                  <button
                    key={persona.id}
                    onClick={() => setSelectedPersonaId(persona.id)}
                    className={`w-full flex items-center gap-2.5 px-2 py-2 rounded-xl text-left transition-colors mb-1 ${
                      selectedPersonaId === persona.id
                        ? 'bg-stone-100 text-stone-900'
                        : 'text-stone-600 hover:bg-stone-50'
                    }`}
                  >
                    <PersonaAvatar
                      name={persona.name}
                      imageUrl={persona.image_url}
                      personaId={persona.id}
                      size="sm"
                    />
                    <div className="min-w-0">
                      <span className="text-sm font-medium truncate block">{persona.name}</span>
                      <span className="text-xs text-stone-400 truncate block">{persona.setName}</span>
                    </div>
                  </button>
                ))
              )
            ) : personaSets.length === 0 ? (
              <p className="text-sm text-stone-400 text-center py-8 px-2">
                No persona sets in this project yet.
              </p>
            ) : (
              personaSets.map((set) => (
                <button
                  key={set.id}
                  onClick={() => setSelectedSetId(set.id)}
                  className={`w-full flex items-start gap-2.5 px-2 py-2 rounded-xl text-left transition-colors mb-1 ${
                    selectedSetId === set.id
                      ? 'bg-stone-100 text-stone-900'
                      : 'text-stone-600 hover:bg-stone-50'
                  }`}
                >
                  <div className="w-8 h-8 rounded-full bg-stone-200 flex items-center justify-center flex-shrink-0">
                    <Users className="w-4 h-4 text-stone-600" />
                  </div>
                  <div className="min-w-0">
                    <span className="text-sm font-medium truncate block">{set.name}</span>
                    <span className="text-xs text-stone-400 block">
                      {set.personas?.length || 0} personas
                    </span>
                  </div>
                </button>
              ))
            )}
          </div>
        </div>

        {/* Chat area */}
        <div
          className={`glass-card rounded-2xl overflow-hidden flex flex-col min-h-[520px] max-h-[75vh] ${
            activeTarget ? 'xl:col-span-5' : 'xl:col-span-10'
          }`}
        >
          {!activeTarget ? (
            <div className="flex-1 flex items-center justify-center text-stone-400">
              <div className="text-center">
                <Bot className="mx-auto h-12 w-12 mb-3 opacity-40" />
                <p>
                  {chatMode === 'single'
                    ? 'Select a project, then pick a persona to start chatting'
                    : 'Select a project, then pick a persona set'}
                </p>
              </div>
            </div>
          ) : (
            <>
              <div className="px-5 py-3 border-b border-stone-200 flex items-center justify-between gap-2 flex-wrap">
                <div className="flex items-center gap-3 min-w-0">
                  {chatMode === 'single' && selectedPersona ? (
                    <PersonaAvatar
                      name={selectedPersona.name}
                      imageUrl={selectedPersona.image_url}
                      personaId={selectedPersona.id}
                    />
                  ) : (
                    <div className="w-10 h-10 rounded-full bg-stone-200 flex items-center justify-center">
                      <Users className="w-5 h-5 text-stone-600" />
                    </div>
                  )}
                  <div className="min-w-0">
                    <p className="font-semibold text-stone-900 truncate">
                      {chatMode === 'single'
                        ? selectedPersona?.name
                        : selectedSet?.name}
                    </p>
                    <p className="text-xs text-stone-400 truncate">
                      {chatMode === 'single'
                        ? selectedPersona?.setName
                        : `${setParticipants.length} personas · type @ to address one`}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-3 flex-wrap">
                  <label className="flex items-center gap-2 text-xs text-stone-600 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={strictMode}
                      onChange={(e) => setStrictMode(e.target.checked)}
                      className="rounded accent-stone-900"
                    />
                    Strict mode
                  </label>
                  <button
                    onClick={() => handleDownloadChat('txt')}
                    disabled={messages.length === 0}
                    className="inline-flex items-center gap-1 text-xs text-stone-500 hover:text-stone-900 transition-colors disabled:opacity-40"
                  >
                    <Download className="w-3.5 h-3.5" />
                    Download
                  </button>
                  <button
                    onClick={() => handleDownloadChat('json')}
                    disabled={messages.length === 0}
                    className="inline-flex items-center gap-1 text-xs text-stone-500 hover:text-stone-900 transition-colors disabled:opacity-40"
                  >
                    JSON
                  </button>
                  <button
                    onClick={handleNewChat}
                    disabled={initializing}
                    className="inline-flex items-center gap-1 text-xs text-stone-500 hover:text-stone-900 transition-colors"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 ${initializing ? 'animate-spin' : ''}`} />
                    New chat
                  </button>
                </div>
              </div>

              {/* Set participant chips */}
              {chatMode === 'set' && setParticipants.length > 0 && (
                <div className="px-4 py-2 border-b border-stone-100 flex flex-wrap gap-1.5">
                  {setParticipants.map((p) => {
                    const name = (p.persona_data as any)?.name || p.name;
                    return (
                      <button
                        key={p.id}
                        type="button"
                        onClick={() => insertMention(p)}
                        className="inline-flex items-center gap-1.5 rounded-full bg-stone-50 border border-stone-200 px-2 py-0.5 text-xs text-stone-700 hover:bg-stone-100"
                        title={`Mention @${name}`}
                      >
                        <PersonaAvatar name={name} imageUrl={p.image_url} personaId={p.id} size="sm" />
                        @{name}
                      </button>
                    );
                  })}
                </div>
              )}

              <div className="flex-1 overflow-y-auto px-5 py-4 min-h-0">
                {initializing ? (
                  <div className="flex items-center justify-center h-full">
                    <Loader2 className="h-6 w-6 animate-spin text-stone-400" />
                  </div>
                ) : messages.length === 0 ? (
                  <div className="flex items-center justify-center h-full text-stone-400 text-sm text-center">
                    <div>
                      <p className="mb-1">
                        {chatMode === 'single'
                          ? `Ask ${selectedPersona?.name} a question.`
                          : `Ask the ${selectedSet?.name} set a question.`}
                      </p>
                      <p className="text-xs">
                        {chatMode === 'set'
                          ? 'Everyone replies unless you @mention someone.'
                          : 'They answer from their profile and project documents.'}
                      </p>
                    </div>
                  </div>
                ) : (
                  messages.map((msg) => (
                    <ChatBubble
                      key={msg.id}
                      message={msg}
                      fallbackPersonaName={selectedPersona?.name}
                      fallbackPersonaImageUrl={selectedPersona?.image_url}
                      fallbackPersonaId={selectedPersona?.id}
                    />
                  ))
                )}
                {loading && (
                  <div className="flex items-center gap-2 text-stone-400 text-sm mb-4">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    {chatMode === 'set'
                      ? 'Personas are responding...'
                      : `${selectedPersona?.name || 'Persona'} is thinking...`}
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>

              {error && (
                <div className="mx-5 mb-2 flex items-center gap-2 text-sm text-red-600 bg-red-50 border border-red-100 rounded-lg px-3 py-2">
                  <AlertCircle className="w-4 h-4 flex-shrink-0" />
                  {error}
                </div>
              )}

              <form onSubmit={handleSend} className="px-5 py-4 border-t border-stone-200 relative">
                {mentionOpen && mentionCandidates.length > 0 && (
                  <div className="absolute bottom-full left-5 right-5 mb-1 max-h-48 overflow-y-auto rounded-xl border border-stone-200 bg-white shadow-lg z-20">
                    {mentionCandidates.map((p, idx) => {
                      const name = (p.persona_data as any)?.name || p.name;
                      return (
                        <button
                          key={p.id}
                          type="button"
                          onMouseDown={(e) => {
                            e.preventDefault();
                            insertMention(p);
                          }}
                          className={`w-full flex items-center gap-2 px-3 py-2 text-left text-sm ${
                            idx === mentionIndex ? 'bg-stone-100' : 'hover:bg-stone-50'
                          }`}
                        >
                          <PersonaAvatar name={name} imageUrl={p.image_url} personaId={p.id} size="sm" />
                          <span className="font-medium text-stone-900">@{name}</span>
                        </button>
                      );
                    })}
                  </div>
                )}
                <div className="flex gap-3">
                  <input
                    ref={inputRef}
                    type="text"
                    value={input}
                    onChange={(e) => handleInputChange(e.target.value)}
                    onKeyDown={(e) => {
                      if (!mentionOpen || mentionCandidates.length === 0) return;
                      if (e.key === 'ArrowDown') {
                        e.preventDefault();
                        setMentionIndex((i) => (i + 1) % mentionCandidates.length);
                      } else if (e.key === 'ArrowUp') {
                        e.preventDefault();
                        setMentionIndex(
                          (i) => (i - 1 + mentionCandidates.length) % mentionCandidates.length
                        );
                      } else if (e.key === 'Enter' && mentionOpen) {
                        e.preventDefault();
                        insertMention(mentionCandidates[mentionIndex]);
                      } else if (e.key === 'Escape') {
                        setMentionOpen(false);
                      }
                    }}
                    placeholder={
                      chatMode === 'set'
                        ? `Ask the set, or @someone...`
                        : `Ask ${selectedPersona?.name || 'persona'} something...`
                    }
                    disabled={loading || initializing || !session}
                    className="flex-1 px-4 py-2.5 bg-white border border-stone-200 rounded-xl text-stone-900 placeholder:text-stone-400 focus:outline-none focus:ring-2 focus:ring-stone-900/20 disabled:opacity-50"
                  />
                  <button
                    type="submit"
                    disabled={loading || initializing || !input.trim() || !session}
                    className="inline-flex items-center justify-center px-4 py-2.5 rounded-xl text-white bg-stone-900 hover:bg-stone-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                  </button>
                </div>
              </form>
            </>
          )}
        </div>

        {/* Right panel: profile (single) or roster (set) */}
        {chatMode === 'single' && selectedPersona && (
          <div className="xl:col-span-5 flex flex-col min-h-[520px] max-h-[75vh]">
            <div className="px-1 pb-2">
              <h3 className="text-sm font-semibold text-stone-900">Persona profile</h3>
            </div>
            <div className="flex-1 min-h-0 overflow-y-auto">
              <PersonaProfileCard persona={selectedPersona} compact />
            </div>
          </div>
        )}

        {chatMode === 'set' && selectedSet && (
          <div className="xl:col-span-5 flex flex-col min-h-[520px] max-h-[75vh]">
            <div className="px-1 pb-2">
              <h3 className="text-sm font-semibold text-stone-900">
                Set roster · {selectedSet.name}
              </h3>
            </div>
            <div className="flex-1 min-h-0 overflow-y-auto space-y-3">
              {setParticipants.map((p) => (
                <PersonaProfileCard key={p.id} persona={p} compact />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
