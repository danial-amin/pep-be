import { BrowserRouter as Router, Routes, Route, Link, useLocation, Navigate } from 'react-router-dom';
import { FileText, Users, MessageSquare, BarChart3, FolderOpen, Play, Bot, LogOut, UserPlus, LayoutGrid, ClipboardList } from 'lucide-react';
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
import LoginPage from './pages/LoginPage';
import AcceptInvitePage from './pages/AcceptInvitePage';
import InvitesPage from './pages/InvitesPage';
import StudyEnterPage from './pages/StudyEnterPage';
import StudyProfilesPage from './pages/StudyProfilesPage';
import StudyAdminPage from './pages/StudyAdminPage';
import LandingPage from './pages/LandingPage';
import ProtectedRoute from './components/ProtectedRoute';
import { AuthProvider, useAuth } from './context/AuthContext';
import { getActiveStudySlug, studyPath } from './hooks/useStudyTracker';

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

function StudyParticipantGate({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const studySlug = user?.study_slug || getActiveStudySlug();
  if (loading) return null;
  if (user?.is_study_participant && studySlug) {
    return <Navigate to={studyPath(studySlug, '/profiles')} replace />;
  }
  return <>{children}</>;
}

function AppShell() {
  const location = useLocation();
  const { user, logout, isAuthenticated, loading } = useAuth();
  const isAuthScreen =
    location.pathname.startsWith('/login') ||
    location.pathname.startsWith('/invite') ||
    /^\/study\/[^/]+$/.test(location.pathname);
  const isStudyParticipant = !!user?.is_study_participant;
  const studySlug = user?.study_slug || getActiveStudySlug();
  const hideMainNav = isStudyParticipant || location.pathname.startsWith('/study/');
  const showStudyNav = isAuthenticated && !!studySlug && (isStudyParticipant || location.pathname.startsWith('/study/'));

  return (
    <div className="min-h-screen bg-[#f8f7f4]">
      {!isAuthScreen && (
        <nav className="glass-strong sticky top-0 z-50 bg-white">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between h-14">
              <div className="flex items-center gap-6">
                <Link
                  to={
                    isStudyParticipant && studySlug
                      ? studyPath(studySlug, '/profiles')
                      : isAuthenticated
                        ? '/projects'
                        : '/'
                  }
                  className="flex-shrink-0 flex items-center gap-2.5 group"
                >
                  <div className="w-7 h-7 rounded-lg bg-stone-900 flex items-center justify-center group-hover:bg-stone-800 transition-colors">
                    <span className="text-white text-xs font-bold tracking-tight">P</span>
                  </div>
                  <span className="text-sm font-semibold text-stone-900 group-hover:text-stone-800 transition-colors">PEP</span>
                  <span className="text-stone-300 text-sm">|</span>
                  <span className="text-sm text-stone-400 font-normal group-hover:text-stone-500 transition-colors">
                    {isStudyParticipant ? 'User study' : 'Persona Generator'}
                  </span>
                </Link>
                {showStudyNav && studySlug && (
                  <div className="flex items-center gap-1 overflow-x-auto">
                    <NavLink to={studyPath(studySlug, '/profiles')} icon={LayoutGrid} label="Profiles" />
                    <NavLink to={studyPath(studySlug, '/persona-chat')} icon={Bot} label="Chat" />
                    <NavLink to={studyPath(studySlug, '/simulations')} icon={Play} label="Simulation" />
                  </div>
                )}
                {isAuthenticated && !hideMainNav && (
                  <div className="hidden sm:flex sm:items-center sm:gap-1">
                    <NavLink to="/projects" icon={FolderOpen} label="Projects" />
                    <NavLink to="/documents" icon={FileText} label="Documents" />
                    <NavLink to="/personas" icon={Users} label="Personas" />
                    <NavLink to="/simulations" icon={Play} label="Simulation" />
                    <NavLink to="/persona-chat" icon={Bot} label="Persona Chat" />
                    <NavLink to="/prompts" icon={MessageSquare} label="Q&A Prompts" />
                    <NavLink to="/reports" icon={BarChart3} label="Reports" />
                    {user?.is_admin && <NavLink to="/invites" icon={UserPlus} label="Invites" />}
                    {user?.is_admin && <NavLink to="/admin/study" icon={ClipboardList} label="Study" />}
                  </div>
                )}
              </div>
              <div className="flex items-center gap-3">
                {!loading && isAuthenticated && user && (
                  <>
                    <span className="hidden sm:inline text-xs text-stone-500 truncate max-w-[160px]" title={user.email}>
                      {user.participant_code || user.name}
                    </span>
                    <button
                      type="button"
                      onClick={logout}
                      className="inline-flex items-center gap-1.5 text-xs text-stone-500 hover:text-stone-900 px-2 py-1.5 rounded-lg hover:bg-stone-50"
                    >
                      <LogOut className="h-3.5 w-3.5" />
                      {isStudyParticipant ? 'End' : 'Sign out'}
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
          <Route path="/study/:slug" element={<StudyEnterPage />} />
          <Route
            path="/"
            element={
              isStudyParticipant && studySlug ? (
                <Navigate to={studyPath(studySlug, '/profiles')} replace />
              ) : isAuthenticated && !isStudyParticipant ? (
                <Navigate to="/projects" replace />
              ) : (
                <LandingPage />
              )
            }
          />

          {/* Study participant workspace — same JWT identity (P01 / PX / …) */}
          <Route path="/study/:slug/profiles" element={<ProtectedRoute><StudyProfilesPage /></ProtectedRoute>} />
          <Route path="/study/:slug/persona-chat" element={<ProtectedRoute><PersonaChatPage /></ProtectedRoute>} />
          <Route path="/study/:slug/persona-chat/:personaId" element={<ProtectedRoute><PersonaChatPage /></ProtectedRoute>} />
          <Route path="/study/:slug/simulations" element={<ProtectedRoute><SimulationPage /></ProtectedRoute>} />
          <Route path="/study/:slug/simulations/:simulationId" element={<ProtectedRoute><SimulationPage /></ProtectedRoute>} />
          <Route path="/study/:slug/simulations/:simulationId/persona-chats" element={<ProtectedRoute><SimulationPersonaChatsPage /></ProtectedRoute>} />
          <Route path="/study/:slug/simulations/:simulationId/persona-chats/:personaId/:personaSlug" element={<ProtectedRoute><SimulationPersonaChatsPage /></ProtectedRoute>} />

          <Route path="/projects" element={<ProtectedRoute><StudyParticipantGate><ProjectsPage /></StudyParticipantGate></ProtectedRoute>} />
          <Route path="/projects/new" element={<ProtectedRoute><StudyParticipantGate><NewProjectPage /></StudyParticipantGate></ProtectedRoute>} />
          <Route path="/projects/:projectId/workflow" element={<ProtectedRoute><StudyParticipantGate><ProjectWorkflowPage /></StudyParticipantGate></ProtectedRoute>} />
          <Route path="/documents" element={<ProtectedRoute><StudyParticipantGate><DocumentsPage /></StudyParticipantGate></ProtectedRoute>} />
          <Route path="/personas" element={<ProtectedRoute><StudyParticipantGate><PersonasPage /></StudyParticipantGate></ProtectedRoute>} />
          <Route path="/personas/:setId/profiles" element={<ProtectedRoute><StudyParticipantGate><PersonaSetProfilesPage /></StudyParticipantGate></ProtectedRoute>} />
          <Route path="/personas/:setId" element={<ProtectedRoute><StudyParticipantGate><PersonaDetailPage /></StudyParticipantGate></ProtectedRoute>} />
          <Route path="/personas/:setId/:personaId" element={<ProtectedRoute><StudyParticipantGate><PersonaDetailPage /></StudyParticipantGate></ProtectedRoute>} />
          <Route path="/simulations" element={<ProtectedRoute><StudyParticipantGate><SimulationPage /></StudyParticipantGate></ProtectedRoute>} />
          <Route path="/simulations/:simulationId" element={<ProtectedRoute><StudyParticipantGate><SimulationPage /></StudyParticipantGate></ProtectedRoute>} />
          <Route path="/simulations/:simulationId/persona-chats" element={<ProtectedRoute><StudyParticipantGate><SimulationPersonaChatsPage /></StudyParticipantGate></ProtectedRoute>} />
          <Route path="/simulations/:simulationId/persona-chats/:personaId/:personaSlug" element={<ProtectedRoute><StudyParticipantGate><SimulationPersonaChatsPage /></StudyParticipantGate></ProtectedRoute>} />
          <Route path="/persona-chat" element={<ProtectedRoute><StudyParticipantGate><PersonaChatPage /></StudyParticipantGate></ProtectedRoute>} />
          <Route path="/persona-chat/:personaId" element={<ProtectedRoute><StudyParticipantGate><PersonaChatPage /></StudyParticipantGate></ProtectedRoute>} />
          <Route path="/prompts" element={<ProtectedRoute><StudyParticipantGate><PromptsPage /></StudyParticipantGate></ProtectedRoute>} />
          <Route path="/reports" element={<ProtectedRoute><StudyParticipantGate><ReportsPage /></StudyParticipantGate></ProtectedRoute>} />
          <Route path="/invites" element={<ProtectedRoute><StudyParticipantGate><InvitesPage /></StudyParticipantGate></ProtectedRoute>} />
          <Route path="/admin/study" element={<ProtectedRoute><StudyParticipantGate><StudyAdminPage /></StudyParticipantGate></ProtectedRoute>} />
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
