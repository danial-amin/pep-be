import type { AgreementEvaluation, SimulationMessage } from '../../types';
import { agreementForHead, lineageOf } from './lineage';

interface BranchCompareProps {
  messages: SimulationMessage[];
  leftId: number;
  rightId: number;
  evaluations: AgreementEvaluation[];
  onClose: () => void;
}

function Column({
  title,
  messages,
  evaluation,
}: {
  title: string;
  messages: SimulationMessage[];
  evaluation?: AgreementEvaluation;
}) {
  return (
    <div className="min-w-0 flex-1 rounded-xl border border-stone-200 bg-white p-4">
      <h5 className="text-sm font-semibold text-stone-900">{title}</h5>
      {evaluation ? (
        <p className="mt-1 text-xs text-stone-600">
          Agreement {(evaluation.overall_agreement_score * 100).toFixed(0)}%
          {evaluation.agreement_reached ? ' · threshold met' : ''}
        </p>
      ) : (
        <p className="mt-1 text-xs text-stone-400">No agreement snapshot on this node.</p>
      )}
      {evaluation?.persona_stances && (
        <ul className="mt-2 space-y-1">
          {Object.entries(evaluation.persona_stances).map(([id, stance]) => (
            <li key={id} className="text-xs text-stone-600">
              {stance.persona_name}: drift {(stance.drift_score * 100).toFixed(0)}%
            </li>
          ))}
        </ul>
      )}
      <ol className="mt-3 max-h-64 space-y-2 overflow-y-auto">
        {messages.map((message) => {
          const human = message.is_human_message || message.persona_id == null;
          return (
            <li key={message.id} className="text-sm text-stone-800">
              <span className="font-medium">{human ? 'Facilitator' : message.persona_name}: </span>
              {message.content}
            </li>
          );
        })}
      </ol>
    </div>
  );
}

export default function BranchCompare({
  messages,
  leftId,
  rightId,
  evaluations,
  onClose,
}: BranchCompareProps) {
  const left = lineageOf(messages, leftId);
  const right = lineageOf(messages, rightId);
  const leftHead = left[left.length - 1];
  const rightHead = right[right.length - 1];

  return (
    <div className="glass-card rounded-2xl p-4">
      <div className="mb-3 flex items-center justify-between">
        <h4 className="text-sm font-semibold text-stone-900">Compare paths</h4>
        <button type="button" onClick={onClose} className="text-xs text-stone-500 hover:text-stone-900">
          Close
        </button>
      </div>
      <div className="flex flex-col gap-3 md:flex-row">
        <Column
          title={leftHead ? `${leftHead.persona_name} · turn ${leftHead.turn_number}` : 'Path A'}
          messages={left}
          evaluation={agreementForHead(evaluations, leftId)}
        />
        <Column
          title={rightHead ? `${rightHead.persona_name} · turn ${rightHead.turn_number}` : 'Path B'}
          messages={right}
          evaluation={agreementForHead(evaluations, rightId)}
        />
      </div>
    </div>
  );
}
