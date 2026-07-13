import { useState, useEffect, useRef } from 'react';
import { useParams } from 'react-router-dom';
import { Bot, Send, Loader2, Shield, AlertCircle, RefreshCw } from 'lucide-react';
import { personaChatApi, personasApi } from '../services/api';
import { PersonaSet, PersonaChatMessage, PersonaChatSession } from '../types';
import { getPersonaImageUrl } from '../utils/imageUtils';

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
            {message.retrieval_score != null && !refused && (
              <span className="text-xs text-stone-400">
                relevance {(message.retrieval_score * 100).toFixed(0)}%
              </span>
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
  const [personaSets, setPersonaSets] = useState<PersonaSet[]>([]);
  const [selectedPersonaId, setSelectedPersonaId] = useState<number | null>(
    personaIdParam ? parseInt(personaIdParam, 10) : null
  );
  const [session, setSession] = useState<PersonaChatSession | null>(null);
  const [messages, setMessages] = useState<PersonaChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [initializing, setInitializing] = useState(false);
  const [strictMode, setStrictMode] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    personasApi.getAllSets().then(setPersonaSets).catch(() => setError('Failed to load personas'));
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const selectedPersona = personaSets
    .flatMap((s) => s.personas.map((p) => ({ ...p, setName: s.name })))
    .find((p) => p.id === selectedPersonaId);

  const startSession = async (personaId: number) => {
    setInitializing(true);
    setError(null);
    setMessages([]);
    setSession(null);
    try {
      const newSession = await personaChatApi.createSession(personaId);
      setSession(newSession);
      setMessages(newSession.messages || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to start chat');
    } finally {
      setInitializing(false);
    }
  };

  useEffect(() => {
    if (selectedPersonaId) {
      startSession(selectedPersonaId);
    }
  }, [selectedPersonaId]);

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
      setError(err.response?.data?.detail || err.message || 'Failed to send message');
      setMessages((prev) => prev.filter((m) => m.id !== optimisticUser.id));
      setInput(userText);
    } finally {
      setLoading(false);
    }
  };

  const handleNewChat = () => {
    if (selectedPersonaId) startSession(selectedPersonaId);
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
            Out-of-scope questions receive: &ldquo;I don&apos;t know.&rdquo;
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6" style={{ minHeight: 'calc(100vh - 220px)' }}>
        {/* Persona picker */}
        <div className="lg:col-span-1 glass-card rounded-2xl overflow-hidden flex flex-col">
          <div className="px-4 py-3 border-b border-stone-200">
            <h3 className="text-sm font-semibold text-stone-900">Select Persona</h3>
          </div>
          <div className="flex-1 overflow-y-auto p-2 max-h-[60vh] lg:max-h-none">
            {personaSets.map((set) => (
              <div key={set.id} className="mb-3">
                <p className="text-xs font-medium text-stone-400 uppercase tracking-wide px-2 mb-1">
                  {set.name}
                </p>
                {set.personas.map((persona) => (
                  <button
                    key={persona.id}
                    onClick={() => setSelectedPersonaId(persona.id)}
                    className={`w-full flex items-center gap-2.5 px-2 py-2 rounded-xl text-left transition-colors ${
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
                    <span className="text-sm font-medium truncate">{persona.name}</span>
                  </button>
                ))}
              </div>
            ))}
          </div>
        </div>

        {/* Chat area */}
        <div className="lg:col-span-3 glass-card rounded-2xl overflow-hidden flex flex-col">
          {!selectedPersona ? (
            <div className="flex-1 flex items-center justify-center text-stone-400">
              <div className="text-center">
                <Bot className="mx-auto h-12 w-12 mb-3 opacity-40" />
                <p>Select a persona to start chatting</p>
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
