import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, LayoutGrid, Maximize2, X } from 'lucide-react';
import PersonaProfileCard from '../components/PersonaProfileCard';
import { personasApi } from '../services/api';
import { Persona, PersonaSet } from '../types';
import { usePersonaViewTimer } from '../hooks/usePersonaViewTimer';

export default function PersonaSetProfilesPage() {
  const { setId } = useParams<{ setId: string }>();
  const navigate = useNavigate();
  const [personaSet, setPersonaSet] = useState<PersonaSet | null>(null);
  const [loading, setLoading] = useState(true);
  const [expandedPersona, setExpandedPersona] = useState<Persona | null>(null);

  const resolvedSetId = personaSet?.id ?? (setId ? parseInt(setId, 10) : null);

  usePersonaViewTimer({
    personaSetId: resolvedSetId,
    viewType: 'set_profiles',
    enabled: !loading && !!resolvedSetId,
  });

  usePersonaViewTimer({
    personaSetId: resolvedSetId,
    personaId: expandedPersona?.id ?? null,
    viewType: 'persona',
    enabled: !!expandedPersona?.id,
  });

  useEffect(() => {
    if (!setId) return;
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const set = await personasApi.getSet(parseInt(setId, 10));
        if (!cancelled) setPersonaSet(set);
      } catch (error) {
        console.error('Failed to load persona set:', error);
        if (!cancelled) setPersonaSet(null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [setId]);

  useEffect(() => {
    if (!expandedPersona) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setExpandedPersona(null);
    };
    document.addEventListener('keydown', onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = prev;
    };
  }, [expandedPersona]);

  if (loading) {
    return <div className="px-4 py-6 text-stone-600">Loading profiles…</div>;
  }

  if (!personaSet) {
    return (
      <div className="px-4 py-6">
        <p className="text-stone-600 mb-4">Persona set not found.</p>
        <button
          type="button"
          onClick={() => navigate('/personas')}
          className="inline-flex items-center gap-2 text-stone-700 hover:text-stone-900"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Personas
        </button>
      </div>
    );
  }

  const count = personaSet.personas.length;
  const gridCols =
    count <= 1
      ? 'grid-cols-1 max-w-2xl mx-auto'
      : count === 2
        ? 'grid-cols-1 md:grid-cols-2'
        : 'grid-cols-1 md:grid-cols-2 xl:grid-cols-3';

  return (
    <div className="px-4 py-6">
      <div className="glass-card rounded-2xl p-4 mb-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex min-w-0 items-center gap-3">
            <button
              type="button"
              onClick={() => navigate(`/personas/${personaSet.id}`)}
              className="flex-shrink-0 rounded-lg p-2 transition-colors hover:bg-stone-100"
              title="Back to carousel view"
            >
              <ArrowLeft className="h-5 w-5 text-stone-900" />
            </button>
            <div className="min-w-0">
              <div className="flex items-center gap-2 text-stone-500 text-xs font-medium uppercase tracking-wide mb-0.5">
                <LayoutGrid className="h-3.5 w-3.5" />
                All profiles
              </div>
              <h1 className="truncate text-lg font-bold text-stone-900 sm:text-xl">
                {personaSet.name}
              </h1>
              <p className="text-sm text-stone-500">
                {count} persona{count !== 1 ? 's' : ''} · click a card to enlarge
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => navigate(`/personas/${personaSet.id}`)}
            className="inline-flex items-center justify-center gap-2 rounded-lg bg-stone-100 px-4 py-2.5 text-sm text-stone-900 hover:bg-stone-200"
          >
            Single persona view
          </button>
        </div>
      </div>

      {count === 0 ? (
        <div className="glass-card rounded-2xl p-8 text-center text-stone-600">
          This set has no personas yet.
        </div>
      ) : (
        <div className={`grid gap-4 ${gridCols}`}>
          {personaSet.personas.map((persona) => (
            <div key={persona.id} className="relative min-w-0">
              <div className="absolute top-3 right-3 z-10 pointer-events-none">
                <span className="inline-flex items-center gap-1 rounded-full bg-white/90 border border-stone-200 px-2 py-1 text-xs text-stone-600 shadow-sm">
                  <Maximize2 className="h-3 w-3" />
                  Expand
                </span>
              </div>
              <div className="max-h-[70vh] overflow-hidden rounded-2xl">
                <PersonaProfileCard
                  persona={persona}
                  compact
                  onClick={() => setExpandedPersona(persona)}
                  className="h-full"
                />
              </div>
              <div className="pointer-events-none absolute inset-x-0 bottom-0 h-16 rounded-b-2xl bg-gradient-to-t from-[#f8f7f4] to-transparent" />
            </div>
          ))}
        </div>
      )}

      {expandedPersona && (
        <div
          className="fixed inset-0 z-[100] flex items-center justify-center p-4 sm:p-6"
          role="dialog"
          aria-modal="true"
          aria-label={`${expandedPersona.persona_data?.name || expandedPersona.name} profile`}
        >
          <button
            type="button"
            className="absolute inset-0 bg-stone-900/50"
            aria-label="Close profile"
            onClick={() => setExpandedPersona(null)}
          />
          <div className="relative z-10 flex max-h-[92vh] w-full max-w-4xl flex-col overflow-hidden rounded-2xl bg-[#f8f7f4] shadow-2xl">
            <div className="flex items-center justify-between gap-3 border-b border-stone-200 bg-white px-4 py-3">
              <h2 className="truncate text-base font-semibold text-stone-900">
                {expandedPersona.persona_data?.name || expandedPersona.name}
              </h2>
              <button
                type="button"
                onClick={() => setExpandedPersona(null)}
                className="rounded-lg p-2 text-stone-600 hover:bg-stone-100 hover:text-stone-900"
                aria-label="Close"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            <div className="min-h-0 flex-1 overflow-y-auto p-4 sm:p-6">
              <PersonaProfileCard persona={expandedPersona} />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
