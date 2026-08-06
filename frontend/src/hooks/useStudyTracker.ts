import { useCallback, useEffect, useRef } from 'react';
import { useLocation } from 'react-router-dom';
import { studyApi } from '../services/api';

const STUDY_SLUG_KEY = 'pep_study_slug';

export function getActiveStudySlug(): string | null {
  try {
    return localStorage.getItem(STUDY_SLUG_KEY);
  } catch {
    return null;
  }
}

export function setActiveStudySlug(slug: string | null) {
  try {
    if (slug) localStorage.setItem(STUDY_SLUG_KEY, slug);
    else localStorage.removeItem(STUDY_SLUG_KEY);
  } catch {
    /* ignore */
  }
}

/**
 * Records study actions when a study slug is active.
 * Tracks route changes automatically; call track() for clicks / expands / etc.
 */
export function useStudyTracker(slug?: string | null) {
  const location = useLocation();
  const activeSlug = slug || getActiveStudySlug();
  const pathRef = useRef(location.pathname);

  const track = useCallback(
    (eventType: string, payload?: Record<string, unknown>) => {
      const s = slug || getActiveStudySlug();
      if (!s) return;
      void studyApi.recordEvent(s, eventType, pathRef.current, payload);
    },
    [slug]
  );

  useEffect(() => {
    pathRef.current = location.pathname;
  }, [location.pathname]);

  useEffect(() => {
    if (!activeSlug) return;
    void studyApi.recordEvent(activeSlug, 'page_view', location.pathname, {
      search: location.search,
    });
  }, [activeSlug, location.pathname, location.search]);

  return { track, activeSlug };
}
