import { FormEvent, useEffect, useState } from 'react';
import { Copy, Mail, Plus } from 'lucide-react';
import { Navigate } from 'react-router-dom';
import { authApi, type InviteRecord } from '../services/api';
import { useAuth } from '../context/AuthContext';

export default function InvitesPage() {
  const { user } = useAuth();
  const [invites, setInvites] = useState<InviteRecord[]>([]);
  const [email, setEmail] = useState('');
  const [note, setNote] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [createdLink, setCreatedLink] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const isAdmin = !!user?.is_admin;

  useEffect(() => {
    if (!isAdmin) return;
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const data = await authApi.listInvites();
        if (!cancelled) setInvites(data);
      } catch (err: any) {
        if (!cancelled) setError(err?.response?.data?.detail || 'Failed to load invites');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [isAdmin]);

  if (!isAdmin) {
    return <Navigate to="/projects" replace />;
  }

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setCreatedLink(null);
    setSubmitting(true);
    try {
      const invite = await authApi.createInvite(email.trim(), note.trim() || undefined);
      const link = `${window.location.origin}${invite.accept_path || `/invite/${invite.token}`}`;
      setCreatedLink(link);
      setEmail('');
      setNote('');
      const data = await authApi.listInvites();
      setInvites(data);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to create invite');
    } finally {
      setSubmitting(false);
    }
  };

  const copy = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      /* ignore */
    }
  };

  return (
    <div className="px-4 py-6 sm:px-0 max-w-3xl mx-auto">
      <div className="mb-6">
        <h2 className="text-3xl font-bold text-stone-900 mb-2">Invites</h2>
        <p className="text-stone-600">Invite teammates by email. They set a password via the link.</p>
      </div>

      <form onSubmit={onSubmit} className="glass-card rounded-2xl p-6 space-y-4 mb-8">
        {error && (
          <div className="rounded-lg bg-red-50 text-red-700 text-sm px-3 py-2 border border-red-100">
            {error}
          </div>
        )}
        {createdLink && (
          <div className="rounded-lg bg-emerald-50 text-emerald-800 text-sm px-3 py-2 border border-emerald-100 flex items-start justify-between gap-3">
            <div className="break-all">
              Invite created. Share this link:
              <div className="mt-1 font-mono text-xs">{createdLink}</div>
            </div>
            <button
              type="button"
              onClick={() => copy(createdLink)}
              className="shrink-0 inline-flex items-center gap-1 text-emerald-900 hover:underline"
            >
              <Copy className="h-3.5 w-3.5" /> Copy
            </button>
          </div>
        )}
        <div>
          <label className="block text-sm font-medium text-stone-700 mb-1.5">Email</label>
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full rounded-xl border border-stone-200 bg-white px-3 py-2.5 text-sm"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-stone-700 mb-1.5">Note (optional)</label>
          <input
            type="text"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            className="w-full rounded-xl border border-stone-200 bg-white px-3 py-2.5 text-sm"
          />
        </div>
        <button
          type="submit"
          disabled={submitting}
          className="inline-flex items-center gap-2 rounded-xl bg-stone-900 text-white text-sm font-medium px-4 py-2.5 hover:bg-stone-800 disabled:opacity-60"
        >
          <Plus className="h-4 w-4" />
          {submitting ? 'Creating…' : 'Create invite'}
        </button>
      </form>

      <div className="glass-card rounded-2xl overflow-hidden">
        <div className="px-6 py-4 border-b border-stone-100 flex items-center gap-2 text-sm font-medium text-stone-700">
          <Mail className="h-4 w-4" /> Recent invites
        </div>
        {loading ? (
          <div className="p-6 text-sm text-stone-500">Loading…</div>
        ) : invites.length === 0 ? (
          <div className="p-6 text-sm text-stone-500">No invites yet.</div>
        ) : (
          <ul className="divide-y divide-stone-100">
            {invites.map((inv) => {
              const link = `${window.location.origin}${inv.accept_path || `/invite/${inv.token}`}`;
              return (
                <li key={inv.id} className="px-6 py-4 flex items-start justify-between gap-4">
                  <div>
                    <div className="text-sm font-medium text-stone-900">{inv.email}</div>
                    <div className="text-xs text-stone-500 mt-1">
                      {inv.accepted_at
                        ? `Accepted ${new Date(inv.accepted_at).toLocaleString()}`
                        : `Expires ${new Date(inv.expires_at).toLocaleDateString()}`}
                    </div>
                  </div>
                  {!inv.accepted_at && (
                    <button
                      type="button"
                      onClick={() => copy(link)}
                      className="text-xs text-stone-600 hover:text-stone-900 inline-flex items-center gap-1"
                    >
                      <Copy className="h-3.5 w-3.5" /> Copy link
                    </button>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}
