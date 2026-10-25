import { Loader2, MessageSquare, SkipForward } from 'lucide-react';
import type { SimulationMessage } from '../../types';
import type { NodeSelection } from './lineage';

interface PlaygroundDetailsProps {
  goal: string;
  goalContext?: string;
  selected: NodeSelection;
  selectedMessage: SimulationMessage | null;
  crumbs: SimulationMessage[];
  pathClosed: boolean;
  running: boolean;
  intervening: boolean;
  interventionText: string;
  onInterventionText: (value: string) => void;
  onIntervene: () => void;
  onNextTurn: () => void;
  compareArmed: boolean;
  onArmCompare: () => void;
}

export default function PlaygroundDetails({
  goal,
  goalContext,
  selected,
  selectedMessage,
  crumbs,
  pathClosed,
  running,
  intervening,
  interventionText,
  onInterventionText,
  onIntervene,
  onNextTurn,
  compareArmed,
  onArmCompare,
}: PlaygroundDetailsProps) {
  const human = !!selectedMessage && (selectedMessage.is_human_message || selectedMessage.persona_id == null);
  const title = selected === 'root'
    ? 'Goal'
    : human
      ? 'Facilitator'
      : selectedMessage?.persona_name || 'Message';

  return (
    <aside className="glass-card flex flex-col rounded-2xl p-4">
      <div className="text-xs font-semibold uppercase tracking-wide text-stone-400">Details</div>
      <h3 className="mt-1 text-base font-semibold text-stone-900">{title}</h3>
      {crumbs.length > 0 && (
        <p className="mt-1 text-xs leading-relaxed text-stone-500">
          {crumbs.map((message) => (message.is_human_message || message.persona_id == null ? 'Facilitator' : message.persona_name)).join(' → ')}
        </p>
      )}
      <p className="mt-3 whitespace-pre-wrap text-sm leading-relaxed text-stone-800">
        {selected === 'root' ? goal : selectedMessage?.content}
      </p>
      {selected === 'root' && goalContext && (
        <p className="mt-2 text-xs leading-relaxed text-stone-500">{goalContext}</p>
      )}
      {pathClosed && (
        <p className="mt-3 text-xs text-stone-500">
          This path is closed. Pick an earlier node to branch.
        </p>
      )}

      <div className="mt-4 space-y-3 border-t border-stone-200 pt-4">
        <button
          type="button"
          onClick={onNextTurn}
          disabled={running || pathClosed}
          className="inline-flex w-full items-center justify-center gap-1.5 rounded-xl bg-stone-900 px-3 py-2.5 text-sm font-medium text-white disabled:opacity-50"
        >
          {running ? <Loader2 className="h-4 w-4 animate-spin" /> : <SkipForward className="h-4 w-4" />}
          Continue this path
        </button>
        <div>
          <label className="mb-1.5 block text-xs font-medium text-stone-600" htmlFor="path-intervention">
            Speak from this point
          </label>
          <textarea
            id="path-intervention"
            value={interventionText}
            onChange={(event) => onInterventionText(event.target.value)}
            placeholder="Ask one persona, or add a constraint the cast has to answer."
            rows={3}
            disabled={intervening || running || pathClosed}
            className="w-full rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-900 placeholder:text-stone-400 focus:outline-none focus:ring-2 focus:ring-amber-400 disabled:opacity-50"
          />
          <p className="mt-1.5 text-xs leading-relaxed text-stone-500">
            If this turn already continues, speaking here opens a new branch. The earlier continuation stays on the map.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={onIntervene}
            disabled={intervening || running || pathClosed || !interventionText.trim()}
            className="inline-flex items-center gap-1.5 rounded-xl bg-amber-100 px-3 py-2 text-sm font-medium text-amber-900 disabled:opacity-50"
          >
            {intervening || running ? <Loader2 className="h-4 w-4 animate-spin" /> : <MessageSquare className="h-4 w-4" />}
            Add and branch
          </button>
          <button
            type="button"
            onClick={onArmCompare}
            disabled={selected === 'root'}
            className={`rounded-xl px-3 py-2 text-sm font-medium ${
              compareArmed ? 'bg-blue-100 text-blue-800' : 'bg-stone-100 text-stone-800'
            } disabled:opacity-50`}
          >
            {compareArmed ? 'Now click the other path' : 'Compare'}
          </button>
        </div>
      </div>
    </aside>
  );
}
