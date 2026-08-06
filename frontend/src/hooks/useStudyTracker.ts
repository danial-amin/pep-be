import { useCallback, useEffect, useRef } from 'react';
import { useLocation } from 'react-router-dom';
import { studyApi } from '../services/api';
import { getActiveStudySlug, getStudyScope } from '../studyScope';

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
      study_scope: getStudyScope(),
    });
  }, [activeSlug, location.pathname, location.search]);

  return { track, activeSlug, scope: getStudyScope() };
}

export {
  getActiveStudySlug,
  setActiveStudySlug,
  getStudyScope,
  setStudyScope,
  clearStudyScope,
  studyPath,
} from '../studyScope';
