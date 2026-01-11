import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, FolderOpen, ArrowRight } from 'lucide-react';
import { projectsApi } from '../services/api';
import { Project } from '../types';

export default function ProjectsPage() {
  const navigate = useNavigate();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadProjects();
  }, []);

  const loadProjects = async () => {
    setLoading(true);
    try {
      const data = await projectsApi.getAll();
      setProjects(data);
    } catch (error) {
      console.error('Failed to load projects:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="px-4 py-6 sm:px-0">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold text-white mb-2 drop-shadow-lg">Projects</h2>
          <p className="text-white/80 text-lg">Manage your persona generation projects</p>
        </div>
        <button
          onClick={() => navigate('/projects/new')}
          className="inline-flex items-center px-6 py-3 border border-transparent text-sm font-medium rounded-xl text-white bg-gradient-to-r from-purple-400 via-pink-400 to-rose-400 hover:from-purple-500 hover:via-pink-500 hover:to-rose-500 transition-all duration-200 shadow-lg hover:shadow-xl hover:scale-105"
        >
          <Plus className="mr-2 h-5 w-5" />
          New Project
        </button>
      </div>

      {loading ? (
        <div className="text-center text-white/80 py-12">Loading projects...</div>
      ) : projects.length === 0 ? (
        <div className="glass-card rounded-2xl p-12 text-center">
          <FolderOpen className="mx-auto h-16 w-16 text-white/40 mb-4" />
          <h3 className="text-xl font-semibold text-white mb-2">No projects yet</h3>
          <p className="text-white/70 mb-6">Create your first project to start generating personas</p>
          <button
            onClick={() => navigate('/projects/new')}
            className="inline-flex items-center px-6 py-3 border border-transparent text-sm font-medium rounded-xl text-white bg-gradient-to-r from-purple-400 via-pink-400 to-rose-400 hover:from-purple-500 hover:via-pink-500 hover:to-rose-500 transition-all duration-200 shadow-lg hover:shadow-xl hover:scale-105"
          >
            <Plus className="mr-2 h-5 w-5" />
            Create Project
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {projects.map((project) => (
            <div
              key={project.id}
              className="glass-card rounded-2xl p-6 hover:scale-105 transition-all duration-200 cursor-pointer pastel-blue"
              onClick={() => navigate(`/projects/${project.id}/workflow`)}
            >
              <div className="flex items-start justify-between mb-4">
                <FolderOpen className="h-8 w-8 text-white/90" />
                <ArrowRight className="h-5 w-5 text-white/60" />
              </div>
              <h3 className="text-xl font-semibold text-white mb-2">{project.name}</h3>
              {project.field_of_study && (
                <p className="text-sm text-white/70 mb-2">
                  <span className="font-medium">Field:</span> {project.field_of_study}
                </p>
              )}
              {project.core_objective && (
                <p className="text-sm text-white/60 mb-4 line-clamp-2">{project.core_objective}</p>
              )}
              <div className="flex items-center space-x-4 text-xs text-white/60">
                <span className={project.includes_context ? 'text-green-400' : 'text-white/40'}>
                  {project.includes_context ? '✓ Context' : '✗ Context'}
                </span>
                <span className={project.includes_interviews ? 'text-green-400' : 'text-white/40'}>
                  {project.includes_interviews ? '✓ Interviews' : '✗ Interviews'}
                </span>
              </div>
              <p className="text-xs text-white/50 mt-4">
                Created {new Date(project.created_at).toLocaleDateString()}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
