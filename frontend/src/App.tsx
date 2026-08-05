import { BrowserRouter as Router, Routes, Route, Link, useLocation, Navigate } from 'react-router-dom';
import { FileText, Users, MessageSquare, BarChart3, FolderOpen, Play, Bot, LogOut, UserPlus } from 'lucide-react';
import DocumentsPage from './pages/DocumentsPage';
import PersonasPage from './pages/PersonasPage';
import PersonaDetailPage from './pages/PersonaDetailPage';
import PersonaSetProfilesPage from './pages/PersonaSetProfilesPage';
import PromptsPage from './pages/PromptsPage';
import ReportsPage from './pages/ReportsPage';
import ProjectsPage from './pages/ProjectsPage';
import NewProjectPage from './pages/NewProjectPage';
import ProjectWorkflowPage from './pages/ProjectWorkflowPage';
import SimulationPage from './pages/SimulationPage';
import SimulationPersonaChatsPage from './pages/SimulationPersonaChatsPage';
import PersonaChatPage from './pages/PersonaChatPage';
import LandingPage from './pages/LandingPage';
import LoginPage from './pages/LoginPage';
import AcceptInvitePage from './pages/AcceptInvitePage';
import InvitesPage from './pages/InvitesPage';
import ProtectedRoute from './components/ProtectedRoute';
import { AuthProvider, useAuth } from './context/AuthContext';

function NavLink({ to, icon: Icon, label }: { to: string; icon: React.ElementType; label: string }) {
  const location = useLocation();
  const isActive = location.pathname === to || (to !== '/' && location.pathname.startsWith(to));
  return (
    <Link
      to={to}
      className={`inline-flex items-center px-3 py-2 text-sm font-medium rounded-lg transition-all duration-150 ${
        isActive
          ? 'bg-stone-100 text-stone-900'
          : 'text-stone-500 hover:text-stone-900 hover:bg-stone-50'
      }`}
    >
      <Icon className="mr-2 h-4 w-4" />
      {label}
    </Link>
  );
}

function AppShell() {
  const location = useLocation();
  const { user, logout, isAuthenticated, loading } = useAuth();
  const isAuthScreen =
    location.pathname.startsWith('/login') || location.pathname.startsWith('/invite');

  return (
    <div className="min-h-screen bg-[#f8f7f4]">
      {!isAuthScreen && (
        <nav className="glass-strong sticky top-0 z-50 bg-white">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between h-14">
              <div className="flex items-center gap-6">
                <Link to={isAuthenticated ? '/projects' : '/'} className="flex-shrink-0 flex items-center gap-2.5 group">
                  <div className="w-7 h-7 rounded-lg bg-stone-900 flex items-center justify-center group-hover:bg-stone-800 transition-colors">
                    <span className="text-white text-xs font-bold tracking-tight">P</span>
                  </div>
                  <span className="text-sm font-semibold text-stone-900 group-hover:text-stone-800 transition-colors">PEP</span>
                  <span className="text-stone-300 text-sm">|</span>
                  <span className="text-sm text-stone-400 font-normal group-hover:text-stone-500 transition-colors">Persona Generator</span>
                </Link>
                {isAuthenticated && (
                  <div className="hidden sm:flex sm:items-center sm:gap-1">
                    <NavLink to="/projects" icon={FolderOpen} label="Projects" />
                    <NavLink to="/documents" icon={FileText} label="Documents" />
                    <NavLink to="/personas" icon={Users} label="Personas" />
                    <NavLink to="/simulations" icon={Play} label="Simulation" />
                    <NavLink to="/persona-chat" icon={Bot} label="Persona Chat" />
                    <NavLink to="/prompts" icon={MessageSquare} label="Q&A Prompts" />
                    <NavLink to="/reports" icon={BarChart3} label="Reports" />
                    {user?.is_admin && <NavLink to="/invites" icon={UserPlus} label="Invites" />}
                  </div>
                )}
              </div>
              <div className="flex items-center gap-3">
                {!loading && isAuthenticated && user && (
                  <>
                    <span className="hidden sm:inline text-xs text-stone-500 truncate max-w-[160px]" title={user.email}>
                      {user.name}
                    </span>
                    <button
                      type="button"
                      onClick={logout}
                      className="inline-flex items-center gap-1.5 text-xs text-stone-500 hover:text-stone-900 px-2 py-1.5 rounded-lg hover:bg-stone-50"
                    >
                      <LogOut className="h-3.5 w-3.5" />
                      Sign out
                    </button>
                  </>
                )}
                {!loading && !isAuthenticated && !isAuthScreen && (
                  <Link
                    to="/login"
                    className="text-xs font-medium text-stone-600 hover:text-stone-900 px-3 py-1.5 rounded-lg hover:bg-stone-50"
                  >
                    Sign in
                  </Link>
                )}
              </div>
            </div>
          </div>
        </nav>
      )}

      <main className={`mx-auto py-8 sm:px-6 lg:px-8 ${isAuthScreen ? 'max-w-7xl' : 'max-w-7xl'}`}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/invite/:token" element={<AcceptInvitePage />} />
          <Route path="/" element={isAuthenticated ? <Navigate to="/projects" replace /> : <LandingPage />} />

          <Route path="/projects" element={<ProtectedRoute><ProjectsPage /></ProtectedRoute>} />
          <Route path="/projects/new" element={<ProtectedRoute><NewProjectPage /></ProtectedRoute>} />
          <Route path="/projects/:projectId/workflow" element={<ProtectedRoute><ProjectWorkflowPage /></ProtectedRoute>} />
          <Route path="/documents" element={<ProtectedRoute><DocumentsPage /></ProtectedRoute>} />
          <Route path="/personas" element={<ProtectedRoute><PersonasPage /></ProtectedRoute>} />
          <Route path="/personas/:setId/profiles" element={<ProtectedRoute><PersonaSetProfilesPage /></ProtectedRoute>} />
          <Route path="/personas/:setId" element={<ProtectedRoute><PersonaDetailPage /></ProtectedRoute>} />
          <Route path="/personas/:setId/:personaId" element={<ProtectedRoute><PersonaDetailPage /></ProtectedRoute>} />
          <Route path="/simulations" element={<ProtectedRoute><SimulationPage /></ProtectedRoute>} />
          <Route path="/simulations/:simulationId" element={<ProtectedRoute><SimulationPage /></ProtectedRoute>} />
          <Route path="/simulations/:simulationId/persona-chats" element={<ProtectedRoute><SimulationPersonaChatsPage /></ProtectedRoute>} />
          <Route path="/simulations/:simulationId/persona-chats/:personaId/:personaSlug" element={<ProtectedRoute><SimulationPersonaChatsPage /></ProtectedRoute>} />
          <Route path="/persona-chat" element={<ProtectedRoute><PersonaChatPage /></ProtectedRoute>} />
          <Route path="/persona-chat/:personaId" element={<ProtectedRoute><PersonaChatPage /></ProtectedRoute>} />
          <Route path="/prompts" element={<ProtectedRoute><PromptsPage /></ProtectedRoute>} />
          <Route path="/reports" element={<ProtectedRoute><ReportsPage /></ProtectedRoute>} />
          <Route path="/invites" element={<ProtectedRoute><InvitesPage /></ProtectedRoute>} />
        </Routes>
      </main>
    </div>
  );
}

function App() {
  return (
    <AuthProvider>
      <Router>
        <AppShell />
      </Router>
    </AuthProvider>
  );
}

export default App;
