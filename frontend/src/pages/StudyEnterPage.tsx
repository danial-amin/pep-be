import { FormEvent, useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { setAuthToken, studyApi, type StudyPublicInfo } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { setStudyScope } from '../hooks/useStudyTracker';

export default function StudyEnterPage() {
  const { slug } = useParams<{ slug: string }>();
  const navigate = useNavigate();
  const { user, refresh } = useAuth();
  const [info, setInfo] = useState<StudyPublicInfo | null>(null);
  const [code, setCode] = useState('');
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (user?.is_study_participant && user.study_slug === slug) {
      navigate(`/study/${slug}/profiles`, { replace: true });
    }
  }, [user, slug, navigate]);

  useEffect(() => {
    if (!slug) return;
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await studyApi.getPublic(slug);
        if (!cancelled) setInfo(data);
      } catch (e: any) {
        if (!cancelled) {
          setInfo(null);
          setError(e?.response?.data?.detail || 'Study not found or disabled');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [slug]);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!slug || !code.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      const result = await studyApi.enter(slug, code.trim());
      setAuthToken(result.access_token);
      setStudyScope({
        slug,
        projectId: result.study.project_id ?? null,
        personaSetId: result.study.persona_set_id,
      });
      await refresh();
      await studyApi.recordEvent(slug, 'study_enter', `/study/${slug}`, {
        participant_code: result.participant.code,
      });
      navigate(`/study/${slug}/profiles`, { replace: true });
    } catch (err: any) {
      setError(err?.response?.data?.detail || err.message || 'Could not enter study');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return <div className="min-h-[60vh] flex items-center justify-center text-stone-600">Loading study…</div>;
  }

  if (!info) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center px-4">
        <div className="max-w-md text-center text-stone-700">{error || 'Study unavailable'}</div>
      </div>
    );
  }

  return (
    <div className="min-h-[70vh] flex items-center justify-center px-4 py-10">
      <div className="w-full max-w-md glass-card rounded-2xl border border-stone-200 p-6 sm:p-8">
        <p className="text-xs font-medium uppercase tracking-wide text-stone-500 mb-2">User study</p>
        <h1 className="text-2xl font-bold text-stone-900 mb-2">{info.name}</h1>
        <p className="text-sm text-stone-600 mb-6 whitespace-pre-wrap">
          {info.welcome_text ||
            'Enter your participant code to begin. No password is required.'}
        </p>
        <form onSubmit={onSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-stone-700 mb-1">
              Participant code
            </label>
            <input
              value={code}
              onChange={(e) => setCode(e.target.value.toUpperCase())}
              placeholder="P01"
              autoFocus
              autoComplete="off"
              className="w-full px-4 py-3 rounded-xl border border-stone-200 text-stone-900 text-lg tracking-wider font-mono"
            />
            <p className="mt-1.5 text-xs text-stone-500">
              Participants: P01, P02, P03… · Test: PX (or PX1–PX6 for each order)
            </p>
          </div>
          {error && (
            <div className="text-sm text-red-700 bg-red-50 border border-red-100 rounded-lg px-3 py-2">
              {error}
            </div>
          )}
          <button
            type="submit"
            disabled={submitting || !code.trim()}
            className="w-full py-3 rounded-xl bg-stone-900 text-white font-medium disabled:opacity-50"
          >
            {submitting ? 'Entering…' : 'Enter study'}
          </button>
        </form>
      </div>
    </div>
  );
}
