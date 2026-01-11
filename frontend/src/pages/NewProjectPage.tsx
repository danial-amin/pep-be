import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Save } from 'lucide-react';
import { projectsApi } from '../services/api';

export default function NewProjectPage() {
  const navigate = useNavigate();
  const [name, setName] = useState('');
  const [fieldOfStudy, setFieldOfStudy] = useState('');
  const [coreObjective, setCoreObjective] = useState('');
  const [includesContext, setIncludesContext] = useState(true);
  const [includesInterviews, setIncludesInterviews] = useState(true);
  const [creating, setCreating] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      alert('Please enter a project name');
      return;
    }

    setCreating(true);
    try {
      const project = await projectsApi.create({
        name: name.trim(),
        field_of_study: fieldOfStudy.trim() || undefined,
        core_objective: coreObjective.trim() || undefined,
        includes_context: includesContext,
        includes_interviews: includesInterviews,
      });
      navigate(`/projects/${project.id}/workflow`);
    } catch (error: any) {
      alert(`Failed to create project: ${error.response?.data?.detail || error.message}`);
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="px-4 py-6 sm:px-0 max-w-3xl mx-auto">
      <button
        onClick={() => navigate('/projects')}
        className="mb-6 inline-flex items-center text-white/80 hover:text-white transition-colors"
      >
        <ArrowLeft className="mr-2 h-4 w-4" />
        Back to Projects
      </button>

      <div className="mb-6">
        <h2 className="text-3xl font-bold text-white mb-2 drop-shadow-lg">Create New Project</h2>
        <p className="text-white/80 text-lg">Set up a new persona generation project</p>
      </div>

      <form onSubmit={handleSubmit} className="glass-card rounded-2xl p-6 space-y-6">
        <div>
          <label className="block text-sm font-medium text-white/90 mb-2">
            Project Name <span className="text-red-400">*</span>
          </label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g., Finnish Electric Vehicle Transition"
            required
            className="w-full px-4 py-3 bg-white/20 border border-white/30 rounded-xl text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-white/50"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-white/90 mb-2">
            Field of Study
          </label>
          <input
            type="text"
            value={fieldOfStudy}
            onChange={(e) => setFieldOfStudy(e.target.value)}
            placeholder="e.g., Electric Vehicle Transition, Healthcare AI, User Experience"
            className="w-full px-4 py-3 bg-white/20 border border-white/30 rounded-xl text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-white/50"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-white/90 mb-2">
            Core Objective
          </label>
          <textarea
            value={coreObjective}
            onChange={(e) => setCoreObjective(e.target.value)}
            placeholder="Describe the main objective for generating personas in this project..."
            rows={4}
            className="w-full px-4 py-3 bg-white/20 border border-white/30 rounded-xl text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-white/50"
          />
        </div>

        <div className="space-y-4">
          <h3 className="text-lg font-semibold text-white">Document Types</h3>
          <p className="text-sm text-white/70">Select which types of documents this project will use:</p>
          
          <div className="flex items-center space-x-3">
            <input
              type="checkbox"
              id="includes_context"
              checked={includesContext}
              onChange={(e) => setIncludesContext(e.target.checked)}
              className="h-5 w-5 text-purple-400 focus:ring-purple-300 border-white/30 rounded bg-white/20"
            />
            <label htmlFor="includes_context" className="text-white/90">
              Context Documents (research, reports, background information)
            </label>
          </div>

          <div className="flex items-center space-x-3">
            <input
              type="checkbox"
              id="includes_interviews"
              checked={includesInterviews}
              onChange={(e) => setIncludesInterviews(e.target.checked)}
              className="h-5 w-5 text-purple-400 focus:ring-purple-300 border-white/30 rounded bg-white/20"
            />
            <label htmlFor="includes_interviews" className="text-white/90">
              Interview Documents (transcripts, user research)
            </label>
          </div>

          {!includesContext && !includesInterviews && (
            <p className="text-sm text-yellow-400">
              ⚠ At least one document type must be selected
            </p>
          )}
        </div>

        <div className="flex space-x-4 pt-4">
          <button
            type="button"
            onClick={() => navigate('/projects')}
            className="px-6 py-3 border border-white/30 text-white rounded-xl hover:bg-white/20 transition-all duration-200"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={creating || (!includesContext && !includesInterviews)}
            className="flex-1 inline-flex items-center justify-center px-6 py-3 border border-transparent text-sm font-medium rounded-xl text-white bg-gradient-to-r from-purple-400 via-pink-400 to-rose-400 hover:from-purple-500 hover:via-pink-500 hover:to-rose-500 disabled:opacity-50 transition-all duration-200 shadow-lg hover:shadow-xl hover:scale-105"
          >
            <Save className="mr-2 h-4 w-4" />
            {creating ? 'Creating...' : 'Create Project'}
          </button>
        </div>
      </form>
    </div>
  );
}
