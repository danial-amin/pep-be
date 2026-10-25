import { FormEvent, useEffect, useMemo, useState } from 'react';
import { Navigate, Link } from 'react-router-dom';
import { ClipboardList, ExternalLink, RefreshCw, Save } from 'lucide-react';
import { personasApi, projectsApi, studyApi } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { DEFAULT_STUDY_SLUG, studyEnterPath } from '../studyScope';
import { PersonaSet, Project } from '../types';

type Tab = 'config' | 'participants' | 'events';

export default function StudyAdminPage() {
  const { user } = useAuth();
  const isAdmin = !!user?.is_admin;

  const [tab, setTab] = useState<Tab>('config');
  const [slug, setSlug] = useState(DEFAULT_STUDY_SLUG);
  const [studies, setStudies] = useState<
    Array<{ slug: string; name: string; enabled: boolean; participant_count: number; event_count: number }>
  >([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [personaSets, setPersonaSets] = useState<PersonaSet[]>([]);
  const [config, setConfig] = useState<{
    name: string;
    enabled: boolean;
    project_id: number | null;
    persona_set_id: number;
    allow_open_codes: boolean;
    max_participants: number;
    welcome_text: string;
    order_rotations?: string[][] | null;
    persona_order?: number[] | null;
  } | null>(null);

  const [participants, setParticipants] = useState<
    Array<{
      id: number;
      code: string;
      event_count: number;
      last_seen_at?: string | null;
      is_test: boolean;
    }>
  >([]);
  const [events, setEvents] = useState<
    Array<{
      id: number;
      participant_id?: number | null;
      participant_code?: string | null;
      user_id?: number | null;
      event_type: string;
      path?: string | null;
      payload?: Record<string, unknown> | null;
      created_at?: string | null;
    }>
  >([]);
  const [eventSearch, setEventSearch] = useState('');
  const [debouncedEventSearch, setDebouncedEventSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savedMsg, setSavedMsg] = useState<string | null>(null);

  useEffect(() => {
    if (!isAdmin) return;
    let cancelled = false;
    const run = async () => {
      setLoading(true);
      setError(null);
      try {
        const [proj, studyList] = await Promise.all([
          projectsApi.getAll(),
          studyApi.adminListStudies(),
        ]);
        if (cancelled) return;
        setProjects(proj);
        setStudies(studyList);
        const activeSlug =
          studyList.length && !studyList.some((s) => s.slug === slug)
            ? studyList[0].slug
            : slug;
        if (activeSlug !== slug) {
          setSlug(activeSlug);
          return;
        }
        const data = await studyApi.adminGetStudy(activeSlug);
        if (cancelled) return;
        setConfig({
          name: data.name,
          enabled: data.enabled,
          project_id: data.project_id ?? null,
          persona_set_id: data.persona_set_id,
          allow_open_codes: data.allow_open_codes,
          max_participants: data.max_participants,
          welcome_text: data.welcome_text || '',
          order_rotations: data.order_rotations,
          persona_order: data.persona_order,
        });
        const sets = await personasApi.getAllSets(data.project_id ?? undefined);
        if (!cancelled) setPersonaSets(sets);
      } catch (e: any) {
        if (!cancelled) {
          setError(e?.response?.data?.detail || e.message || 'Failed to load study admin');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    void run();
    return () => {
      cancelled = true;
    };
  }, [slug, isAdmin]);

  useEffect(() => {
    if (!isAdmin || config?.project_id == null) return;
    void personasApi.getAllSets(config.project_id).then(setPersonaSets).catch(() => undefined);
  }, [config?.project_id, isAdmin]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setDebouncedEventSearch(eventSearch.trim());
    }, 300);
    return () => window.clearTimeout(timer);
  }, [eventSearch]);

  useEffect(() => {
    if (!isAdmin) return;
    if (tab === 'participants') {
      void studyApi.adminListParticipants(slug).then(setParticipants).catch((e) => setError(e.message));
    }
    if (tab === 'events') {
      void studyApi
        .adminListEvents(slug, debouncedEventSearch || undefined)
        .then(setEvents)
        .catch((e) => setError(e.message));
    }
  }, [tab, slug, debouncedEventSearch, isAdmin]);

  const selectedSet = useMemo(
    () => personaSets.find((s) => s.id === config?.persona_set_id),
    [personaSets, config?.persona_set_id]
  );

  if (!isAdmin) {
    return <Navigate to="/projects" replace />;
  }

  const onSave = async (e: FormEvent) => {
    e.preventDefault();
    if (!config) return;
    setSaving(true);
    setSavedMsg(null);
    setError(null);
    try {
      const updated = await studyApi.adminUpdateStudy(slug, {
        name: config.name,
        enabled: config.enabled,
        project_id: config.project_id,
        persona_set_id: config.persona_set_id,
        allow_open_codes: config.allow_open_codes,
        max_participants: config.max_participants,
        welcome_text: config.welcome_text,
        rebuild_rotations: true,
      });
      setConfig({
        name: updated.name,
        enabled: updated.enabled,
        project_id: updated.project_id ?? null,
        persona_set_id: updated.persona_set_id,
        allow_open_codes: updated.allow_open_codes,
        max_participants: updated.max_participants,
        welcome_text: updated.welcome_text || '',
        order_rotations: updated.order_rotations,
        persona_order: updated.persona_order,
      });
      setSavedMsg('Study settings saved. Participants will see the selected persona set.');
      const studyList = await studyApi.adminListStudies();
      setStudies(studyList);
    } catch (err: any) {
      setError(err?.response?.data?.detail || err.message || 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  const refreshAll = () => {
    setLoading(true);
    void studyApi
      .adminGetStudy(slug)
      .then(async (data) => {
        setConfig({
          name: data.name,
          enabled: data.enabled,
          project_id: data.project_id ?? null,
          persona_set_id: data.persona_set_id,
          allow_open_codes: data.allow_open_codes,
          max_participants: data.max_participants,
          welcome_text: data.welcome_text || '',
          order_rotations: data.order_rotations,
          persona_order: data.persona_order,
        });
        const [proj, studyList, sets] = await Promise.all([
          projectsApi.getAll(),
          studyApi.adminListStudies(),
          personasApi.getAllSets(data.project_id ?? undefined),
        ]);
        setProjects(proj);
        setStudies(studyList);
        setPersonaSets(sets);
        if (tab === 'participants') {
          setParticipants(await studyApi.adminListParticipants(slug));
        }
        if (tab === 'events') {
          setEvents(await studyApi.adminListEvents(slug, debouncedEventSearch || undefined));
        }
      })
      .catch((e: any) => setError(e?.response?.data?.detail || e.message || 'Refresh failed'))
      .finally(() => setLoading(false));
  };

  return (
    <div className="px-4 py-6 sm:px-0 max-w-5xl mx-auto">
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="flex items-center gap-2 text-stone-500 text-xs font-medium uppercase tracking-wide mb-1">
            <ClipboardList className="h-3.5 w-3.5" />
            Admin
          </div>
          <h2 className="text-3xl font-bold text-stone-900 mb-1">User study</h2>
          <p className="text-stone-600 text-sm">
            Choose the persona set, toggle the study, and inspect participant tracking.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <a
            href={studyEnterPath(slug)}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1.5 rounded-lg bg-stone-100 px-3 py-2 text-sm text-stone-900"
          >
            <ExternalLink className="h-4 w-4" />
            Open entry
          </a>
          <button
            type="button"
            onClick={() => void refreshAll()}
            className="inline-flex items-center gap-1.5 rounded-lg bg-stone-100 px-3 py-2 text-sm text-stone-900"
          >
            <RefreshCw className="h-4 w-4" />
            Refresh
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-4 rounded-lg bg-red-50 text-red-700 text-sm px-3 py-2 border border-red-100">
          {error}
        </div>
      )}
      {savedMsg && (
        <div className="mb-4 rounded-lg bg-green-50 text-green-800 text-sm px-3 py-2 border border-green-100">
          {savedMsg}
        </div>
      )}

      <div className="mb-4 flex flex-wrap items-center gap-3">
        <label className="text-sm text-stone-600">Study</label>
        <select
          value={slug}
          onChange={(e) => setSlug(e.target.value)}
          className="rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm"
        >
          {studies.map((s) => (
            <option key={s.slug} value={s.slug}>
              {s.name} ({s.slug}) {s.enabled ? '' : '— disabled'}
            </option>
          ))}
          {!studies.length && <option value={DEFAULT_STUDY_SLUG}>{DEFAULT_STUDY_SLUG}</option>}
        </select>
        <div className="inline-flex rounded-xl border border-stone-200 bg-white p-1">
          {(['config', 'participants', 'events'] as Tab[]).map((t) => (
            <button
              key={t}
              type="button"
              onClick={() => setTab(t)}
              className={`px-3 py-1.5 rounded-lg text-sm capitalize ${
                tab === t ? 'bg-stone-900 text-white' : 'text-stone-600'
              }`}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      {loading || !config ? (
        <div className="text-stone-500 text-sm py-10 text-center">Loading…</div>
      ) : tab === 'config' ? (
        <form onSubmit={onSave} className="glass-card rounded-2xl p-6 space-y-5">
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="block text-xs font-medium text-stone-500 mb-1">Name</label>
              <input
                value={config.name}
                onChange={(e) => setConfig({ ...config, name: e.target.value })}
                className="w-full rounded-xl border border-stone-200 px-3 py-2 text-sm"
              />
            </div>
            <div className="flex items-end gap-4">
              <label className="inline-flex items-center gap-2 text-sm text-stone-800">
                <input
                  type="checkbox"
                  checked={config.enabled}
                  onChange={(e) => setConfig({ ...config, enabled: e.target.checked })}
                />
                Enabled
              </label>
              <label className="inline-flex items-center gap-2 text-sm text-stone-800">
                <input
                  type="checkbox"
                  checked={config.allow_open_codes}
                  onChange={(e) => setConfig({ ...config, allow_open_codes: e.target.checked })}
                />
                Open codes (P01…)
              </label>
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="block text-xs font-medium text-stone-500 mb-1">Project</label>
              <select
                value={config.project_id ?? ''}
                onChange={(e) => {
                  const pid = e.target.value ? parseInt(e.target.value, 10) : null;
                  setConfig({ ...config, project_id: pid });
                }}
                className="w-full rounded-xl border border-stone-200 px-3 py-2 text-sm"
              >
                <option value="">Select project</option>
                {projects.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} (#{p.id})
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-stone-500 mb-1">
                Persona set (used in the study)
              </label>
              <select
                value={config.persona_set_id}
                onChange={(e) =>
                  setConfig({ ...config, persona_set_id: parseInt(e.target.value, 10) })
                }
                className="w-full rounded-xl border border-stone-200 px-3 py-2 text-sm"
              >
                {personaSets.map((s) => (
                  <option key={s.id} value={s.id}>
                    #{s.id} · {s.name} · {s.personas?.length || 0} personas
                  </option>
                ))}
              </select>
              {selectedSet && (
                <p className="mt-1.5 text-xs text-stone-500">
                  Personas:{' '}
                  {(selectedSet.personas || [])
                    .map((p) => p.persona_data?.name || p.name)
                    .join(', ') || '—'}
                </p>
              )}
              <p className="mt-1 text-xs text-stone-400">
                Saving with a new set rebuilds AH/HW/BISP order rotations when those groups exist.
              </p>
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-stone-500 mb-1">Max participants</label>
            <input
              type="number"
              min={1}
              max={500}
              value={config.max_participants}
              onChange={(e) =>
                setConfig({ ...config, max_participants: parseInt(e.target.value, 10) || 40 })
              }
              className="w-40 rounded-xl border border-stone-200 px-3 py-2 text-sm"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-stone-500 mb-1">Welcome text</label>
            <textarea
              value={config.welcome_text}
              onChange={(e) => setConfig({ ...config, welcome_text: e.target.value })}
              rows={4}
              className="w-full rounded-xl border border-stone-200 px-3 py-2 text-sm"
            />
          </div>

          <div className="rounded-xl bg-stone-50 border border-stone-100 p-3 text-xs text-stone-600 space-y-1">
            <div>
              Rotations:{' '}
              {config.order_rotations?.length
                ? `${config.order_rotations.length} (counterbalanced)`
                : 'none'}
            </div>
            <div>Fallback persona order IDs: {(config.persona_order || []).join(', ') || '—'}</div>
            <div>
              Participant URL:{' '}
              <Link className="underline" to={studyEnterPath(slug)}>
                {studyEnterPath(slug)}
              </Link>
            </div>
          </div>

          <button
            type="submit"
            disabled={saving}
            className="inline-flex items-center gap-2 rounded-xl bg-stone-900 px-4 py-2.5 text-sm text-white disabled:opacity-50"
          >
            <Save className="h-4 w-4" />
            {saving ? 'Saving…' : 'Save study settings'}
          </button>
        </form>
      ) : tab === 'participants' ? (
        <div className="glass-card rounded-2xl overflow-hidden">
          <div className="px-4 py-3 border-b border-stone-200 text-sm text-stone-600">
            {participants.length} participant{participants.length === 1 ? '' : 's'}
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-stone-50 text-left text-xs text-stone-500 uppercase">
                <tr>
                  <th className="px-4 py-2">Code</th>
                  <th className="px-4 py-2">Events</th>
                  <th className="px-4 py-2">Last seen</th>
                  <th className="px-4 py-2">Type</th>
                  <th className="px-4 py-2" />
                </tr>
              </thead>
              <tbody>
                {participants.map((p) => (
                  <tr key={p.id} className="border-t border-stone-100">
                    <td className="px-4 py-2 font-mono font-medium text-stone-900">{p.code}</td>
                    <td className="px-4 py-2 text-stone-700">{p.event_count}</td>
                    <td className="px-4 py-2 text-stone-500">
                      {p.last_seen_at ? new Date(p.last_seen_at).toLocaleString() : '—'}
                    </td>
                    <td className="px-4 py-2 text-stone-500">{p.is_test ? 'test' : 'real'}</td>
                    <td className="px-4 py-2">
                      <button
                        type="button"
                        className="text-xs text-stone-600 underline"
                        onClick={() => {
                          setEventSearch(p.code);
                          setTab('events');
                        }}
                      >
                        View events
                      </button>
                    </td>
                  </tr>
                ))}
                {!participants.length && (
                  <tr>
                    <td colSpan={5} className="px-4 py-8 text-center text-stone-400">
                      No participants yet
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div className="space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <input
              type="search"
              value={eventSearch}
              onChange={(e) => setEventSearch(e.target.value)}
              placeholder="Search events — code, type, path, message, sim id…"
              className="min-w-[16rem] flex-1 rounded-xl border border-stone-200 px-3 py-2 text-sm"
            />
            <button
              type="button"
              onClick={() => setEventSearch('')}
              className="text-xs text-stone-500 underline"
            >
              Clear
            </button>
            <span className="text-xs text-stone-400">
              {debouncedEventSearch
                ? `${events.length} match${events.length === 1 ? '' : 'es'} for “${debouncedEventSearch}”`
                : `Showing ${events.length} recent events`}
            </span>
          </div>
          <div className="glass-card rounded-2xl overflow-hidden max-h-[70vh] overflow-y-auto">
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-stone-50 text-left text-xs text-stone-500 uppercase">
                <tr>
                  <th className="px-3 py-2">When</th>
                  <th className="px-3 py-2">Participant</th>
                  <th className="px-3 py-2">Event</th>
                  <th className="px-3 py-2">Summary</th>
                  <th className="px-3 py-2">Details</th>
                </tr>
              </thead>
              <tbody>
                {events.map((ev) => {
                  const p = ev.payload || {};
                  const duration =
                    typeof p.duration_seconds === 'number'
                      ? `${p.duration_seconds}s`
                      : null;
                  const summaryBits = [
                    duration ? `dwell ${duration}` : null,
                    typeof p.user_message === 'string'
                      ? `msg: ${String(p.user_message).slice(0, 80)}`
                      : null,
                    typeof p.message === 'string'
                      ? `intervention: ${String(p.message).slice(0, 80)}`
                      : null,
                    typeof p.content === 'string'
                      ? `turn: ${String(p.content).slice(0, 80)}`
                      : null,
                    p.persona_name ? `persona: ${p.persona_name}` : null,
                    p.persona_id != null ? `persona_id=${p.persona_id}` : null,
                    p.simulation_id != null ? `sim=${p.simulation_id}` : null,
                    p.session_id != null ? `chat=${p.session_id}` : null,
                    ev.path || null,
                  ].filter(Boolean);

                  return (
                    <tr key={ev.id} className="border-t border-stone-100 align-top">
                      <td className="px-3 py-2 text-xs text-stone-500 whitespace-nowrap">
                        {ev.created_at ? new Date(ev.created_at).toLocaleString() : '—'}
                      </td>
                      <td className="px-3 py-2 text-xs">
                        <div className="font-mono font-medium text-stone-900">
                          {ev.participant_code ||
                            (typeof p.participant_code === 'string'
                              ? p.participant_code
                              : '—')}
                        </div>
                        <div className="text-stone-400">
                          user #{ev.user_id ?? (typeof p.user_id === 'number' ? p.user_id : '—')}
                          {ev.participant_id != null ? ` · pid ${ev.participant_id}` : ''}
                        </div>
                      </td>
                      <td className="px-3 py-2 font-medium text-stone-900 whitespace-nowrap">
                        {ev.event_type}
                      </td>
                      <td className="px-3 py-2 text-xs text-stone-600 max-w-xs">
                        {summaryBits.length ? summaryBits.join(' · ') : '—'}
                      </td>
                      <td className="px-3 py-2 text-xs text-stone-500">
                        {ev.payload && Object.keys(ev.payload).length > 0 ? (
                          <details>
                            <summary className="cursor-pointer text-stone-600 underline">
                              payload
                            </summary>
                            <pre className="mt-1 max-w-md whitespace-pre-wrap break-all text-[11px] text-stone-400">
                              {JSON.stringify(ev.payload, null, 2)}
                            </pre>
                          </details>
                        ) : (
                          '—'
                        )}
                      </td>
                    </tr>
                  );
                })}
                {!events.length && (
                  <tr>
                    <td colSpan={5} className="px-4 py-8 text-center text-stone-400">
                      No events
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
