import { useState } from 'react';
import type { SimulationMessage, SimulationParticipant } from '../../types';
import { getPersonaImageUrl } from '../../utils/imageUtils';
import type { NodeSelection } from './lineage';

interface PathChatProps {
  messages: SimulationMessage[];
  participants: SimulationParticipant[];
  selectedId: NodeSelection;
  onSelect: (id: NodeSelection) => void;
}

function SpeakerMark({
  name,
  imageUrl,
  personaId,
}: {
  name: string;
  imageUrl?: string | null;
  personaId?: number | null;
}) {
  const [failed, setFailed] = useState(false);
  const src = getPersonaImageUrl(imageUrl, personaId ?? undefined);
  if (src && !failed) {
    return <img src={src} alt="" className="h-8 w-8 rounded-full object-cover" onError={() => setFailed(true)} />;
  }
  return (
    <span className="flex h-8 w-8 items-center justify-center rounded-full bg-stone-200 text-xs font-semibold text-stone-600">
      {name.charAt(0).toUpperCase()}
    </span>
  );
}

export default function PathChat({ messages, participants, selectedId, onSelect }: PathChatProps) {
  const byPersona = new Map(participants.map((participant) => [participant.persona_id, participant]));

  return (
    <div className="glass-card rounded-2xl p-4">
      <div className="mb-3 flex items-baseline justify-between gap-3">
        <h4 className="text-sm font-semibold text-stone-900">Discussion</h4>
        <span className="text-xs text-stone-400">
          {messages.length === 0 ? 'Nothing said yet' : `${messages.length} on this path`}
        </span>
      </div>
      <div className="mb-3 flex gap-1.5 overflow-x-auto pb-1">
        <button
          type="button"
          onClick={() => onSelect('root')}
          className={`shrink-0 rounded-full px-2.5 py-1 text-xs ${
            selectedId === 'root' ? 'bg-stone-900 text-white' : 'bg-stone-100 text-stone-700'
          }`}
        >
          Goal
        </button>
        {messages.map((message) => {
          const human = message.is_human_message || message.persona_id == null;
          const label = human ? 'Facilitator' : message.persona_name;
          return (
            <button
              key={message.id}
              type="button"
              onClick={() => onSelect(message.id)}
              className={`max-w-[9rem] shrink-0 truncate rounded-full px-2.5 py-1 text-xs ${
                selectedId === message.id ? 'bg-stone-900 text-white' : 'bg-stone-100 text-stone-700'
              }`}
            >
              {label}
            </button>
          );
        })}
      </div>
      {messages.length === 0 ? (
        <p className="text-sm leading-relaxed text-stone-500">
          The goal is the root. Continue to hear the first persona, or speak first and the cast answers from there.
        </p>
      ) : (
        <ol className="max-h-[32rem] space-y-3 overflow-y-auto pr-1">
          {messages.map((message) => {
            const human = message.is_human_message || message.persona_id == null;
            const speaker = human ? 'Facilitator' : message.persona_name;
            const participant = message.persona_id != null ? byPersona.get(message.persona_id) : undefined;
            const active = selectedId === message.id;
            return (
              <li key={message.id}>
                <button
                  type="button"
                  onClick={() => onSelect(message.id)}
                  className={`flex w-full gap-3 rounded-xl px-3 py-3 text-left ${
                    active
                      ? 'bg-stone-100'
                      : human
                        ? 'bg-amber-50'
                        : 'hover:bg-stone-50'
                  }`}
                >
                  <SpeakerMark
                    name={speaker}
                    imageUrl={participant?.persona_image_url}
                    personaId={message.persona_id}
                  />
                  <span className="min-w-0 flex-1">
                    <span className="mb-1 flex items-center gap-2 text-xs text-stone-500">
                      <span className="font-semibold text-stone-900">{speaker}</span>
                      <span>Round {message.turn_number}</span>
                    </span>
                    <span className="block whitespace-pre-wrap text-sm leading-relaxed text-stone-800">{message.content}</span>
                  </span>
                </button>
              </li>
            );
          })}
        </ol>
      )}
    </div>
  );
}
