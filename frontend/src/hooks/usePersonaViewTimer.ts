import { useEffect, useRef } from 'react';
import { getApiUrl, getAuthToken } from '../services/api';

export type PersonaViewType = 'persona' | 'set_profiles';

type UsePersonaViewTimerOptions = {
  personaSetId: number | null | undefined;
  viewType: PersonaViewType;
  /** Required when viewType is 'persona' */
  personaId?: number | null;
  enabled?: boolean;
  /** Ignore visits shorter than this (seconds). Default 1. */
  minSeconds?: number;
};

function sendProfileView(payload: Record<string, unknown>) {
  const token = getAuthToken();
  if (!token) return;

  const url = `${getApiUrl()}/analytics/profile-views`;
  const body = JSON.stringify(payload);

  try {
    void fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body,
      keepalive: true,
    }).catch(() => {
      /* best-effort */
    });
  } catch {
    /* best-effort */
  }
}

/**
 * Starts timing when the page/view becomes active and records duration on leave,
 * persona switch, or page unload. Time while the tab is hidden is excluded.
 */
export function usePersonaViewTimer({
  personaSetId,
  viewType,
  personaId = null,
  enabled = true,
  minSeconds = 1,
}: UsePersonaViewTimerOptions) {
  const accumulatedMsRef = useRef(0);
  const activeStartRef = useRef<number | null>(null);
  const sessionStartRef = useRef<string | null>(null);
  const flushedRef = useRef(false);

  useEffect(() => {
    const canTrack =
      enabled &&
      !!personaSetId &&
      (viewType === 'set_profiles' || !!personaId);

    if (!canTrack) return;

    accumulatedMsRef.current = 0;
    flushedRef.current = false;
    sessionStartRef.current = new Date().toISOString();
    activeStartRef.current = document.hidden ? null : Date.now();

    const pause = () => {
      if (activeStartRef.current != null) {
        accumulatedMsRef.current += Date.now() - activeStartRef.current;
        activeStartRef.current = null;
      }
    };

    const resume = () => {
      if (activeStartRef.current == null && !document.hidden) {
        activeStartRef.current = Date.now();
      }
    };

    const flush = () => {
      pause();
      if (flushedRef.current) return;
      flushedRef.current = true;

      const durationSeconds = accumulatedMsRef.current / 1000;
      if (durationSeconds < minSeconds) return;

      sendProfileView({
        persona_set_id: personaSetId,
        persona_id: viewType === 'persona' ? personaId : null,
        view_type: viewType,
        duration_seconds: Math.round(durationSeconds * 100) / 100,
        started_at: sessionStartRef.current,
        ended_at: new Date().toISOString(),
      });
    };

    const onVisibility = () => {
      if (document.hidden) pause();
      else resume();
    };

    document.addEventListener('visibilitychange', onVisibility);
    window.addEventListener('pagehide', flush);

    return () => {
      flush();
      document.removeEventListener('visibilitychange', onVisibility);
      window.removeEventListener('pagehide', flush);
    };
  }, [enabled, personaSetId, personaId, viewType, minSeconds]);
}
