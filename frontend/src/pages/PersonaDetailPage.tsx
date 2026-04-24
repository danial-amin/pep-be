import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ChevronLeft, ChevronRight, User, MapPin, Briefcase, Target, AlertCircle, Smartphone, Quote, X, Download, Image as ImageIcon, FileJson } from 'lucide-react';
import { personasApi } from '../services/api';
import { PersonaSet } from '../types';
import { getPersonaImageUrl } from '../utils/imageUtils';
import html2canvas from 'html2canvas';

export default function PersonaDetailPage() {
  const { setId, personaId } = useParams<{ setId: string; personaId?: string }>();
  const navigate = useNavigate();
  const [personaSet, setPersonaSet] = useState<PersonaSet | null>(null);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [loading, setLoading] = useState(true);
  const [generatingImages, setGeneratingImages] = useState<number[]>([]);
  const [imageErrors, setImageErrors] = useState<Set<number>>(new Set());
  const [downloadingProfile, setDownloadingProfile] = useState(false);
  const profileCardRef = useRef<HTMLDivElement>(null);

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

  const sanitizeFilename = (name: string) =>
    name.replace(/[^a-z0-9]/gi, '_').toLowerCase() || 'persona';

  const handleDownloadFullSetJson = async () => {
    if (!personaSet) return;
    try {
      const blob = await personasApi.downloadJson(personaSet.id);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `persona_set_${personaSet.id}.json`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error: any) {
      alert(`Failed to download: ${error.response?.data?.detail || error.message}`);
    }
  };

  const handleDownloadCurrentPersonaJson = () => {
    if (!personaSet) return;
    const p = personaSet.personas[currentIndex];
    const blob = new Blob([JSON.stringify(p, null, 2)], { type: 'application/json' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    const label = sanitizeFilename(p.persona_data?.name || p.name || `persona_${p.id}`);
    a.download = `${label}_${p.id}.json`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  };

  const preloadImages = (element: HTMLElement): Promise<void> => {
    return new Promise((resolve) => {
      const images = element.querySelectorAll('img');
      if (images.length === 0) {
        resolve();
        return;
      }
      
      let loaded = 0;
      const total = images.length;
      
      const checkComplete = () => {
        loaded++;
        if (loaded === total) {
          resolve();
        }
      };
      
      images.forEach((img) => {
        if (img.complete) {
          checkComplete();
        } else {
          img.onload = checkComplete;
          img.onerror = checkComplete; // Continue even if image fails
          // Force reload if src is set
          if (img.src) {
            const src = img.src;
            img.src = '';
            img.src = src;
          }
        }
      });
      
      // Timeout after 5 seconds
      setTimeout(() => {
        resolve();
      }, 5000);
    });
  };

  const handleDownloadProfileImage = async () => {
    if (!profileCardRef.current || downloadingProfile) return;

    const currentPersona = personaSet?.personas[currentIndex];
    if (!currentPersona) return;

    const sourceEl = profileCardRef.current;

    setDownloadingProfile(true);
    try {
      await preloadImages(sourceEl);
      sourceEl.scrollIntoView({ block: 'nearest', inline: 'nearest' });
      await new Promise((resolve) => setTimeout(resolve, 150));

      // Width at capture time so line breaks match the profile card as laid out on screen
      const captureWidthPx = Math.max(320, Math.ceil(sourceEl.getBoundingClientRect().width));

      // Create a temporary wrapper so the exported image has a consistent solid background.
      const exportBg = '#0b1220'; // deep navy, prints well and keeps good contrast
      const wrapper = document.createElement('div');
      wrapper.style.position = 'fixed';
      wrapper.style.left = '-10000px';
      wrapper.style.top = '0';
      wrapper.style.padding = '24px';
      wrapper.style.width = `${captureWidthPx + 48}px`;
      wrapper.style.background = exportBg;
      wrapper.style.borderRadius = '24px';
      wrapper.style.boxSizing = 'border-box';

      const clone = sourceEl.cloneNode(true) as HTMLElement;
      clone.style.width = `${captureWidthPx}px`;
      clone.style.maxWidth = 'none';
      clone.style.boxSizing = 'border-box';
      wrapper.appendChild(clone);
      document.body.appendChild(wrapper);

      let canvas: HTMLCanvasElement;
      try {
        canvas = await html2canvas(wrapper, {
          backgroundColor: exportBg,
        scale: Math.min(2.5, Math.max(2, window.devicePixelRatio || 2)),
        useCORS: true,
        allowTaint: true,
        logging: false,
        imageTimeout: 20000,
        removeContainer: false,
        foreignObjectRendering: false,
        scrollX: 0,
        scrollY: 0,
        onclone: (_doc: Document, cloned: HTMLElement) => {
          // Hide export-only UI (e.g. image generation overlay)
          cloned.querySelectorAll('.persona-export-hide').forEach((el: Element) => {
            (el as HTMLElement).style.display = 'none';
          });

          // Ensure long fields wrap (avoid ellipsis/truncation in export)
          cloned.querySelectorAll('.persona-export-text').forEach((el: Element) => {
            const node = el as HTMLElement;
            node.style.whiteSpace = 'normal';
            node.style.overflow = 'visible';
            node.style.textOverflow = 'clip';
            node.style.wordBreak = 'break-word';
          });

          // html2canvas does not rasterize backdrop-filter reliably; approximate the real card look
          const exportedCard = cloned.querySelector(
            '[data-persona-profile-card="true"]'
          ) as HTMLElement | null;
          if (exportedCard) {
            exportedCard.style.backdropFilter = 'none';
            exportedCard.style.setProperty('-webkit-backdrop-filter', 'none');
            exportedCard.style.background =
              'linear-gradient(135deg, rgba(255, 255, 255, 0.34) 0%, rgba(255, 255, 255, 0.22) 100%), linear-gradient(135deg, rgba(173, 216, 230, 0.42), rgba(176, 224, 230, 0.28))';
            exportedCard.style.backgroundColor = 'rgba(255, 255, 255, 0.25)';
            exportedCard.style.border = '1px solid rgba(255, 255, 255, 0.45)';
            exportedCard.style.boxShadow = '0 8px 32px 0 rgba(31, 38, 135, 0.22)';
          }
        },
        } as any);
      } finally {
        if (wrapper.parentNode) {
          wrapper.parentNode.removeChild(wrapper);
        }
      }
      
      // Convert to blob and download
      canvas.toBlob((blob) => {
        if (!blob) {
          console.error('Failed to create blob');
          setDownloadingProfile(false);
          return;
        }
        
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        const personaName = sanitizeFilename(
          currentPersona.persona_data?.name || currentPersona.name || `persona_${currentPersona.id}`
        );
        link.download = `${personaName}_profile.png`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
        setDownloadingProfile(false);
      }, 'image/png', 1.0); // Maximum quality
    } catch (error) {
      console.error('Error capturing profile image:', error);
      setDownloadingProfile(false);
    }
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

  // Helper function to safely convert any value to string for rendering
  const safeString = (value: any): string => {
    if (value === null || value === undefined) return '';
    if (typeof value === 'string') return value;
    if (typeof value === 'number' || typeof value === 'boolean') return String(value);
    if (Array.isArray(value)) {
      return value.map(item => safeString(item)).join(', ');
    }
    if (typeof value === 'object') {
      // Try to extract meaningful text fields first
      if ('text' in value && typeof value.text === 'string') return value.text;
      if ('description' in value && typeof value.description === 'string') return value.description;
      if ('content' in value && typeof value.content === 'string') return value.content;
      // Otherwise stringify
      try {
        return JSON.stringify(value);
      } catch {
        return String(value);
      }
    }
    return String(value);
  };

  // Helper function to get field value from nested structure
  const getField = (fieldName: string, fallback?: string) => {
    // All personas now use nested structure with demographics object
    if (fieldName === 'age' || fieldName === 'gender' || fieldName === 'occupation' || 
        fieldName === 'location' || fieldName === 'education' || fieldName === 'nationality' ||
        fieldName === 'income_bracket' || fieldName === 'relationship_status') {
      return personaData.demographics?.[fieldName] || fallback;
    }
    // Top-level fields
    return personaData[fieldName] || fallback;
  };

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
          ) : typeof data === 'object' && data !== null && !Array.isArray(data) ? (
            <div className="space-y-2">
              {Object.entries(data).map(([key, value]) => (
                <div key={key} className="flex flex-col gap-0.5 sm:flex-row sm:gap-2">
                  <span className="shrink-0 font-medium capitalize text-white/70 sm:min-w-[8.5rem]">
                    {key.replace(/_/g, ' ')}:
                  </span>
                  <span className="min-w-0 flex-1 break-words text-white/90">
                    {(() => {
                      if (value === null || value === undefined) return String(value || '');
                      if (typeof value === 'object') {
                        if (Array.isArray(value)) {
                          return value.map(String).join(', ');
                        }
                        return JSON.stringify(value, null, 2);
                      }
                      return String(value);
                    })()}
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
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex min-w-0 items-center gap-3 sm:gap-4">
            <button
              type="button"
              onClick={() => navigate('/personas')}
              className="flex-shrink-0 rounded-lg p-2 transition-colors hover:bg-white/20"
            >
              <X className="h-5 w-5 text-white" />
            </button>
            <div className="min-w-0">
              <h1 className="truncate text-lg font-bold text-white sm:text-xl">{personaSet.name}</h1>
              <p className="text-sm text-white/70">
                Persona {currentIndex + 1} of {personaSet.personas.length}
              </p>
            </div>
          </div>
          <div className="flex flex-wrap items-stretch justify-start gap-2 sm:justify-end">
            <button
              type="button"
              onClick={handleDownloadProfileImage}
              disabled={downloadingProfile}
              className="inline-flex flex-1 items-center justify-center gap-2 rounded-lg bg-white/20 px-3 py-2.5 text-left text-sm text-white transition-colors hover:bg-white/30 disabled:cursor-not-allowed disabled:opacity-50 sm:flex-initial sm:px-4"
            >
              <ImageIcon className="h-4 w-4 flex-shrink-0" />
              <span className="leading-snug">
                {downloadingProfile ? 'Saving…' : 'Download profile as image'}
              </span>
            </button>
            <button
              type="button"
              onClick={handleDownloadCurrentPersonaJson}
              className="inline-flex flex-1 items-center justify-center gap-2 rounded-lg bg-white/20 px-3 py-2.5 text-sm text-white transition-colors hover:bg-white/30 sm:flex-initial sm:px-4"
            >
              <FileJson className="h-4 w-4 flex-shrink-0" />
              <span className="leading-snug">This persona (JSON)</span>
            </button>
            <button
              type="button"
              onClick={handleDownloadFullSetJson}
              className="inline-flex flex-1 basis-full items-center justify-center gap-2 rounded-lg bg-white/20 px-3 py-2.5 text-sm text-white transition-colors hover:bg-white/30 sm:basis-auto sm:flex-initial sm:px-4"
            >
              <Download className="h-4 w-4 flex-shrink-0" />
              <span className="leading-snug">Full set (JSON)</span>
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
                {(persona.image_url || persona.id) && !imageErrors.has(persona.id) ? (
                  <img
                    src={getPersonaImageUrl(persona.image_url, persona.id) || ''}
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
      <div
        ref={profileCardRef}
        data-persona-profile-card="true"
        className="glass-card rounded-2xl p-6 border border-white/20 pastel-blue max-w-7xl mx-auto"
      >
        {/* Header with Image, Demographics, Quote and Overview */}
        <div className="mb-4 flex flex-col gap-6 border-b border-white/20 pb-4 xl:flex-row xl:items-start">
          {/* Left: Image and Demographics */}
          <div className="flex flex-col gap-4 sm:flex-row sm:items-start">
            {/* Persona Image */}
            <div className="flex-shrink-0">
              {(currentPersona.image_url || currentPersona.id) && !imageErrors.has(currentPersona.id) ? (
                <img
                  src={getPersonaImageUrl(currentPersona.image_url, currentPersona.id) || ''}
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
                      type="button"
                      onClick={() => handleGenerateImage(currentPersona.id)}
                      className="persona-export-hide absolute inset-0 flex items-center justify-center rounded-xl bg-black/50 opacity-0 transition-opacity hover:opacity-100"
                    >
                      <span className="text-xs text-white">Generate</span>
                    </button>
                  )}
                </div>
              )}
            </div>
            
            {/* Demographics - Four Rows */}
            <div className="flex min-w-0 max-w-full flex-col justify-center space-y-2 sm:min-w-[200px]">
              <h4 className="mb-2 break-words text-2xl font-bold text-white">
                {personaData.name || currentPersona.name}
              </h4>
              {(getField('age')) && (
                <div className="flex items-center space-x-2 text-sm text-white/90">
                  <User className="h-4 w-4 text-white/70" />
                  <span><strong>Age:</strong> {String(getField('age') || '')}</span>
                </div>
              )}
              {(getField('location') || getField('nationality')) && (
                <div className="flex items-center space-x-2 text-sm text-white/90">
                  <MapPin className="h-4 w-4 text-white/70" />
                  <span className="persona-export-text break-words">
                    <strong>Location:</strong>{' '}
                    {
                      (() => {
                        const location = getField('location');
                        const nationality = getField('nationality');
                        if (typeof location === 'string') {
                          return location;
                        } else if (location && typeof location === 'object' && 'city' in location && 'country' in location) {
                          return `${location.city}, ${location.country}`;
                        } else if (nationality) {
                          return nationality;
                        }
                        return location ? JSON.stringify(location) : '';
                      })()
                    }
                  </span>
                </div>
              )}
              {(getField('occupation')) && (
                <div className="flex items-center space-x-2 text-sm text-white/90">
                  <Briefcase className="h-4 w-4 text-white/70" />
                  <span className="persona-export-text break-words">
                    <strong>Occupation:</strong> {String(getField('occupation') || '')}
                  </span>
                </div>
              )}
              {(getField('gender')) && (
                <div className="flex items-center space-x-2 text-sm text-white/90">
                  <User className="h-4 w-4 text-white/70" />
                  <span><strong>Gender:</strong> {String(getField('gender') || '')}</span>
                </div>
              )}
              {(getField('nationality') && !getField('location')) && (
                <div className="flex items-center space-x-2 text-sm text-white/90">
                  <MapPin className="h-4 w-4 text-white/70" />
                  <span><strong>Nationality:</strong> {String(getField('nationality') || '')}</span>
                </div>
              )}
              {(getField('education_level')) && (
                <div className="flex items-center space-x-2 text-sm text-white/90">
                  <User className="h-4 w-4 text-white/70" />
                  <span><strong>Education:</strong> {String(getField('education_level') || '')}</span>
                </div>
              )}
              {(getField('income_bracket')) && (
                <div className="flex items-center space-x-2 text-sm text-white/90">
                  <User className="h-4 w-4 text-white/70" />
                  <span><strong>Income:</strong> {String(getField('income_bracket') || '')}</span>
                </div>
              )}
            </div>
          </div>

          {/* Right: Quote and Overview */}
          <div className="min-w-0 flex-1 space-y-3">
            {(personaData.quote || personaData.quotes) && (
              <div className="p-3 bg-white/10 rounded-lg border-l-4 border-purple-400">
                <div className="flex items-start space-x-2">
                  <Quote className="h-4 w-4 text-purple-300 flex-shrink-0 mt-0.5" />
                  <div className="text-sm italic leading-relaxed text-white/90 break-words">
                    {Array.isArray(personaData.quotes) ? (
                      <ul className="list-disc list-inside space-y-1">
                        {personaData.quotes.map((q: any, idx: number) => (
                          <li key={idx}>"{typeof q === 'string' ? q : JSON.stringify(q)}"</li>
                        ))}
                      </ul>
                    ) : (
                      <p>"{typeof personaData.quote === 'string' ? personaData.quote : (typeof personaData.quote === 'object' ? JSON.stringify(personaData.quote) : String(personaData.quote || ''))}"</p>
                    )}
                  </div>
                </div>
              </div>
            )}
            {(personaData.basic_description || personaData.tagline || personaData.role) && (
              <div>
                <h5 className="text-xs font-semibold text-white uppercase tracking-wide mb-2">Overview</h5>
                <p className="text-sm leading-relaxed text-white/90 break-words">
                  {(() => {
                    const getStringValue = (value: any): string | null => {
                      if (!value) return null;
                      if (typeof value === 'string') return value;
                      if (typeof value === 'object') {
                        if (Array.isArray(value)) return value.map(String).join(', ');
                        if ('text' in value || 'description' in value || 'content' in value) {
                          return String(value.text || value.description || value.content);
                        }
                        return JSON.stringify(value);
                      }
                      return String(value);
                    };
                    return getStringValue(personaData.basic_description) || 
                           getStringValue(personaData.tagline) || 
                           getStringValue(personaData.role) || '';
                  })()}
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Details Section - 2x2 Grid */}
        {/* NOTE: No internal scrolling here; keep full profile visible + exportable */}
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {/* Top Left: Background */}
          <div>
            {renderSection(
              'Background',
              <User className="h-3 w-3 text-white/70" />,
              (() => {
                const bg = personaData.background || personaData.other_information;
                // If it's an object, renderSection will handle it, but ensure it's not null
                return bg;
              })()
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
                        {personaData.technology_profile.primary_devices.map((device: any, idx: number) => (
                          <span key={idx} className="px-1.5 py-0.5 bg-white/20 rounded text-xs text-white/90">
                            {typeof device === 'string' ? device : (typeof device === 'object' ? JSON.stringify(device) : String(device))}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  {personaData.technology_profile.comfort_level && (
                    <div className="text-xs">
                      <span className="text-white/70 font-medium">Level:</span>
                      <span className="ml-1 text-white/90">
                        {typeof personaData.technology_profile.comfort_level === 'string' 
                          ? personaData.technology_profile.comfort_level 
                          : (typeof personaData.technology_profile.comfort_level === 'object' 
                            ? JSON.stringify(personaData.technology_profile.comfort_level) 
                            : String(personaData.technology_profile.comfort_level))}
                      </span>
                    </div>
                  )}
                  {personaData.technology_profile.software_used && (
                    <div>
                      <span className="text-xs text-white/70 font-medium">Software:</span>
                      <div className="flex flex-wrap gap-1 mt-0.5">
                        {personaData.technology_profile.software_used.map((software: any, idx: number) => (
                          <span key={idx} className="px-1.5 py-0.5 bg-white/20 rounded text-xs text-white/90">
                            {typeof software === 'string' ? software : (typeof software === 'object' ? JSON.stringify(software) : String(software))}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  {personaData.technology_profile.interaction_preferences && (
                    <div>
                      <span className="text-xs text-white/70 font-medium">Preferences:</span>
                      <ul className="list-disc list-inside space-y-0.5 mt-0.5 text-xs text-white/90">
                        {personaData.technology_profile.interaction_preferences.map((pref: any, idx: number) => (
                          <li key={idx} className="leading-tight">
                            {typeof pref === 'string' ? pref : (typeof pref === 'object' ? JSON.stringify(pref) : String(pref))}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {personaData.technology_profile.accessibility_needs && personaData.technology_profile.accessibility_needs.length > 0 && (
                    <div>
                      <span className="text-xs text-white/70 font-medium">Accessibility:</span>
                      <ul className="list-disc list-inside space-y-0.5 mt-0.5 text-xs text-white/90">
                        {personaData.technology_profile.accessibility_needs.map((need: any, idx: number) => (
                          <li key={idx} className="leading-tight">
                            {typeof need === 'string' ? need : (typeof need === 'object' ? JSON.stringify(need) : String(need))}
                          </li>
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
              // All personas now use arrays for goals
              Array.isArray(personaData.goals) ? personaData.goals : null,
              true
            )}
          </div>

          {/* Bottom Right: Frustrations / Motivations */}
          <div>
            {renderSection(
              personaData.frustrations && personaData.frustrations.length > 0 ? 'Frustrations' : 'Motivations',
              <AlertCircle className="h-3 w-3 text-white/70" />,
              // All personas now use arrays
              Array.isArray(personaData.frustrations) && personaData.frustrations.length > 0
                ? personaData.frustrations
                : Array.isArray(personaData.motivations) && personaData.motivations.length > 0
                  ? personaData.motivations
                  : null,
              true
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

