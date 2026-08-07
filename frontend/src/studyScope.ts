/** Persisted study session scope (localStorage). No API imports. */

export const STUDY_SLUG_KEY = 'pep_study_slug';
export const STUDY_PROJECT_KEY = 'pep_study_project_id';
export const STUDY_PERSONA_SET_KEY = 'pep_study_persona_set_id';

/** Default study entry for this deployment (Policy Study user study). */
export const DEFAULT_STUDY_SLUG = 'policy-study';

export type StudyScope = {
  slug: string;
  projectId: number | null;
  personaSetId: number | null;
};

function readInt(key: string): number | null {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return null;
    const n = parseInt(raw, 10);
    return Number.isFinite(n) ? n : null;
  } catch {
    return null;
  }
}

export function getActiveStudySlug(): string | null {
  try {
    return localStorage.getItem(STUDY_SLUG_KEY);
  } catch {
    return null;
  }
}

/** Prefer active study slug, else the deployment default. */
export function getStudyEntrySlug(): string {
  return getActiveStudySlug() || DEFAULT_STUDY_SLUG;
}

/** Study enter URL (no password) — use instead of /login for participants. */
export function studyEnterPath(slug?: string | null): string {
  return `/study/${slug || getStudyEntrySlug()}`;
}

export function getStudyScope(): StudyScope | null {
  const slug = getActiveStudySlug();
  if (!slug) return null;
  return {
    slug,
    projectId: readInt(STUDY_PROJECT_KEY),
    personaSetId: readInt(STUDY_PERSONA_SET_KEY),
  };
}

export function setStudyScope(scope: {
  slug: string;
  projectId?: number | null;
  personaSetId?: number | null;
}) {
  try {
    localStorage.setItem(STUDY_SLUG_KEY, scope.slug);
    if (scope.projectId != null) {
      localStorage.setItem(STUDY_PROJECT_KEY, String(scope.projectId));
    }
    if (scope.personaSetId != null) {
      localStorage.setItem(STUDY_PERSONA_SET_KEY, String(scope.personaSetId));
    }
  } catch {
    /* ignore */
  }
}

export function setActiveStudySlug(slug: string | null) {
  try {
    if (slug) localStorage.setItem(STUDY_SLUG_KEY, slug);
    else clearStudyScope();
  } catch {
    /* ignore */
  }
}

export function clearStudyScope() {
  try {
    localStorage.removeItem(STUDY_SLUG_KEY);
    localStorage.removeItem(STUDY_PROJECT_KEY);
    localStorage.removeItem(STUDY_PERSONA_SET_KEY);
  } catch {
    /* ignore */
  }
}

/** Build a path under /study/:slug/... */
export function studyPath(slug: string, rest: string): string {
  const path = rest.startsWith('/') ? rest : `/${rest}`;
  return `/study/${slug}${path}`;
}
