/**
 * Utility functions for handling persona images.
 * Use persona ID when available so the API can serve from file or base64 (retained in DB).
 */

// Full API base URL (with /api/v1) for persona image endpoint
const getFullApiUrl = (): string => {
  let apiUrl = 'http://localhost:8080/api/v1';
  if (typeof window !== 'undefined' && (window as any).APP_CONFIG?.VITE_API_URL) {
    apiUrl = (window as any).APP_CONFIG.VITE_API_URL;
  } else {
    apiUrl = import.meta.env.VITE_API_URL || apiUrl;
  }
  return apiUrl;
};

// Base URL without /api/v1 for static assets
const getApiBaseUrl = (): string => {
  return getFullApiUrl().replace(/\/api\/v1\/?$/, '') || getFullApiUrl();
};

/**
 * Get the image URL for a persona. Prefer the API endpoint when personaId is provided
 * so the backend can serve from file or base64 (images are retained in DB).
 */
export function getPersonaImageUrl(
  imageUrl: string | undefined | null,
  personaId?: number
): string | null {
  // When we have a persona ID, use the API image endpoint (serves file or base64 from DB)
  if (personaId != null) {
    return `${getFullApiUrl()}/personas/persona/${personaId}/image`;
  }

  if (!imageUrl) {
    return null;
  }

  const base = getApiBaseUrl();

  if (imageUrl.startsWith('http://') || imageUrl.startsWith('https://')) {
    return imageUrl;
  }
  if (imageUrl.startsWith('/static')) {
    return `${base}${imageUrl}`;
  }
  if (imageUrl.startsWith('persona_')) {
    return `${base}/static/images/personas/${imageUrl}`;
  }
  return `${base}${imageUrl.startsWith('/') ? imageUrl : '/' + imageUrl}`;
}

