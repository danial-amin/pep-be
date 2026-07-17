import { FormEvent, useEffect, useState } from 'react';
import { Link, Navigate, useNavigate, useParams } from 'react-router-dom';
import { authApi } from '../services/api';
import { useAuth } from '../context/AuthContext';

export default function AcceptInvitePage() {
  const { token = '' } = useParams<{ token: string }>();
  const { acceptInvite, isAuthenticated, loading: authLoading } = useAuth();
  const navigate = useNavigate();

  const [preview, setPreview] = useState<{ email: string; valid: boolean; note?: string | null } | null>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [name, setName] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    (async () => {
      try {
        const data = await authApi.previewInvite(token);
        if (!cancelled) {
          setPreview(data);
          if (!data.valid) setPreviewError('This invite is invalid or already used.');
        }
      } catch {
        if (!cancelled) setPreviewError('Invite not found or expired.');
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [token]);

  if (!authLoading && isAuthenticated) {
    return <Navigate to="/projects" replace />;
  }

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    if (password.length < 8) {
      setError('Password must be at least 8 characters.');
      return;
    }
    if (password !== confirm) {
      setError('Passwords do not match.');
      return;
    }
    setSubmitting(true);
    try {
      await acceptInvite(token, name.trim(), password);
      navigate('/projects', { replace: true });
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || 'Could not accept invite');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-[70vh] flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <div className="inline-flex w-10 h-10 rounded-xl bg-stone-900 items-center justify-center mb-4">
            <span className="text-white text-sm font-bold">P</span>
          </div>
          <h1 className="text-2xl font-semibold text-stone-900">Accept invitation</h1>
          <p className="mt-2 text-sm text-stone-500">
            Create your password to join PEP.
          </p>
        </div>

        {previewError ? (
          <div className="glass-card rounded-2xl p-6 text-center space-y-4">
            <p className="text-sm text-red-700">{previewError}</p>
            <Link to="/login" className="text-sm text-stone-600 underline underline-offset-2">
              Back to sign in
            </Link>
          </div>
        ) : (
          <form onSubmit={onSubmit} className="glass-card rounded-2xl p-6 space-y-4">
            {preview && (
              <div className="rounded-lg bg-stone-50 border border-stone-100 px-3 py-2 text-sm text-stone-600">
                Invited as <span className="font-medium text-stone-900">{preview.email}</span>
                {preview.note ? <p className="mt-1 text-stone-500">{preview.note}</p> : null}
              </div>
            )}
            {error && (
              <div className="rounded-lg bg-red-50 text-red-700 text-sm px-3 py-2 border border-red-100">
                {error}
              </div>
            )}
            <div>
              <label className="block text-sm font-medium text-stone-700 mb-1.5">Your name</label>
              <input
                type="text"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full rounded-xl border border-stone-200 bg-white px-3 py-2.5 text-sm text-stone-900 focus:outline-none focus:ring-2 focus:ring-stone-900/10 focus:border-stone-400"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-stone-700 mb-1.5">Password</label>
              <input
                type="password"
                required
                minLength={8}
                autoComplete="new-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-xl border border-stone-200 bg-white px-3 py-2.5 text-sm text-stone-900 focus:outline-none focus:ring-2 focus:ring-stone-900/10 focus:border-stone-400"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-stone-700 mb-1.5">Confirm password</label>
              <input
                type="password"
                required
                minLength={8}
                autoComplete="new-password"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                className="w-full rounded-xl border border-stone-200 bg-white px-3 py-2.5 text-sm text-stone-900 focus:outline-none focus:ring-2 focus:ring-stone-900/10 focus:border-stone-400"
              />
            </div>
            <button
              type="submit"
              disabled={submitting || !preview?.valid}
              className="w-full rounded-xl bg-stone-900 text-white text-sm font-medium py-2.5 hover:bg-stone-800 disabled:opacity-60 transition-colors"
            >
              {submitting ? 'Creating account…' : 'Create account'}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
