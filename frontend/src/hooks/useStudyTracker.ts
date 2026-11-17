import { useCallback, useEffect, useRef } from 'react';
import { useLocation } from 'react-router-dom';
import { studyApi } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { getActiveStudySlug, getStudyScope } from '../studyScope';

/**
 * Records study actions when a study slug is active.
 * Tracks route changes + dwell time; call track() for clicks / messages / etc.
 * Every event payload is tagged with participant_code and user_id when available.
 */
export function useStudyTracker(slug?: string | null) {
  const location = useLocation();
  const { user } = useAuth();
  const activeSlug = slug || getActiveStudySlug();
  const pathRef = useRef(location.pathname);
  const prevPathRef = useRef(location.pathname);
  const pageEnteredAtRef = useRef<number>(Date.now());
  const pageActiveStartRef = useRef<number | null>(document.hidden ? null : Date.now());
  const pageAccumulatedMsRef = useRef(0);
  const hasSeenPageRef = useRef(false);
  const identityRef = useRef({
    user_id: user?.id ?? null,
    participant_code: user?.participant_code ?? null,
    study_id: user?.study_id ?? null,
  });

  useEffect(() => {
    identityRef.current = {
      user_id: user?.id ?? null,
      participant_code: user?.participant_code ?? null,
      study_id: user?.study_id ?? null,
    };
  }, [user?.id, user?.participant_code, user?.study_id]);

  const withIdentity = useCallback((payload?: Record<string, unknown>) => {
    const id = identityRef.current;
    return {
      ...(payload || {}),
      user_id: id.user_id,
      participant_code: id.participant_code,
      study_id: id.study_id,
      client_ts: new Date().toISOString(),
    };
  }, []);

  const track = useCallback(
    (eventType: string, payload?: Record<string, unknown>) => {
      const s = slug || getActiveStudySlug();
      if (!s) return;
      void studyApi.recordEvent(s, eventType, pathRef.current, withIdentity(payload));
    },
    [slug, withIdentity]
  );

  const pausePageTimer = useCallback(() => {
    if (pageActiveStartRef.current != null) {
      pageAccumulatedMsRef.current += Date.now() - pageActiveStartRef.current;
      pageActiveStartRef.current = null;
    }
  }, []);

  const resumePageTimer = useCallback(() => {
    if (pageActiveStartRef.current == null && !document.hidden) {
      pageActiveStartRef.current = Date.now();
    }
  }, []);

  const flushPageDwell = useCallback(
    (reason: string, opts?: { path?: string; nextPath?: string }) => {
      const s = slug || getActiveStudySlug();
      if (!s) return;
      pausePageTimer();
      const durationSeconds = pageAccumulatedMsRef.current / 1000;
      if (durationSeconds < 0.5) return;
      const path = opts?.path ?? pathRef.current;
      void studyApi.recordEvent(
        s,
        'page_dwell',
        path,
        withIdentity({
          duration_seconds: Math.round(durationSeconds * 100) / 100,
          reason,
          next_path: opts?.nextPath ?? null,
          entered_at: new Date(pageEnteredAtRef.current).toISOString(),
          left_at: new Date().toISOString(),
          study_scope: getStudyScope(),
        })
      );
    },
    [slug, pausePageTimer, withIdentity]
  );

  // Page view + dwell accounting across route changes
  useEffect(() => {
    if (!activeSlug) {
      pathRef.current = location.pathname;
      prevPathRef.current = location.pathname;
      return;
    }

    const leavingPath = prevPathRef.current;
    if (hasSeenPageRef.current && leavingPath !== location.pathname) {
      flushPageDwell('route_change', {
        path: leavingPath,
        nextPath: location.pathname,
      });
    }
    hasSeenPageRef.current = true;

    prevPathRef.current = location.pathname;
    pathRef.current = location.pathname;
    pageEnteredAtRef.current = Date.now();
    pageAccumulatedMsRef.current = 0;
    pageActiveStartRef.current = document.hidden ? null : Date.now();

    void studyApi.recordEvent(
      activeSlug,
      'page_view',
      location.pathname,
      withIdentity({
        search: location.search,
        study_scope: getStudyScope(),
      })
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeSlug, location.pathname, location.search]);

  // Visibility + unload dwell
  useEffect(() => {
    if (!activeSlug) return;

    const onVisibility = () => {
      if (document.hidden) {
        flushPageDwell('tab_hidden', { path: pathRef.current });
        pageAccumulatedMsRef.current = 0;
        pageEnteredAtRef.current = Date.now();
        pageActiveStartRef.current = null;
      } else {
        resumePageTimer();
      }
    };

    const onPageHide = () => {
      flushPageDwell('pagehide', { path: pathRef.current });
    };

    document.addEventListener('visibilitychange', onVisibility);
    window.addEventListener('pagehide', onPageHide);
    return () => {
      flushPageDwell('unmount', { path: pathRef.current });
      document.removeEventListener('visibilitychange', onVisibility);
      window.removeEventListener('pagehide', onPageHide);
    };
  }, [activeSlug, flushPageDwell, resumePageTimer]);

  return {
    track,
    activeSlug,
    scope: getStudyScope(),
    participantCode: user?.participant_code ?? null,
    userId: user?.id ?? null,
  };
}

export {
  getActiveStudySlug,
  setActiveStudySlug,
  getStudyScope,
  setStudyScope,
  clearStudyScope,
  studyPath,
  studyEnterPath,
  getStudyEntrySlug,
  DEFAULT_STUDY_SLUG,
} from '../studyScope';
