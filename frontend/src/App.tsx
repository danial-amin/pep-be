import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import { FileText, Users, MessageSquare } from 'lucide-react';
import DocumentsPage from './pages/DocumentsPage';
import PersonasPage from './pages/PersonasPage';
import PromptsPage from './pages/PromptsPage';

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-gray-50">
        {/* Navigation */}
        <nav className="bg-white shadow-sm border-b">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between h-16">
              <div className="flex">
                <div className="flex-shrink-0 flex items-center">
                  <h1 className="text-xl font-bold text-gray-900">PEP</h1>
                  <span className="ml-2 text-sm text-gray-500">Persona Generator</span>
                </div>
                <div className="hidden sm:ml-6 sm:flex sm:space-x-8">
                  <Link
                    to="/"
                    className="inline-flex items-center px-1 pt-1 text-sm font-medium text-gray-900 border-b-2 border-transparent hover:border-gray-300 hover:text-gray-700"
                  >
                    <FileText className="mr-2 h-4 w-4" />
                    Documents
                  </Link>
                  <Link
                    to="/personas"
                    className="inline-flex items-center px-1 pt-1 text-sm font-medium text-gray-500 border-b-2 border-transparent hover:border-gray-300 hover:text-gray-700"
                  >
                    <Users className="mr-2 h-4 w-4" />
                    Personas
                  </Link>
                  <Link
                    to="/prompts"
                    className="inline-flex items-center px-1 pt-1 text-sm font-medium text-gray-500 border-b-2 border-transparent hover:border-gray-300 hover:text-gray-700"
                  >
                    <MessageSquare className="mr-2 h-4 w-4" />
                    Prompts
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
            <Route path="/prompts" element={<PromptsPage />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;

