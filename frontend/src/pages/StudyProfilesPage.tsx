import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowDown, ArrowUp, LayoutGrid, LogOut, Maximize2, Save, X } from 'lucide-react';
import PersonaProfileCard from '../components/PersonaProfileCard';
import { studyApi, clearAuthToken } from '../services/api';
import { Persona } from '../types';
import { useAuth } from '../context/AuthContext';
import { setStudyScope, useStudyTracker, clearStudyScope } from '../hooks/useStudyTracker';
import { usePersonaViewTimer } from '../hooks/usePersonaViewTimer';

type StudyPersona = Persona & { stakeholder_group?: string | null };

export default function StudyProfilesPage() {
  const { slug } = useParams<{ slug: string }>();
  const navigate = useNavigate();
  const { user, logout, refresh } = useAuth();
  const { track } = useStudyTracker(slug);
  const [personas, setPersonas] = useState<StudyPersona[]>([]);
  const [personaSetId, setPersonaSetId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [savingOrder, setSavingOrder] = useState(false);
  const [expanded, setExpanded] = useState<StudyPersona | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [orderCondition, setOrderCondition] = useState<string | null>(null);
  const [hasRotations, setHasRotations] = useState(false);
  const [orderDirty, setOrderDirty] = useState(false);

  const canReorder = !!user?.is_admin && !hasRotations;

  useEffect(() => {
    if (slug) {
      setStudyScope({ slug });
    }
  }, [slug]);

  useEffect(() => {
    if (!slug) return;
    if (!user) {
      navigate(`/study/${slug}`, { replace: true });
      return;
    }
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await studyApi.getPersonas(slug);
        if (cancelled) return;
        setPersonaSetId(data.persona_set_id);
        setPersonas(
          data.personas.map((p) => ({
            ...p,
            persona_data: p.persona_data || {},
          })) as StudyPersona[]
        );
        setOrderCondition(data.order_condition || null);
        setHasRotations(!!data.has_order_rotations);
        setOrderDirty(false);
        if (slug) {
          setStudyScope({
            slug,
            projectId: data.project_id ?? null,
            personaSetId: data.persona_set_id,
          });
        }
        track('profiles_loaded', {
          count: data.personas.length,
          order_condition: data.order_condition,
          order_rotation_index: data.order_rotation_index,
          persona_order: data.persona_order,
        });
      } catch (e: any) {
        if (!cancelled) setError(e?.response?.data?.detail || e.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
    // intentionally only reload when slug/user identity changes
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [slug, user?.id]);

  usePersonaViewTimer({
    personaSetId,
    viewType: 'set_profiles',
    enabled: !loading && !!personaSetId,
  });

  usePersonaViewTimer({
    personaSetId,
    personaId: expanded?.id ?? null,
    personaName: expanded?.name ?? null,
    viewType: 'persona',
    enabled: !!expanded?.id,
  });

  useEffect(() => {
    if (!expanded) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        track('profile_modal_close', { persona_id: expanded.id, via: 'escape' });
        setExpanded(null);
      }
    };
    document.addEventListener('keydown', onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = prev;
    };
  }, [expanded, track]);

  const move = (index: number, dir: -1 | 1) => {
    const next = index + dir;
    if (next < 0 || next >= personas.length) return;
    setPersonas((prev) => {
      const copy = [...prev];
      const tmp = copy[index];
      copy[index] = copy[next];
      copy[next] = tmp;
      return copy;
    });
    setOrderDirty(true);
    track('persona_reorder_step', { from: index, to: next });
  };

  const saveOrder = async () => {
    if (!slug || !canReorder) return;
    setSavingOrder(true);
    try {
      const order = personas.map((p) => p.id);
      await studyApi.updatePersonaOrder(slug, order);
      setOrderDirty(false);
      track('persona_order_saved', { persona_order: order });
    } catch (e: any) {
      alert(e?.response?.data?.detail || e.message);
    } finally {
      setSavingOrder(false);
    }
  };

  const handleLogout = () => {
    track('study_logout');
    clearStudyScope();
    clearAuthToken();
    logout();
    navigate(slug ? `/study/${slug}` : '/login');
    void refresh();
  };

  const gridCols = useMemo(() => {
    const count = personas.length;
    if (count <= 1) return 'grid-cols-1 max-w-2xl mx-auto';
    if (count === 2) return 'grid-cols-1 md:grid-cols-2';
    return 'grid-cols-1 md:grid-cols-2 xl:grid-cols-3';
  }, [personas.length]);

  if (loading) {
    return <div className="px-4 py-10 text-center text-stone-600">Loading profiles…</div>;
  }

  if (error) {
    return (
      <div className="px-4 py-10 text-center">
        <p className="text-stone-700 mb-4">{error}</p>
        <button
          type="button"
          onClick={() => navigate(`/study/${slug}`)}
          className="px-4 py-2 rounded-xl bg-stone-900 text-white"
        >
          Back to study entry
        </button>
      </div>
    );
  }

  return (
    <div className="px-4 py-6">
      <div className="glass-card rounded-2xl p-4 mb-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="min-w-0">
            <div className="flex items-center gap-2 text-stone-500 text-xs font-medium uppercase tracking-wide mb-0.5">
              <LayoutGrid className="h-3.5 w-3.5" />
              Study profiles
            </div>
            <h1 className="text-lg font-bold text-stone-900 sm:text-xl truncate">
              {slug}
            </h1>
            <p className="text-sm text-stone-500">
              {user?.participant_code || user?.name || 'Participant'}
              {orderCondition ? ` · ${orderCondition}` : ''}
              {' · '}
              {personas.length} persona{personas.length !== 1 ? 's' : ''}
              {canReorder ? ' · drag order with arrows, then Save' : ''}
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {canReorder && (
              <button
                type="button"
                onClick={saveOrder}
                disabled={!orderDirty || savingOrder}
                className="inline-flex items-center gap-2 rounded-lg bg-stone-900 px-3 py-2 text-sm text-white disabled:opacity-40"
              >
                <Save className="h-4 w-4" />
                {savingOrder ? 'Saving…' : 'Save order'}
              </button>
            )}
            <button
              type="button"
              onClick={handleLogout}
              className="inline-flex items-center gap-2 rounded-lg bg-stone-100 px-3 py-2 text-sm text-stone-900"
            >
              <LogOut className="h-4 w-4" />
              End session
            </button>
          </div>
        </div>
      </div>

      <div className={`grid gap-4 ${gridCols}`}>
        {personas.map((persona, index) => (
          <div key={persona.id} className="relative min-w-0">
            {canReorder && (
              <div className="absolute top-3 left-3 z-20 flex flex-col gap-1">
                <button
                  type="button"
                  onClick={() => move(index, -1)}
                  disabled={index === 0}
                  className="rounded-md bg-white/95 border border-stone-200 p-1 disabled:opacity-30"
                  aria-label="Move left"
                >
                  <ArrowUp className="h-3.5 w-3.5" />
                </button>
                <button
                  type="button"
                  onClick={() => move(index, 1)}
                  disabled={index === personas.length - 1}
                  className="rounded-md bg-white/95 border border-stone-200 p-1 disabled:opacity-30"
                  aria-label="Move right"
                >
                  <ArrowDown className="h-3.5 w-3.5" />
                </button>
              </div>
            )}
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
                stakeholderSubtext={
                  persona.stakeholder_group ||
                  persona.persona_data?.stakeholder_group ||
                  null
                }
                onClick={() => {
                  setExpanded(persona);
                  track('profile_expand', {
                    persona_id: persona.id,
                    persona_name: persona.name,
                    stakeholder_group:
                      persona.stakeholder_group || persona.persona_data?.stakeholder_group,
                  });
                }}
                className="h-full"
              />
            </div>
            <div className="pointer-events-none absolute inset-x-0 bottom-0 h-16 rounded-b-2xl bg-gradient-to-t from-[#f8f7f4] to-transparent" />
          </div>
        ))}
      </div>

      {expanded && (
        <div
          className="fixed inset-0 z-[100] flex items-center justify-center p-4 sm:p-6"
          role="dialog"
          aria-modal="true"
        >
          <button
            type="button"
            className="absolute inset-0 bg-stone-900/50"
            aria-label="Close"
            onClick={() => {
              track('profile_modal_close', { persona_id: expanded.id, via: 'backdrop' });
              setExpanded(null);
            }}
          />
          <div className="relative z-10 flex max-h-[92vh] w-full max-w-4xl min-w-0 flex-col overflow-hidden rounded-2xl bg-[#f8f7f4] shadow-2xl">
            <div className="flex items-center justify-between gap-3 border-b border-stone-200 bg-white px-4 py-3">
              <h2 className="truncate text-base font-semibold text-stone-900">
                {expanded.persona_data?.name || expanded.name}
              </h2>
              <button
                type="button"
                onClick={() => {
                  track('profile_modal_close', { persona_id: expanded.id, via: 'button' });
                  setExpanded(null);
                }}
                className="rounded-lg p-2 text-stone-600 hover:bg-stone-100"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            <div className="min-h-0 min-w-0 flex-1 overflow-y-auto overflow-x-hidden p-4 sm:p-6">
              <PersonaProfileCard
                persona={expanded}
                stakeholderSubtext={
                  expanded.stakeholder_group ||
                  expanded.persona_data?.stakeholder_group ||
                  null
                }
                className="border-0 shadow-none bg-transparent"
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
