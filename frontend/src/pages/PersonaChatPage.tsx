import { useState, useEffect, useRef } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import { Bot, Send, Loader2, Shield, AlertCircle, RefreshCw, FolderOpen } from 'lucide-react';
import { personaChatApi, personasApi, projectsApi } from '../services/api';
import { PersonaSet, PersonaChatMessage, PersonaChatSession, Project } from '../types';
import { getPersonaImageUrl } from '../utils/imageUtils';

const PROJECT_STORAGE_KEY = 'persona-chat-project-id';

function PersonaAvatar({
  name,
  imageUrl,
  personaId,
  size = 'md',
}: {
  name: string;
  imageUrl?: string | null;
  personaId?: number;
  size?: 'sm' | 'md';
}) {
  const [imageError, setImageError] = useState(false);
  const sizeClasses = { sm: 'w-8 h-8 text-sm', md: 'w-10 h-10 text-base' };
  const src = getPersonaImageUrl(imageUrl, personaId);

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

function ChatBubble({ message, personaName, personaImageUrl, personaId }: {
  message: PersonaChatMessage;
  personaName: string;
  personaImageUrl?: string | null;
  personaId: number;
}) {
  const isUser = message.role === 'user';

  if (isUser) {
    return (
      <div className="flex justify-end mb-4">
        <div className="bg-stone-900 text-white rounded-2xl px-4 py-3 max-w-[75%]">
          <p className="text-sm leading-relaxed">{message.content}</p>
        </div>
      </div>
    );
  }

  const refused = message.refused;
  return (
    <div className="flex justify-start mb-4">
      <div className="flex items-start gap-3 max-w-[80%]">
        <PersonaAvatar name={personaName} imageUrl={personaImageUrl} personaId={personaId} size="sm" />
        <div className={`rounded-2xl px-4 py-3 ${
          refused
            ? 'bg-amber-50 border border-amber-200'
            : 'bg-white border border-stone-200'
        }`}>
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <span className="text-sm font-semibold text-stone-900">{personaName}</span>
            {refused && (
              <span className="text-xs px-1.5 py-0.5 rounded-full bg-amber-100 text-amber-700">
                {message.refusal_reason === 'jailbreak_attempt'
                  ? 'Blocked'
                  : message.refusal_reason === 'boundary_violation'
                    ? 'Boundary enforced'
                    : 'Out of scope'}
              </span>
            )}
            {message.retrieval_score != null && !refused && message.sources_used && message.sources_used.length > 0 && (
              <span className="text-xs text-stone-400">
                relevance {(message.retrieval_score * 100).toFixed(0)}%
              </span>
            )}
            {!refused && (!message.sources_used || message.sources_used.length === 0) && (
              <span className="text-xs text-stone-400">from profile</span>
            )}
          </div>
          <p className={`text-sm leading-relaxed ${refused ? 'text-amber-800 italic' : 'text-stone-800'}`}>
            {message.content}
          </p>
          {message.sources_used && message.sources_used.length > 0 && (
            <p className="text-xs text-stone-400 mt-2">
              Grounded in {message.sources_used.length} evidence chunk{message.sources_used.length !== 1 ? 's' : ''}
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

  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<number | null>(null);
  const [personaSets, setPersonaSets] = useState<PersonaSet[]>([]);
  const [loadingPersonas, setLoadingPersonas] = useState(false);
  const [selectedPersonaId, setSelectedPersonaId] = useState<number | null>(
    personaIdParam ? parseInt(personaIdParam, 10) : null
  );
  const [session, setSession] = useState<PersonaChatSession | null>(null);
  const [messages, setMessages] = useState<PersonaChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [initializing, setInitializing] = useState(false);
  const [strictMode, setStrictMode] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    projectsApi.getAll()
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
    personasApi.getAllSets(selectedProjectId)
      .then((sets) => {
        setPersonaSets(sets);
        const allIds = sets.flatMap((s: PersonaSet) => s.personas.map((p) => p.id));
        if (selectedPersonaId && !allIds.includes(selectedPersonaId)) {
          setSelectedPersonaId(null);
          setSession(null);
          setMessages([]);
        }
      })
      .catch(() => setError('Failed to load personas for this project'))
      .finally(() => setLoadingPersonas(false));
  }, [selectedProjectId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const projectPersonas = personaSets.flatMap((s) =>
    s.personas.map((p) => ({ ...p, setName: s.name }))
  );

  const selectedPersona = projectPersonas.find((p) => p.id === selectedPersonaId);

  const startSession = async (personaId: number, projectId: number) => {
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

  useEffect(() => {
    if (selectedPersonaId && selectedProjectId) {
      startSession(selectedPersonaId, selectedProjectId);
    }
  }, [selectedPersonaId, selectedProjectId]);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || !session || loading) return;

    const userText = input.trim();
    setInput('');
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
      const assistantMsg: PersonaChatMessage = {
        id: reply.message_id,
        role: 'assistant',
        content: reply.reply,
        refused: reply.refused,
        retrieval_score: reply.retrieval_score,
        sources_used: reply.sources_used,
        refusal_reason: reply.refusal_reason,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: any) {
      const detail = err.response?.data?.detail || err.message || 'Failed to send message';
      const timedOut = err.code === 'ECONNABORTED';
      setError(timedOut ? 'Request timed out — try again or pick a shorter question.' : detail);
      setMessages((prev) => prev.filter((m) => m.id !== optimisticUser.id));
      setInput(userText);
    } finally {
      setLoading(false);
    }
  };

  const handleNewChat = () => {
    if (selectedPersonaId && selectedProjectId) {
      startSession(selectedPersonaId, selectedProjectId);
    }
  };

  const handleProjectChange = (projectId: number) => {
    setSelectedProjectId(projectId);
    setSelectedPersonaId(null);
    setSession(null);
    setMessages([]);
    setError(null);
  };

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
              1:1 chat with a persona — answers only from their profile and project evidence
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 mt-3">
          <span className="inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-full bg-green-50 text-green-700 border border-green-200">
            <Shield className="w-3 h-3" />
            Strict knowledge control
          </span>
          <span className="text-xs text-stone-400">
            Out-of-scope questions receive: &ldquo;I don&apos;t know.&rdquo; — toggle Strict mode for tighter control
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6" style={{ minHeight: 'calc(100vh - 220px)' }}>
        {/* Persona picker */}
        <div className="lg:col-span-1 glass-card rounded-2xl overflow-hidden flex flex-col">
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
                    <option key={project.id} value={project.id}>{project.name}</option>
                  ))}
                </select>
              </div>
            </div>
            <h3 className="text-sm font-semibold text-stone-900">
              Personas
              {projectPersonas.length > 0 && (
                <span className="ml-1.5 text-stone-400 font-normal">({projectPersonas.length})</span>
              )}
            </h3>
          </div>
          <div className="flex-1 overflow-y-auto p-2 max-h-[60vh] lg:max-h-none">
            {loadingPersonas ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="w-5 h-5 animate-spin text-stone-400" />
              </div>
            ) : !selectedProjectId ? (
              <p className="text-sm text-stone-400 text-center py-8 px-2">Select a project first</p>
            ) : projectPersonas.length === 0 ? (
              <p className="text-sm text-stone-400 text-center py-8 px-2">
                No personas in this project yet. Generate or attach a persona set first.
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
            )}
          </div>
        </div>

        {/* Chat area */}
        <div className="lg:col-span-3 glass-card rounded-2xl overflow-hidden flex flex-col">
          {!selectedPersona ? (
            <div className="flex-1 flex items-center justify-center text-stone-400">
              <div className="text-center">
                <Bot className="mx-auto h-12 w-12 mb-3 opacity-40" />
                <p>Select a project, then pick a persona to start chatting</p>
              </div>
            </div>
          ) : (
            <>
              {/* Chat header */}
              <div className="px-5 py-3 border-b border-stone-200 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <PersonaAvatar
                    name={selectedPersona.name}
                    imageUrl={selectedPersona.image_url}
                    personaId={selectedPersona.id}
                  />
                  <div>
                    <p className="font-semibold text-stone-900">{selectedPersona.name}</p>
                    <p className="text-xs text-stone-400">{selectedPersona.setName}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
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
                    onClick={handleNewChat}
                    disabled={initializing}
                    className="inline-flex items-center gap-1 text-xs text-stone-500 hover:text-stone-900 transition-colors"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 ${initializing ? 'animate-spin' : ''}`} />
                    New chat
                  </button>
                </div>
              </div>

              {/* Messages */}
              <div className="flex-1 overflow-y-auto px-5 py-4 min-h-[300px]">
                {initializing ? (
                  <div className="flex items-center justify-center h-full">
                    <Loader2 className="h-6 w-6 animate-spin text-stone-400" />
                  </div>
                ) : messages.length === 0 ? (
                  <div className="flex items-center justify-center h-full text-stone-400 text-sm text-center">
                    <div>
                      <p className="mb-1">Ask {selectedPersona.name} a question.</p>
                      <p className="text-xs">They will only answer from their profile and project documents.</p>
                    </div>
                  </div>
                ) : (
                  messages.map((msg) => (
                    <ChatBubble
                      key={msg.id}
                      message={msg}
                      personaName={selectedPersona.name}
                      personaImageUrl={selectedPersona.image_url}
                      personaId={selectedPersona.id}
                    />
                  ))
                )}
                {loading && (
                  <div className="flex items-center gap-2 text-stone-400 text-sm mb-4">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    {selectedPersona.name} is thinking...
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

              {/* Input */}
              <form onSubmit={handleSend} className="px-5 py-4 border-t border-stone-200">
                <div className="flex gap-3">
                  <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder={`Ask ${selectedPersona.name} something...`}
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
      </div>
    </div>
  );
}
