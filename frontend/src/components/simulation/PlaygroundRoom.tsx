import { useState } from 'react';
import { getPersonaImageUrl } from '../../utils/imageUtils';

export interface HallSeat {
  id: number;
  name: string;
  imageUrl?: string | null;
  role?: string;
  speaking?: boolean;
}

interface PlaygroundRoomProps {
  title?: string;
  goal: string;
  seats: HallSeat[];
  floorName?: string;
  floorText?: string;
  facilitatorSpeaking?: boolean;
  running?: boolean;
  compact?: boolean;
  onSeat?: (id: number) => void;
}

function Mark({ name, imageUrl, personaId, hot }: { name: string; imageUrl?: string | null; personaId?: number; hot?: boolean }) {
  const [failed, setFailed] = useState(false);
  const src = getPersonaImageUrl(imageUrl, personaId);
  const ring = hot ? 'ring-2 ring-stone-900 ring-offset-2' : 'ring-1 ring-stone-200';
  if (src && !failed) {
    return (
      <img
        src={src}
        alt=""
        className={`h-12 w-12 rounded-full object-cover ${ring}`}
        onError={() => setFailed(true)}
      />
    );
  }
  return (
    <span className={`flex h-12 w-12 items-center justify-center rounded-full bg-stone-200 text-sm font-semibold text-stone-700 ${ring}`}>
      {(name.trim().charAt(0) || '?').toUpperCase()}
    </span>
  );
}

function place(index: number, total: number): { left: string; top: string } {
  const angle = -Math.PI / 2 + (index / Math.max(total, 1)) * Math.PI * 2;
  const x = 50 + Math.cos(angle) * 38;
  const y = 44 + Math.sin(angle) * 30;
  return { left: `${x}%`, top: `${y}%` };
}

export default function PlaygroundRoom({
  title = 'The hall',
  goal,
  seats,
  floorName,
  floorText,
  facilitatorSpeaking = false,
  running = false,
  compact = false,
  onSeat,
}: PlaygroundRoomProps) {
  return (
    <section className={`relative overflow-hidden rounded-2xl border border-stone-200 bg-[#f4f1ea] ${compact ? 'h-64' : 'h-[460px]'}`}>
      <div className="absolute left-4 top-4 z-10">
        <p className="text-[11px] font-semibold uppercase tracking-wide text-stone-400">{title}</p>
        <p className="mt-0.5 max-w-xs text-sm text-stone-700">{running ? 'Someone has the floor' : 'One seat speaks at a time'}</p>
      </div>

      <div className="absolute left-1/2 top-1/2 z-10 w-[min(280px,46%)] -translate-x-1/2 -translate-y-1/2 rounded-2xl border border-stone-300 bg-white px-4 py-3 text-center shadow-none">
        <p className="text-[10px] font-semibold uppercase tracking-wide text-stone-400">Floor</p>
        <p className="mt-1 line-clamp-2 text-sm font-medium text-stone-900">{goal || 'The agenda is empty'}</p>
        {floorName && (
          <p className="mt-2 text-xs font-semibold text-stone-800">{floorName}</p>
        )}
        {floorText && (
          <p className="mt-1 line-clamp-3 text-xs leading-relaxed text-stone-600">{floorText}</p>
        )}
      </div>

      {seats.map((seat, index) => {
        const at = place(index, seats.length);
        const body = (
          <>
            <Mark name={seat.name} imageUrl={seat.imageUrl} personaId={seat.id} hot={seat.speaking} />
            <span className="mt-1 max-w-[6.5rem] truncate text-[11px] font-medium text-stone-800">{seat.name}</span>
            {seat.role && <span className="max-w-[6.5rem] truncate text-[10px] text-stone-400">{seat.role}</span>}
            {seat.speaking && <span className="text-[10px] font-semibold uppercase tracking-wide text-stone-900">Speaking</span>}
          </>
        );
        const className = 'absolute flex w-24 -translate-x-1/2 -translate-y-1/2 flex-col items-center';
        if (!onSeat) {
          return (
            <div key={seat.id} className={className} style={at}>
              {body}
            </div>
          );
        }
        return (
          <button key={seat.id} type="button" className={className} style={at} onClick={() => onSeat(seat.id)}>
            {body}
          </button>
        );
      })}

      <div className="absolute bottom-4 left-1/2 z-10 flex -translate-x-1/2 flex-col items-center">
        <span className={`flex h-11 w-11 items-center justify-center rounded-full bg-amber-100 text-sm font-semibold text-amber-900 ${facilitatorSpeaking ? 'ring-2 ring-stone-900 ring-offset-2' : 'ring-1 ring-amber-200'}`}>
          You
        </span>
        <span className="mt-1 text-[11px] font-medium text-stone-700">Facilitator</span>
        {facilitatorSpeaking && <span className="text-[10px] font-semibold uppercase tracking-wide text-stone-900">Speaking</span>}
      </div>
    </section>
  );
}
