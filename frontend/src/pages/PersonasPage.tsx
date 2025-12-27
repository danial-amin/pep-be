import { useState, useEffect } from 'react';
import { Users, Plus, Sparkles, Image as ImageIcon, Save, Eye } from 'lucide-react';
import { personasApi } from '../services/api';
import { PersonaSet, PersonaSetGenerateResponse, Persona } from '../types';

export default function PersonasPage() {
  const [personaSets, setPersonaSets] = useState<PersonaSet[]>([]);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [expanding, setExpanding] = useState<number | null>(null);
  const [generatingImages, setGeneratingImages] = useState<number | null>(null);
  const [selectedSet, setSelectedSet] = useState<PersonaSet | null>(null);
  const [numPersonas, setNumPersonas] = useState(3);

  useEffect(() => {
    loadPersonaSets();
  }, []);

  const loadPersonaSets = async () => {
    setLoading(true);
    try {
      const data = await personasApi.getAllSets();
      setPersonaSets(data);
    } catch (error) {
      console.error('Failed to load persona sets:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateSet = async () => {
    setGenerating(true);
    try {
      const response: PersonaSetGenerateResponse = await personasApi.generateSet(numPersonas);
      await loadPersonaSets();
      const newSet = await personasApi.getSet(response.persona_set_id);
      setSelectedSet(newSet);
      alert('Persona set generated successfully!');
    } catch (error: any) {
      alert(`Failed to generate personas: ${error.response?.data?.detail || error.message}`);
    } finally {
      setGenerating(false);
    }
  };

  const handleExpand = async (personaSetId: number) => {
    setExpanding(personaSetId);
    try {
      await personasApi.expand(personaSetId);
      await loadPersonaSets();
      if (selectedSet?.id === personaSetId) {
        const updated = await personasApi.getSet(personaSetId);
        setSelectedSet(updated);
      }
      alert('Personas expanded successfully!');
    } catch (error: any) {
      alert(`Failed to expand personas: ${error.response?.data?.detail || error.message}`);
    } finally {
      setExpanding(null);
    }
  };

  const handleGenerateImages = async (personaSetId: number) => {
    setGeneratingImages(personaSetId);
    try {
      await personasApi.generateImages(personaSetId);
      await loadPersonaSets();
      if (selectedSet?.id === personaSetId) {
        const updated = await personasApi.getSet(personaSetId);
        setSelectedSet(updated);
      }
      alert('Images generated successfully!');
    } catch (error: any) {
      alert(`Failed to generate images: ${error.response?.data?.detail || error.message}`);
    } finally {
      setGeneratingImages(null);
    }
  };

  const handleSaveSet = async (personaSetId: number, name: string, description?: string) => {
    try {
      await personasApi.saveSet(personaSetId, name, description);
      await loadPersonaSets();
      alert('Persona set saved successfully!');
    } catch (error: any) {
      alert(`Failed to save persona set: ${error.response?.data?.detail || error.message}`);
    }
  };

  const handleViewSet = async (personaSetId: number) => {
    try {
      const set = await personasApi.getSet(personaSetId);
      setSelectedSet(set);
    } catch (error: any) {
      alert(`Failed to load persona set: ${error.response?.data?.detail || error.message}`);
    }
  };

  return (
    <div className="px-4 py-6 sm:px-0">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Personas</h2>
        <p className="text-gray-600">Generate and manage user personas from your documents</p>
      </div>

      {/* Generate New Persona Set */}
      <div className="bg-white shadow rounded-lg p-6 mb-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Generate New Persona Set</h3>
        <div className="flex items-center space-x-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Number of Personas
            </label>
            <input
              type="number"
              min="1"
              max="10"
              value={numPersonas}
              onChange={(e) => setNumPersonas(parseInt(e.target.value) || 3)}
              className="w-24 px-3 py-2 border border-gray-300 rounded-md"
            />
          </div>
          <button
            onClick={handleGenerateSet}
            disabled={generating}
            className="mt-6 inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50"
          >
            <Plus className="mr-2 h-4 w-4" />
            {generating ? 'Generating...' : 'Generate Personas'}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Persona Sets List */}
        <div className="bg-white shadow rounded-lg">
          <div className="px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-medium text-gray-900">Persona Sets</h3>
          </div>
          <div className="divide-y divide-gray-200">
            {loading ? (
              <div className="px-6 py-8 text-center text-gray-500">Loading...</div>
            ) : personaSets.length === 0 ? (
              <div className="px-6 py-8 text-center text-gray-500">
                No persona sets found. Generate your first set above.
              </div>
            ) : (
              personaSets.map((set) => (
                <div key={set.id} className="px-6 py-4">
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="text-sm font-medium text-gray-900">
                      {set.name || `Persona Set #${set.id}`}
                    </h4>
                    <button
                      onClick={() => handleViewSet(set.id)}
                      className="text-blue-600 hover:text-blue-700 text-sm"
                    >
                      <Eye className="h-4 w-4" />
                    </button>
                  </div>
                  <p className="text-sm text-gray-500 mb-3">
                    {set.description || 'No description'}
                  </p>
                  <div className="flex items-center space-x-2">
                    <span className="text-xs text-gray-500">
                      {set.personas.length} persona{set.personas.length !== 1 ? 's' : ''}
                    </span>
                    <span className="text-xs text-gray-400">•</span>
                    <span className="text-xs text-gray-500">
                      {new Date(set.created_at).toLocaleDateString()}
                    </span>
                  </div>
                  <div className="mt-3 flex space-x-2">
                    <button
                      onClick={() => handleExpand(set.id)}
                      disabled={expanding === set.id}
                      className="text-xs px-2 py-1 bg-purple-100 text-purple-700 rounded hover:bg-purple-200 disabled:opacity-50"
                    >
                      <Sparkles className="inline h-3 w-3 mr-1" />
                      {expanding === set.id ? 'Expanding...' : 'Expand'}
                    </button>
                    <button
                      onClick={() => handleGenerateImages(set.id)}
                      disabled={generatingImages === set.id}
                      className="text-xs px-2 py-1 bg-pink-100 text-pink-700 rounded hover:bg-pink-200 disabled:opacity-50"
                    >
                      <ImageIcon className="inline h-3 w-3 mr-1" />
                      {generatingImages === set.id ? 'Generating...' : 'Images'}
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Selected Persona Set Details */}
        <div className="bg-white shadow rounded-lg">
          <div className="px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-medium text-gray-900">Persona Details</h3>
          </div>
          <div className="p-6">
            {selectedSet ? (
              <div className="space-y-6">
                {selectedSet.personas.map((persona) => (
                  <div key={persona.id} className="border border-gray-200 rounded-lg p-4">
                    <div className="flex items-start space-x-4">
                      {persona.image_url && (
                        <img
                          src={persona.image_url}
                          alt={persona.name}
                          className="w-24 h-24 object-cover rounded-lg"
                        />
                      )}
                      <div className="flex-1">
                        <h4 className="text-lg font-semibold text-gray-900">{persona.name}</h4>
                        <div className="mt-2 space-y-1 text-sm text-gray-600">
                          {persona.persona_data.age && (
                            <p>Age: {persona.persona_data.age}</p>
                          )}
                          {persona.persona_data.occupation && (
                            <p>Occupation: {persona.persona_data.occupation}</p>
                          )}
                          {persona.persona_data.location && (
                            <p>Location: {persona.persona_data.location}</p>
                          )}
                          {persona.persona_data.detailed_description && (
                            <p className="mt-2">{persona.persona_data.detailed_description}</p>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center text-gray-500 py-8">
                Select a persona set to view details
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

