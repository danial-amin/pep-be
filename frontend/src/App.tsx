import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import { FileText, Users, MessageSquare, BarChart3 } from 'lucide-react';
import DocumentsPage from './pages/DocumentsPage';
import PersonasPage from './pages/PersonasPage';
import PersonaDetailPage from './pages/PersonaDetailPage';
import PromptsPage from './pages/PromptsPage';
import ReportsPage from './pages/ReportsPage';

function App() {
  return (
    <Router>
      <div className="min-h-screen">
        {/* Navigation */}
        <nav className="glass-strong sticky top-0 z-50">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between h-16">
              <div className="flex">
                <div className="flex-shrink-0 flex items-center">
                  <h1 className="text-2xl font-bold bg-gradient-to-r from-pink-400 via-purple-400 to-blue-400 bg-clip-text text-transparent">
                    PEP
                  </h1>
                  <span className="ml-2 text-sm text-white/90 font-medium">Persona Generator</span>
                </div>
                <div className="hidden sm:ml-6 sm:flex sm:space-x-8">
                  <Link
                    to="/"
                    className="inline-flex items-center px-3 py-2 text-sm font-medium text-white/90 rounded-lg hover:bg-white/20 transition-all duration-200 hover:scale-105"
                  >
                    <FileText className="mr-2 h-4 w-4" />
                    Documents
                  </Link>
                  <Link
                    to="/personas"
                    className="inline-flex items-center px-3 py-2 text-sm font-medium text-white/90 rounded-lg hover:bg-white/20 transition-all duration-200 hover:scale-105"
                  >
                    <Users className="mr-2 h-4 w-4" />
                    Personas
                  </Link>
                  <Link
                    to="/prompts"
                    className="inline-flex items-center px-3 py-2 text-sm font-medium text-white/90 rounded-lg hover:bg-white/20 transition-all duration-200 hover:scale-105"
                  >
                    <MessageSquare className="mr-2 h-4 w-4" />
                    Q&A Prompts
                  </Link>
                  <Link
                    to="/reports"
                    className="inline-flex items-center px-3 py-2 text-sm font-medium text-white/90 rounded-lg hover:bg-white/20 transition-all duration-200 hover:scale-105"
                  >
                    <BarChart3 className="mr-2 h-4 w-4" />
                    Reports
                  </Link>
                </div>
              </div>
            </div>
          </div>
        </nav>

        {/* Main Content */}
        <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
          <Routes>
            <Route path="/" element={<DocumentsPage />} />
            <Route path="/personas" element={<PersonasPage />} />
            <Route path="/personas/:setId" element={<PersonaDetailPage />} />
            <Route path="/personas/:setId/:personaId" element={<PersonaDetailPage />} />
            <Route path="/prompts" element={<PromptsPage />} />
            <Route path="/reports" element={<ReportsPage />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;

