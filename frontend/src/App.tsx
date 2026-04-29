import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import { FileText, Users, MessageSquare, BarChart3, FolderOpen, Play } from 'lucide-react';
import DocumentsPage from './pages/DocumentsPage';
import PersonasPage from './pages/PersonasPage';
import PersonaDetailPage from './pages/PersonaDetailPage';
import PromptsPage from './pages/PromptsPage';
import ReportsPage from './pages/ReportsPage';
import ProjectsPage from './pages/ProjectsPage';
import NewProjectPage from './pages/NewProjectPage';
import ProjectWorkflowPage from './pages/ProjectWorkflowPage';
import SimulationPage from './pages/SimulationPage';

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

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-[#f8f7f4]">
        {/* Navigation */}
        <nav className="glass-strong sticky top-0 z-50 bg-white">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between h-14">
              <div className="flex items-center gap-6">
                <div className="flex-shrink-0 flex items-center gap-2.5">
                  <div className="w-7 h-7 rounded-lg bg-stone-900 flex items-center justify-center">
                    <span className="text-white text-xs font-bold tracking-tight">P</span>
                  </div>
                  <span className="text-sm font-semibold text-stone-900">PEP</span>
                  <span className="text-stone-300 text-sm">|</span>
                  <span className="text-sm text-stone-400 font-normal">Persona Generator</span>
                </div>
                <div className="hidden sm:flex sm:items-center sm:gap-1">
                  <NavLink to="/projects" icon={FolderOpen} label="Projects" />
                  <NavLink to="/documents" icon={FileText} label="Documents" />
                  <NavLink to="/personas" icon={Users} label="Personas" />
                  <NavLink to="/simulations" icon={Play} label="Simulation" />
                  <NavLink to="/prompts" icon={MessageSquare} label="Q&A Prompts" />
                  <NavLink to="/reports" icon={BarChart3} label="Reports" />
                </div>
              </div>
            </div>
          </div>
        </nav>

        {/* Main Content */}
        <main className="max-w-7xl mx-auto py-8 sm:px-6 lg:px-8">
          <Routes>
            <Route path="/" element={<ProjectsPage />} />
            <Route path="/projects" element={<ProjectsPage />} />
            <Route path="/projects/new" element={<NewProjectPage />} />
            <Route path="/projects/:projectId/workflow" element={<ProjectWorkflowPage />} />
            <Route path="/documents" element={<DocumentsPage />} />
            <Route path="/personas" element={<PersonasPage />} />
            <Route path="/personas/:setId" element={<PersonaDetailPage />} />
            <Route path="/personas/:setId/:personaId" element={<PersonaDetailPage />} />
            <Route path="/simulations" element={<SimulationPage />} />
            <Route path="/simulations/:simulationId" element={<SimulationPage />} />
            <Route path="/prompts" element={<PromptsPage />} />
            <Route path="/reports" element={<ReportsPage />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;
