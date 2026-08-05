import { useState } from 'react';
import {
  User,
  MapPin,
  Briefcase,
  Target,
  AlertCircle,
  Smartphone,
  Quote,
} from 'lucide-react';
import { Persona } from '../types';
import { getPersonaImageUrl } from '../utils/imageUtils';

function getField(personaData: Record<string, any>, fieldName: string, fallback?: string) {
  if (
    fieldName === 'age' ||
    fieldName === 'gender' ||
    fieldName === 'occupation' ||
    fieldName === 'location' ||
    fieldName === 'education' ||
    fieldName === 'nationality' ||
    fieldName === 'income_bracket' ||
    fieldName === 'relationship_status' ||
    fieldName === 'education_level'
  ) {
    return personaData.demographics?.[fieldName] || personaData[fieldName] || fallback;
  }
  return personaData[fieldName] || fallback;
}

function formatLocation(location: any, nationality?: any): string {
  if (typeof location === 'string') return location;
  if (location && typeof location === 'object' && 'city' in location && 'country' in location) {
    return `${location.city}, ${location.country}`;
  }
  if (nationality) return String(nationality);
  if (location) {
    try {
      return JSON.stringify(location);
    } catch {
      return String(location);
    }
  }
  return '';
}

function renderValue(value: any): string {
  if (value === null || value === undefined) return '';
  if (typeof value === 'string') return value;
  if (typeof value === 'number' || typeof value === 'boolean') return String(value);
  if (Array.isArray(value)) return value.map(renderValue).filter(Boolean).join(', ');
  if (typeof value === 'object') {
    if ('text' in value || 'description' in value || 'content' in value) {
      return String(value.text || value.description || value.content || '');
    }
    try {
      return JSON.stringify(value);
    } catch {
      return String(value);
    }
  }
  return String(value);
}

function Section({
  title,
  icon,
  data,
  isArray = false,
}: {
  title: string;
  icon: React.ReactNode;
  data: any;
  isArray?: boolean;
}) {
  if (!data || (isArray && (!Array.isArray(data) || data.length === 0))) return null;

  return (
    <div className="mb-5">
      <div className="flex items-center space-x-2 mb-2">
        {icon}
        <h5 className="text-xs font-semibold text-stone-900 uppercase tracking-wide">{title}</h5>
      </div>
      <div className="ml-5 space-y-1.5">
        {isArray && Array.isArray(data) ? (
          <ul className="list-disc list-inside space-y-1 text-sm text-stone-700">
            {data.map((item: any, idx: number) => (
              <li key={idx}>{typeof item === 'string' ? item : renderValue(item)}</li>
            ))}
          </ul>
        ) : typeof data === 'object' && data !== null && !Array.isArray(data) ? (
          <div className="space-y-1.5">
            {Object.entries(data).map(([key, value]) => (
              <div key={key} className="text-sm">
                <span className="font-medium capitalize text-stone-500">
                  {key.replace(/_/g, ' ')}:{' '}
                </span>
                <span className="text-stone-700 break-words">{renderValue(value)}</span>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-stone-700 leading-relaxed whitespace-pre-wrap">
            {renderValue(data)}
          </p>
        )}
      </div>
    </div>
  );
}

/**
 * Full persona profile card — matches the downloadable card on the detail page.
 */
export default function PersonaProfileCard({
  persona,
  compact = false,
  className = '',
  onClick,
}: {
  persona: Persona;
  compact?: boolean;
  className?: string;
  onClick?: () => void;
}) {
  const [imageError, setImageError] = useState(false);
  const personaData = persona.persona_data || {};
  const name = personaData.name || persona.name;
  const imageSize = compact ? 'w-24 h-24' : 'w-32 h-32';
  const interactive = typeof onClick === 'function';

  return (
    <div
      data-persona-profile-card="true"
      role={interactive ? 'button' : undefined}
      tabIndex={interactive ? 0 : undefined}
      onClick={onClick}
      onKeyDown={
        interactive
          ? (e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                onClick?.();
              }
            }
          : undefined
      }
      className={`glass-card rounded-2xl border border-stone-200 ${compact ? 'p-4' : 'p-6'} ${
        interactive
          ? 'cursor-pointer transition-shadow hover:border-stone-400 hover:shadow-md focus:outline-none focus:ring-2 focus:ring-stone-400 focus:ring-offset-2'
          : ''
      } ${className}`}
    >
      {/* Header: image, demographics, quote */}
      <div className={`mb-4 flex flex-col gap-4 border-b border-stone-200 pb-4 ${compact ? '' : 'xl:flex-row xl:items-start'}`}>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start">
          <div className="flex-shrink-0">
            {(persona.image_url || persona.id) && !imageError ? (
              <img
                src={getPersonaImageUrl(persona.image_url, persona.id) || ''}
                alt={name}
                className={`${imageSize} object-cover rounded-xl border-4 border-stone-200 shadow-lg`}
                onError={() => setImageError(true)}
              />
            ) : (
              <div
                className={`${imageSize} rounded-xl border-4 border-stone-200 bg-stone-50 flex items-center justify-center`}
              >
                <span className="text-stone-300 text-3xl font-bold">
                  {String(name).charAt(0).toUpperCase()}
                </span>
              </div>
            )}
          </div>

          <div className="flex min-w-0 flex-col justify-center space-y-1.5">
            <h4 className={`mb-1 break-words font-bold text-stone-900 ${compact ? 'text-xl' : 'text-2xl'}`}>
              {name}
            </h4>
            {getField(personaData, 'age') && (
              <div className="flex items-center space-x-2 text-sm text-stone-700">
                <User className="h-4 w-4 text-stone-500 flex-shrink-0" />
                <span>
                  <strong>Age:</strong> {String(getField(personaData, 'age') || '')}
                </span>
              </div>
            )}
            {(getField(personaData, 'location') || getField(personaData, 'nationality')) && (
              <div className="flex items-center space-x-2 text-sm text-stone-700">
                <MapPin className="h-4 w-4 text-stone-500 flex-shrink-0" />
                <span className="break-words">
                  <strong>Location:</strong>{' '}
                  {formatLocation(getField(personaData, 'location'), getField(personaData, 'nationality'))}
                </span>
              </div>
            )}
            {getField(personaData, 'occupation') && (
              <div className="flex items-center space-x-2 text-sm text-stone-700">
                <Briefcase className="h-4 w-4 text-stone-500 flex-shrink-0" />
                <span className="break-words">
                  <strong>Occupation:</strong> {String(getField(personaData, 'occupation') || '')}
                </span>
              </div>
            )}
            {getField(personaData, 'gender') && (
              <div className="flex items-center space-x-2 text-sm text-stone-700">
                <User className="h-4 w-4 text-stone-500 flex-shrink-0" />
                <span>
                  <strong>Gender:</strong> {String(getField(personaData, 'gender') || '')}
                </span>
              </div>
            )}
            {(getField(personaData, 'education') || getField(personaData, 'education_level')) && (
              <div className="flex items-center space-x-2 text-sm text-stone-700">
                <User className="h-4 w-4 text-stone-500 flex-shrink-0" />
                <span className="break-words">
                  <strong>Education:</strong>{' '}
                  {String(
                    getField(personaData, 'education') || getField(personaData, 'education_level') || ''
                  )}
                </span>
              </div>
            )}
          </div>
        </div>

        <div className="min-w-0 flex-1 space-y-3">
          {(personaData.quote || personaData.quotes) && (
            <div className="p-3 bg-stone-50 rounded-lg border-l-4 border-violet-400">
              <div className="flex items-start space-x-2">
                <Quote className="h-4 w-4 text-violet-500 flex-shrink-0 mt-0.5" />
                <div className="text-sm italic leading-relaxed text-stone-700 break-words">
                  {Array.isArray(personaData.quotes) ? (
                    <ul className="list-disc list-inside space-y-1">
                      {personaData.quotes.map((q: any, idx: number) => (
                        <li key={idx}>"{renderValue(q)}"</li>
                      ))}
                    </ul>
                  ) : (
                    <p>"{renderValue(personaData.quote)}"</p>
                  )}
                </div>
              </div>
            </div>
          )}
          {(personaData.basic_description || personaData.tagline || personaData.role) && (
            <div>
              <h5 className="text-xs font-semibold text-stone-900 uppercase tracking-wide mb-1.5">
                Overview
              </h5>
              <p className="text-sm leading-relaxed text-stone-700 break-words">
                {renderValue(personaData.basic_description) ||
                  renderValue(personaData.tagline) ||
                  renderValue(personaData.role)}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Body sections */}
      <div className={compact ? 'space-y-1' : 'grid grid-cols-1 gap-2 lg:grid-cols-2'}>
        <Section
          title="Background"
          icon={<User className="h-3 w-3 text-stone-500" />}
          data={personaData.background || personaData.other_information}
        />

        {personaData.technology_profile && (
          <div className="mb-5">
            <div className="flex items-center space-x-2 mb-2">
              <Smartphone className="h-3 w-3 text-stone-500" />
              <h5 className="text-xs font-semibold text-stone-900 uppercase tracking-wide">
                Technology Profile
              </h5>
            </div>
            <div className="ml-5 space-y-1.5">
              {personaData.technology_profile.primary_devices && (
                <div>
                  <span className="text-xs text-stone-500 font-medium">Devices:</span>
                  <div className="flex flex-wrap gap-1 mt-0.5">
                    {personaData.technology_profile.primary_devices.map((device: any, idx: number) => (
                      <span key={idx} className="px-1.5 py-0.5 bg-stone-100 rounded text-xs text-stone-700">
                        {renderValue(device)}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              {personaData.technology_profile.comfort_level && (
                <div className="text-xs">
                  <span className="text-stone-500 font-medium">Level:</span>
                  <span className="ml-1 text-stone-700">
                    {renderValue(personaData.technology_profile.comfort_level)}
                  </span>
                </div>
              )}
              {personaData.technology_profile.software_used && (
                <div>
                  <span className="text-xs text-stone-500 font-medium">Software:</span>
                  <div className="flex flex-wrap gap-1 mt-0.5">
                    {personaData.technology_profile.software_used.map((software: any, idx: number) => (
                      <span key={idx} className="px-1.5 py-0.5 bg-stone-100 rounded text-xs text-stone-700">
                        {renderValue(software)}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              {personaData.technology_profile.interaction_preferences && (
                <div>
                  <span className="text-xs text-stone-500 font-medium">Preferences:</span>
                  <ul className="list-disc list-inside space-y-0.5 mt-0.5 text-xs text-stone-700">
                    {personaData.technology_profile.interaction_preferences.map(
                      (pref: any, idx: number) => (
                        <li key={idx} className="leading-tight">
                          {renderValue(pref)}
                        </li>
                      )
                    )}
                  </ul>
                </div>
              )}
            </div>
          </div>
        )}

        <Section
          title="Goals"
          icon={<Target className="h-3 w-3 text-stone-500" />}
          data={Array.isArray(personaData.goals) ? personaData.goals : null}
          isArray
        />

        <Section
          title={
            Array.isArray(personaData.frustrations) && personaData.frustrations.length > 0
              ? 'Frustrations'
              : 'Motivations'
          }
          icon={<AlertCircle className="h-3 w-3 text-stone-500" />}
          data={
            Array.isArray(personaData.frustrations) && personaData.frustrations.length > 0
              ? personaData.frustrations
              : Array.isArray(personaData.motivations) && personaData.motivations.length > 0
                ? personaData.motivations
                : null
          }
          isArray
        />

        {personaData.starting_position && (
          <Section
            title="Position"
            icon={<Target className="h-3 w-3 text-stone-500" />}
            data={personaData.starting_position}
          />
        )}
      </div>
    </div>
  );
}
