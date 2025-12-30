import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ChevronLeft, ChevronRight, User, MapPin, Briefcase, Target, AlertCircle, Smartphone, Quote, X, Download } from 'lucide-react';
import { personasApi } from '../services/api';
import { PersonaSet } from '../types';
import { getPersonaImageUrl } from '../utils/imageUtils';

export default function PersonaDetailPage() {
  const { setId, personaId } = useParams<{ setId: string; personaId?: string }>();
  const navigate = useNavigate();
  const [personaSet, setPersonaSet] = useState<PersonaSet | null>(null);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [loading, setLoading] = useState(true);
  const [generatingImages, setGeneratingImages] = useState<number[]>([]);
  const [imageErrors, setImageErrors] = useState<Set<number>>(new Set());

  useEffect(() => {
    loadPersonaSet();
  }, [setId]);

  useEffect(() => {
    if (personaId && personaSet) {
      const index = personaSet.personas.findIndex(p => p.id === parseInt(personaId));
      if (index >= 0) {
        setCurrentIndex(index);
      }
    }
  }, [personaId, personaSet]);

  const loadPersonaSet = async () => {
    if (!setId) return;
    setLoading(true);
    try {
      const set = await personasApi.getSet(parseInt(setId));
      setPersonaSet(set);
      // Generate images for all personas if they don't have images
      await generateMissingImages(set);
    } catch (error) {
      console.error('Failed to load persona set:', error);
    } finally {
      setLoading(false);
    }
  };

  const generateMissingImages = async (set: PersonaSet) => {
    const personasWithoutImages = set.personas.filter(p => !p.image_url);
    // Generate images for all personas without images
    const promises = personasWithoutImages.map(async (persona) => {
      try {
        setGeneratingImages(prev => [...prev, persona.id]);
        await personasApi.generateImage(persona.id);
      } catch (error) {
        console.error(`Failed to generate image for persona ${persona.id}:`, error);
      } finally {
        setGeneratingImages(prev => prev.filter(id => id !== persona.id));
      }
    });
    
    await Promise.all(promises);
    
    // Reload the set to get updated images
    if (setId) {
      const updatedSet = await personasApi.getSet(parseInt(setId));
      setPersonaSet(updatedSet);
    }
  };

  const handleGenerateImage = async (personaId: number) => {
    try {
      setGeneratingImages(prev => [...prev, personaId]);
      await personasApi.generateImage(personaId);
      const updatedSet = await personasApi.getSet(parseInt(setId!));
      setPersonaSet(updatedSet);
    } catch (error: any) {
      alert(`Failed to generate image: ${error.response?.data?.detail || error.message}`);
    } finally {
      setGeneratingImages(prev => prev.filter(id => id !== personaId));
    }
  };

  const handlePrevious = () => {
    if (personaSet && currentIndex > 0) {
      const newIndex = currentIndex - 1;
      setCurrentIndex(newIndex);
      navigate(`/personas/${setId}/${personaSet.personas[newIndex].id}`, { replace: true });
    }
  };

  const handleNext = () => {
    if (personaSet && currentIndex < personaSet.personas.length - 1) {
      const newIndex = currentIndex + 1;
      setCurrentIndex(newIndex);
      navigate(`/personas/${setId}/${personaSet.personas[newIndex].id}`, { replace: true });
    }
  };

  const handleDownload = () => {
    if (!personaSet) return;
    const dataStr = JSON.stringify(personaSet.personas, null, 2);
    const dataUri = 'data:application/json;charset=utf-8,' + encodeURIComponent(dataStr);
    const exportFileDefaultName = `personas_set_${personaSet.id}.json`;
    const linkElement = document.createElement('a');
    linkElement.setAttribute('href', dataUri);
    linkElement.setAttribute('download', exportFileDefaultName);
    linkElement.click();
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-white/80">Loading persona details...</div>
      </div>
    );
  }

  if (!personaSet || personaSet.personas.length === 0) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-white/80">No personas found</div>
      </div>
    );
  }

  const currentPersona = personaSet.personas[currentIndex];
  const personaData = currentPersona.persona_data || {};

  // Helper function to render key-value pairs
  const renderSection = (title: string, icon: React.ReactNode, data: any, isArray = false) => {
    if (!data || (isArray && (!Array.isArray(data) || data.length === 0))) return null;
    
    return (
      <div className="mb-6">
        <div className="flex items-center space-x-2 mb-3">
          {icon}
          <h5 className="text-sm font-semibold text-white uppercase tracking-wide">{title}</h5>
        </div>
        <div className="ml-7 space-y-2">
          {isArray && Array.isArray(data) ? (
            <ul className="list-disc list-inside space-y-1 text-sm text-white/90">
              {data.map((item: any, idx: number) => (
                <li key={idx}>{typeof item === 'string' ? item : JSON.stringify(item)}</li>
              ))}
            </ul>
          ) : typeof data === 'object' && data !== null ? (
            <div className="space-y-2">
              {Object.entries(data).map(([key, value]) => (
                <div key={key} className="flex">
                  <span className="text-white/70 font-medium min-w-[120px] capitalize">{key.replace(/_/g, ' ')}:</span>
                  <span className="text-white/90 flex-1">
                    {typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value)}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-white/90">{String(data)}</p>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className="min-h-screen px-4 py-6">
      {/* Header with Navigation */}
      <div className="glass-card rounded-2xl p-4 mb-6 pastel-purple">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <button
              onClick={() => navigate('/personas')}
              className="p-2 rounded-lg hover:bg-white/20 transition-colors"
            >
              <X className="h-5 w-5 text-white" />
            </button>
            <div>
              <h1 className="text-xl font-bold text-white">{personaSet.name}</h1>
              <p className="text-sm text-white/70">
                Persona {currentIndex + 1} of {personaSet.personas.length}
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={handleDownload}
              className="px-4 py-2 bg-white/20 text-white rounded-lg hover:bg-white/30 transition-colors flex items-center space-x-2"
            >
              <Download className="h-4 w-4" />
              <span>Download JSON</span>
            </button>
          </div>
        </div>
      </div>

      {/* Persona Navigation */}
      <div className="glass-card rounded-2xl p-4 mb-6 pastel-blue">
        <div className="flex items-center justify-between">
          <button
            onClick={handlePrevious}
            disabled={currentIndex === 0}
            className="flex items-center space-x-2 px-4 py-2 bg-white/20 text-white rounded-lg hover:bg-white/30 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <ChevronLeft className="h-5 w-5" />
            <span>Previous</span>
          </button>
          
          {/* Persona Thumbnails */}
          <div className="flex items-center space-x-2 flex-1 justify-center overflow-x-auto px-4">
            {personaSet.personas.map((persona, index) => (
              <button
                key={persona.id}
                onClick={() => {
                  setCurrentIndex(index);
                  navigate(`/personas/${setId}/${persona.id}`, { replace: true });
                }}
                className={`flex-shrink-0 w-16 h-16 rounded-lg overflow-hidden border-2 transition-all ${
                  index === currentIndex
                    ? 'border-white scale-110'
                    : 'border-white/30 hover:border-white/50'
                }`}
              >
                {persona.image_url && !imageErrors.has(persona.id) ? (
                  <img
                    src={getPersonaImageUrl(persona.image_url) || ''}
                    alt={persona.name}
                    className="w-full h-full object-cover"
                    onError={() => setImageErrors(prev => new Set(prev).add(persona.id))}
                  />
                ) : (
                  <div className="w-full h-full bg-white/10 flex items-center justify-center">
                    <span className="text-white/40 text-lg font-bold">
                      {(persona.persona_data?.name || persona.name).charAt(0).toUpperCase()}
                    </span>
                  </div>
                )}
              </button>
            ))}
          </div>

          <button
            onClick={handleNext}
            disabled={currentIndex === personaSet.personas.length - 1}
            className="flex items-center space-x-2 px-4 py-2 bg-white/20 text-white rounded-lg hover:bg-white/30 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <span>Next</span>
            <ChevronRight className="h-5 w-5" />
          </button>
        </div>
      </div>

      {/* Expanded Persona Card */}
      <div className="glass-card rounded-2xl p-6 border border-white/20 pastel-blue max-w-7xl mx-auto">
        {/* Header with Image, Demographics, Quote and Overview */}
        <div className="flex gap-6 mb-4 pb-4 border-b border-white/20">
          {/* Left: Image and Demographics */}
          <div className="flex gap-4">
            {/* Persona Image */}
            <div className="flex-shrink-0">
              {currentPersona.image_url && !imageErrors.has(currentPersona.id) ? (
                <img
                  src={getPersonaImageUrl(currentPersona.image_url) || ''}
                  alt={currentPersona.name}
                  className="w-32 h-32 object-cover rounded-xl border-4 border-white/30 shadow-lg"
                  onError={() => setImageErrors(prev => new Set(prev).add(currentPersona.id))}
                />
              ) : (
                <div className="w-32 h-32 rounded-xl border-4 border-white/30 bg-white/10 flex items-center justify-center relative">
                  <span className="text-white/40 text-4xl font-bold">
                    {(personaData.name || currentPersona.name).charAt(0).toUpperCase()}
                  </span>
                  {generatingImages.includes(currentPersona.id) ? (
                    <div className="absolute inset-0 bg-black/50 rounded-xl flex items-center justify-center">
                      <div className="text-white text-xs">Generating...</div>
                    </div>
                  ) : (
                    <button
                      onClick={() => handleGenerateImage(currentPersona.id)}
                      className="absolute inset-0 bg-black/50 rounded-xl flex items-center justify-center opacity-0 hover:opacity-100 transition-opacity"
                    >
                      <span className="text-white text-xs">Generate</span>
                    </button>
                  )}
                </div>
              )}
            </div>
            
            {/* Demographics - Four Rows */}
            <div className="flex flex-col justify-center space-y-2 min-w-[200px]">
              <h4 className="text-2xl font-bold text-white mb-2">{personaData.name || currentPersona.name}</h4>
              {(personaData.age || personaData.demographics?.age) && (
                <div className="flex items-center space-x-2 text-sm text-white/90">
                  <User className="h-4 w-4 text-white/70" />
                  <span><strong>Age:</strong> {personaData.age || personaData.demographics?.age}</span>
                </div>
              )}
              {(personaData.location || personaData.demographics?.location) && (
                <div className="flex items-center space-x-2 text-sm text-white/90">
                  <MapPin className="h-4 w-4 text-white/70" />
                  <span className="truncate">
                    <strong>Location:</strong> {
                      typeof (personaData.location || personaData.demographics?.location) === 'string' 
                        ? (personaData.location || personaData.demographics?.location)
                        : (personaData.demographics?.location && typeof personaData.demographics.location === 'object' && 'city' in personaData.demographics.location && 'country' in personaData.demographics.location
                          ? `${personaData.demographics.location.city}, ${personaData.demographics.location.country}`
                          : (personaData.location && typeof personaData.location === 'object' && 'city' in personaData.location && 'country' in personaData.location
                            ? `${(personaData.location as any).city}, ${(personaData.location as any).country}`
                            : JSON.stringify(personaData.location || personaData.demographics?.location)))
                    }
                  </span>
                </div>
              )}
              {(personaData.occupation || personaData.demographics?.occupation) && (
                <div className="flex items-center space-x-2 text-sm text-white/90">
                  <Briefcase className="h-4 w-4 text-white/70" />
                  <span className="truncate"><strong>Occupation:</strong> {personaData.occupation || personaData.demographics?.occupation}</span>
                </div>
              )}
              {(personaData.gender || personaData.demographics?.gender) && (
                <div className="flex items-center space-x-2 text-sm text-white/90">
                  <User className="h-4 w-4 text-white/70" />
                  <span><strong>Gender:</strong> {personaData.gender || personaData.demographics?.gender}</span>
                </div>
              )}
            </div>
          </div>

          {/* Right: Quote and Overview */}
          <div className="flex-1 space-y-3">
            {personaData.quote && (
              <div className="p-3 bg-white/10 rounded-lg border-l-4 border-purple-400">
                <div className="flex items-start space-x-2">
                  <Quote className="h-4 w-4 text-purple-300 flex-shrink-0 mt-0.5" />
                  <p className="text-sm text-white/90 italic leading-relaxed">"{personaData.quote}"</p>
                </div>
              </div>
            )}
            {(personaData.basic_description || personaData.tagline) && (
              <div>
                <h5 className="text-xs font-semibold text-white uppercase tracking-wide mb-2">Overview</h5>
                <p className="text-sm text-white/90 leading-relaxed">{personaData.basic_description || personaData.tagline}</p>
              </div>
            )}
          </div>
        </div>

        {/* Details Section - 2x2 Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 max-h-[calc(100vh-380px)] overflow-y-auto pr-2">
          {/* Top Left: Background */}
          <div>
            {renderSection(
              'Background',
              <User className="h-3 w-3 text-white/70" />,
              personaData.background || personaData.detailed_description || personaData.personal_background
            )}
          </div>

          {/* Top Right: Technology Profile */}
          <div>
            {personaData.technology_profile && (
              <div className="mb-4">
                <div className="flex items-center space-x-1 mb-2">
                  <Smartphone className="h-3 w-3 text-white/70" />
                  <h5 className="text-xs font-semibold text-white uppercase tracking-wide">Technology Profile</h5>
                </div>
                <div className="ml-4 space-y-1.5">
                  {personaData.technology_profile.primary_devices && (
                    <div>
                      <span className="text-xs text-white/70 font-medium">Devices:</span>
                      <div className="flex flex-wrap gap-1 mt-0.5">
                        {personaData.technology_profile.primary_devices.map((device: string, idx: number) => (
                          <span key={idx} className="px-1.5 py-0.5 bg-white/20 rounded text-xs text-white/90">{device}</span>
                        ))}
                      </div>
                    </div>
                  )}
                  {personaData.technology_profile.comfort_level && (
                    <div className="text-xs">
                      <span className="text-white/70 font-medium">Level:</span>
                      <span className="ml-1 text-white/90">{personaData.technology_profile.comfort_level}</span>
                    </div>
                  )}
                  {personaData.technology_profile.software_used && (
                    <div>
                      <span className="text-xs text-white/70 font-medium">Software:</span>
                      <div className="flex flex-wrap gap-1 mt-0.5">
                        {personaData.technology_profile.software_used.map((software: string, idx: number) => (
                          <span key={idx} className="px-1.5 py-0.5 bg-white/20 rounded text-xs text-white/90">{software}</span>
                        ))}
                      </div>
                    </div>
                  )}
                  {personaData.technology_profile.interaction_preferences && (
                    <div>
                      <span className="text-xs text-white/70 font-medium">Preferences:</span>
                      <ul className="list-disc list-inside space-y-0.5 mt-0.5 text-xs text-white/90">
                        {personaData.technology_profile.interaction_preferences.map((pref: string, idx: number) => (
                          <li key={idx} className="leading-tight">{pref}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {personaData.technology_profile.accessibility_needs && personaData.technology_profile.accessibility_needs.length > 0 && (
                    <div>
                      <span className="text-xs text-white/70 font-medium">Accessibility:</span>
                      <ul className="list-disc list-inside space-y-0.5 mt-0.5 text-xs text-white/90">
                        {personaData.technology_profile.accessibility_needs.map((need: string, idx: number) => (
                          <li key={idx} className="leading-tight">{need}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Bottom Left: Goals */}
          <div>
            {renderSection(
              'Goals',
              <Target className="h-3 w-3 text-white/70" />,
              personaData.goals,
              true
            )}
          </div>

          {/* Bottom Right: Frustrations */}
          <div>
            {renderSection(
              'Frustrations',
              <AlertCircle className="h-3 w-3 text-white/70" />,
              personaData.frustrations,
              true
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

