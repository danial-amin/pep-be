import { useMemo, useState } from 'react';
import { Check, ChevronDown, ChevronRight, Loader2, Play, Users } from 'lucide-react';
import type { Persona, PersonaSet } from '../../types';
import { getPersonaImageUrl } from '../../utils/imageUtils';

const STEPS = [
  { id: 'brief', label: 'Brief' },
  { id: 'cast', label: 'Cast' },
  { id: 'rules', label: 'Rules' },
] as const;

interface PlaygroundSetupProps {
  name: string;
  goal: string;
  goalContext: string;
  maxTurns: number;
  runUntilAgreement: boolean;
  agreementThreshold: number;
  personaSets: PersonaSet[];
  expandedSetIds: Set<number>;
  selectedPersonas: Map<number, string>;
  loading: boolean;
  useStudyDefaults: boolean;
  participantCode?: string | null;
  studyOrderNote: boolean;
  onName: (value: string) => void;
  onGoal: (value: string) => void;
  onGoalContext: (value: string) => void;
  onMaxTurns: (value: number) => void;
  onRunUntilAgreement: (value: boolean) => void;
  onAgreementThreshold: (value: number) => void;
  onToggleSet: (setId: number) => void;
  onTogglePersona: (personaId: number) => void;
  onRoleChange: (personaId: number, role: string) => void;
  onCreate: () => void;
}

function initials(name: string): string {
  return (name.trim().charAt(0) || '?').toUpperCase();
}

function PersonaMark({ persona }: { persona: Persona }) {
  const [failed, setFailed] = useState(false);
  const src = getPersonaImageUrl(persona.image_url, persona.id);
  if (src && !failed) {
    return (
      <img
        src={src}
        alt=""
        className="h-10 w-10 rounded-full object-cover"
        onError={() => setFailed(true)}
      />
    );
  }
  return (
    <div className="flex h-10 w-10 items-center justify-center rounded-full bg-stone-200 text-sm font-semibold text-stone-600">
      {initials(persona.persona_data?.name || persona.name)}
    </div>
  );
}

export default function PlaygroundSetup({
  name,
  goal,
  goalContext,
  maxTurns,
  runUntilAgreement,
  agreementThreshold,
  personaSets,
  expandedSetIds,
  selectedPersonas,
  loading,
  useStudyDefaults,
  participantCode,
  studyOrderNote,
  onName,
  onGoal,
  onGoalContext,
  onMaxTurns,
  onRunUntilAgreement,
  onAgreementThreshold,
  onToggleSet,
  onTogglePersona,
  onRoleChange,
  onCreate,
}: PlaygroundSetupProps) {
  const [step, setStep] = useState(0);
  const [query, setQuery] = useState('');

  const personasById = useMemo(() => {
    const map = new Map<number, Persona>();
    for (const set of personaSets) {
      for (const persona of set.personas) map.set(persona.id, persona);
    }
    return map;
  }, [personaSets]);

  const seated = useMemo(
    () =>
      Array.from(selectedPersonas.keys())
        .map((id) => personasById.get(id))
        .filter((persona): persona is Persona => !!persona),
    [personasById, selectedPersonas],
  );

  const needle = query.trim().toLowerCase();
  const canLeaveBrief = goal.trim().length > 0;
  const canLeaveCast = selectedPersonas.size >= 2;

  return (
    <div className="glass-card rounded-2xl p-6">
      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h3 className="text-xl font-semibold text-stone-900">New playground</h3>
          <p className="mt-1 max-w-xl text-sm leading-relaxed text-stone-500">
            Write the brief, seat who speaks, then set how far one path can run. After it starts, any earlier turn can fork without erasing the others.
          </p>
        </div>
        <ol className="flex items-center gap-2">
          {STEPS.map((item, index) => {
            const active = index === step;
            const done = index < step;
            return (
              <li key={item.id} className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => {
                    if (index < step) setStep(index);
                  }}
                  disabled={index > step}
                  className={`flex items-center gap-2 rounded-full px-3 py-1 text-sm ${
                    active
                      ? 'bg-stone-900 text-white'
                      : done
                        ? 'bg-stone-100 text-stone-800'
                        : 'text-stone-400'
                  }`}
                >
                  <span className="text-xs tabular-nums">{index + 1}</span>
                  {item.label}
                </button>
                {index < STEPS.length - 1 && <span className="h-px w-4 bg-stone-200" />}
              </li>
            );
          })}
        </ol>
      </div>

      {step === 0 && (
        <div className="space-y-4">
          <div>
            <label className="mb-2 block text-sm font-medium text-stone-700" htmlFor="playground-name">
              Name
            </label>
            <input
              id="playground-name"
              type="text"
              value={name}
              onChange={(event) => onName(event.target.value)}
              placeholder="Product strategy, week 3"
              className="w-full rounded-xl border border-stone-200 bg-white px-4 py-2 text-stone-900 placeholder:text-stone-400 focus:border-stone-400 focus:outline-none focus:ring-2 focus:ring-stone-900/20"
            />
          </div>
          <div>
            <label className="mb-2 block text-sm font-medium text-stone-700" htmlFor="playground-goal">
              Goal
            </label>
            <textarea
              id="playground-goal"
              value={goal}
              onChange={(event) => onGoal(event.target.value)}
              placeholder="What should this room try to decide or explore?"
              rows={useStudyDefaults ? 4 : 3}
              className="w-full rounded-xl border border-stone-200 bg-white px-4 py-2 text-stone-900 placeholder:text-stone-400 focus:border-stone-400 focus:outline-none focus:ring-2 focus:ring-stone-900/20"
            />
          </div>
          <div>
            <label className="mb-2 block text-sm font-medium text-stone-700" htmlFor="playground-context">
              Context {useStudyDefaults ? '' : '(optional)'}
            </label>
            <textarea
              id="playground-context"
              value={goalContext}
              onChange={(event) => onGoalContext(event.target.value)}
              placeholder="Constraints, facts, or the question you want kept in view."
              rows={useStudyDefaults ? 10 : 4}
              className="w-full rounded-xl border border-stone-200 bg-white px-4 py-2 text-stone-900 placeholder:text-stone-400 focus:border-stone-400 focus:outline-none focus:ring-2 focus:ring-stone-900/20"
            />
            {useStudyDefaults && (
              <p className="mt-1.5 text-xs text-stone-500">
                Prefilled for study code {participantCode}. You can edit it.
              </p>
            )}
          </div>
        </div>
      )}

      {step === 1 && (
        <div>
          <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h4 className="flex items-center gap-2 text-sm font-medium text-stone-800">
                <Users className="h-4 w-4" />
                Seat 2–12 personas
              </h4>
              <p className="mt-1 text-xs text-stone-500">
                {studyOrderNote
                  ? 'Speaking order follows this participant’s assigned rotation.'
                  : 'Speaking order follows the order you select them.'}
              </p>
            </div>
            <span className="text-sm tabular-nums text-stone-500">{selectedPersonas.size} seated</span>
          </div>

          {seated.length > 0 && (
            <ol className="mb-4 flex gap-2 overflow-x-auto pb-1">
              {seated.map((persona, index) => (
                <li
                  key={persona.id}
                  className="flex shrink-0 items-center gap-2 rounded-full border border-stone-200 bg-stone-50 py-1 pl-1 pr-3"
                >
                  <span className="flex h-6 w-6 items-center justify-center rounded-full bg-stone-900 text-[11px] text-white">
                    {index + 1}
                  </span>
                  <span className="max-w-[10rem] truncate text-sm text-stone-800">
                    {persona.persona_data?.name || persona.name}
                  </span>
                </li>
              ))}
            </ol>
          )}

          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Find a persona"
            className="mb-3 w-full rounded-xl border border-stone-200 bg-white px-4 py-2 text-sm text-stone-900 placeholder:text-stone-400 focus:border-stone-400 focus:outline-none focus:ring-2 focus:ring-stone-900/20"
          />

          {personaSets.length === 0 ? (
            <p className="text-sm text-stone-400">No persona sets found.</p>
          ) : (
            <div className="max-h-[460px] space-y-3 overflow-y-auto pr-1">
              {personaSets.map((set) => {
                const visible = needle
                  ? set.personas.filter((persona) =>
                      (persona.persona_data?.name || persona.name).toLowerCase().includes(needle),
                    )
                  : set.personas;
                if (needle && visible.length === 0) return null;
                const open = expandedSetIds.has(set.id) || needle.length > 0;
                const selectedInSet = set.personas.filter((persona) => selectedPersonas.has(persona.id)).length;
                return (
                  <div key={set.id} className="overflow-hidden rounded-xl border border-stone-200">
                    <button
                      type="button"
                      onClick={() => onToggleSet(set.id)}
                      className="flex w-full items-center justify-between bg-stone-50 px-4 py-3 text-left"
                    >
                      <span className="text-sm font-medium text-stone-900">
                        {set.name}
                        <span className="ml-2 font-normal text-stone-400">{visible.length}</span>
                        {selectedInSet > 0 && (
                          <span className="ml-2 rounded-full bg-stone-900 px-2 py-0.5 text-xs font-normal text-white">
                            {selectedInSet} seated
                          </span>
                        )}
                      </span>
                      {open ? <ChevronDown className="h-4 w-4 text-stone-400" /> : <ChevronRight className="h-4 w-4 text-stone-400" />}
                    </button>
                    {open && (
                      <div className="grid grid-cols-1 gap-3 p-3 sm:grid-cols-2">
                        {visible.map((persona) => {
                          const selected = selectedPersonas.has(persona.id);
                          const role = selectedPersonas.get(persona.id) || '';
                          const label = persona.persona_data?.name || persona.name;
                          const occupation = persona.persona_data?.demographics?.occupation;
                          return (
                            <div
                              key={persona.id}
                              className={`rounded-xl border-2 p-3 ${
                                selected ? 'border-stone-900 bg-stone-50' : 'border-stone-200 bg-white'
                              }`}
                            >
                              <button
                                type="button"
                                onClick={() => onTogglePersona(persona.id)}
                                className="flex w-full items-center gap-3 text-left"
                              >
                                <PersonaMark persona={persona} />
                                <span className="min-w-0 flex-1">
                                  <span className="block truncate font-medium text-stone-900">{label}</span>
                                  <span className="block truncate text-sm text-stone-500">{occupation || 'No occupation'}</span>
                                </span>
                                <span
                                  className={`flex h-6 w-6 items-center justify-center rounded-full ${
                                    selected ? 'bg-stone-900 text-white' : 'bg-stone-100 text-transparent'
                                  }`}
                                >
                                  <Check className="h-3.5 w-3.5" />
                                </span>
                              </button>
                              {selected && (
                                <input
                                  type="text"
                                  value={role}
                                  onChange={(event) => onRoleChange(persona.id, event.target.value)}
                                  placeholder="Role in this room, optional"
                                  className="mt-3 w-full rounded-lg border border-stone-200 bg-white px-3 py-2 text-sm text-stone-900 placeholder:text-stone-400 focus:outline-none focus:ring-2 focus:ring-stone-900/20"
                                />
                              )}
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {step === 2 && (
        <div className="space-y-5">
          <div className="rounded-xl border border-stone-200 bg-stone-50 p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-stone-400">This playground</p>
            <p className="mt-1 font-medium text-stone-900">{name.trim() || 'Untitled playground'}</p>
            <p className="mt-1 line-clamp-3 text-sm leading-relaxed text-stone-600">{goal}</p>
            <p className="mt-2 text-sm text-stone-500">
              {seated.length} seated
              {seated.length > 0 ? ` · ${seated.map((persona) => persona.persona_data?.name || persona.name).slice(0, 4).join(', ')}` : ''}
              {seated.length > 4 ? ` +${seated.length - 4}` : ''}
            </p>
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-stone-700" htmlFor="playground-turns">
              Rounds on one path
            </label>
            <select
              id="playground-turns"
              value={maxTurns}
              onChange={(event) => onMaxTurns(parseInt(event.target.value, 10))}
              className="w-full rounded-xl border border-stone-200 bg-white px-4 py-2 text-stone-900 focus:border-stone-400 focus:outline-none focus:ring-2 focus:ring-stone-900/20"
            >
              {[5, 10, 15, 20, 30, 50].map((turns) => (
                <option key={turns} value={turns}>
                  {turns} rounds
                </option>
              ))}
            </select>
            <p className="mt-2 text-xs leading-relaxed text-stone-500">
              One round is every seated persona speaking once. When a path reaches this limit it closes. Other branches stay open, and you can still fork from an earlier turn.
            </p>
          </div>

          <div className="rounded-xl border border-stone-200 p-4">
            <label className="flex cursor-pointer items-start gap-3">
              <input
                type="checkbox"
                checked={runUntilAgreement}
                onChange={(event) => onRunUntilAgreement(event.target.checked)}
                className="mt-1 accent-stone-900"
              />
              <span>
                <span className="block text-sm font-medium text-stone-900">Close a path when it reaches agreement</span>
                <span className="mt-0.5 block text-xs text-stone-500">
                  The limit above still applies. Agreement closes only the path that was scored.
                </span>
              </span>
            </label>
            {runUntilAgreement && (
              <div className="mt-4">
                <label className="mb-2 block text-sm text-stone-600" htmlFor="playground-threshold">
                  Agreement threshold {(agreementThreshold * 100).toFixed(0)}%
                </label>
                <input
                  id="playground-threshold"
                  type="range"
                  min={0.1}
                  max={1}
                  step={0.05}
                  value={agreementThreshold}
                  onChange={(event) => onAgreementThreshold(parseFloat(event.target.value))}
                  className="w-full accent-stone-900"
                />
                <div className="mt-1 flex justify-between text-xs text-stone-400">
                  <span>10%</span>
                  <span>100%</span>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      <div className="mt-6 flex items-center justify-between gap-3 border-t border-stone-200 pt-4">
        <button
          type="button"
          onClick={() => setStep((current) => Math.max(0, current - 1))}
          disabled={step === 0 || loading}
          className="rounded-xl px-4 py-2 text-sm font-medium text-stone-600 disabled:opacity-40"
        >
          Back
        </button>
        {step < 2 ? (
          <button
            type="button"
            onClick={() => setStep((current) => current + 1)}
            disabled={(step === 0 && !canLeaveBrief) || (step === 1 && !canLeaveCast)}
            className="rounded-xl bg-stone-900 px-5 py-2 text-sm font-medium text-white disabled:opacity-40"
          >
            Continue
          </button>
        ) : (
          <button
            type="button"
            onClick={onCreate}
            disabled={loading || !canLeaveBrief || !canLeaveCast}
            className="inline-flex items-center gap-2 rounded-xl bg-stone-900 px-5 py-2 text-sm font-medium text-white disabled:opacity-40"
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
            {loading ? 'Creating…' : 'Open playground'}
          </button>
        )}
      </div>
    </div>
  );
}
