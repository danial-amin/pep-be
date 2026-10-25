import type { SimulationMessage } from '../../types';

interface PathChatProps {
  messages: SimulationMessage[];
}

export default function PathChat({ messages }: PathChatProps) {
  return (
    <div className="glass-card max-h-72 overflow-y-auto rounded-2xl p-4">
      <h4 className="mb-3 text-sm font-semibold text-stone-900">Path chat</h4>
      {messages.length === 0 ? (
        <p className="text-sm text-stone-500">The goal is the root. Continue to hear the first persona, or branch with an intervention.</p>
      ) : (
        <ol className="space-y-3">
          {messages.map((message) => {
            const human = message.is_human_message || message.persona_id == null;
            return (
              <li
                key={message.id}
                className={`rounded-xl px-3 py-2 text-sm ${
                  human ? 'border border-amber-200 bg-amber-50' : 'border border-stone-200 bg-white'
                }`}
              >
                <div className="mb-1 flex items-center gap-2 text-xs text-stone-500">
                  <span className="font-semibold text-stone-800">
                    {human ? 'Facilitator' : message.persona_name}
                  </span>
                  <span>Turn {message.turn_number}</span>
                </div>
                <p className="whitespace-pre-wrap leading-relaxed text-stone-800">{message.content}</p>
              </li>
            );
          })}
        </ol>
      )}
    </div>
  );
}
