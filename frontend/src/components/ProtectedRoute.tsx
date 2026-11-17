import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { studyEnterPath } from '../studyScope';

export default function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="min-h-[50vh] flex items-center justify-center text-stone-500 text-sm">
        Checking session…
      </div>
    );
  }

  if (!isAuthenticated) {
    if (location.pathname.startsWith('/study/')) {
      const slug = location.pathname.split('/')[2];
      return <Navigate to={studyEnterPath(slug)} replace />;
    }
    return <Navigate to="/login" state={{ from: location.pathname }} replace />;
  }

  return <>{children}</>;
}
