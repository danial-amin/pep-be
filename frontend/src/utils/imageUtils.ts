/**
 * Utility functions for handling persona images.
 */

const API_BASE_URL = import.meta.env.VITE_API_URL?.replace('/api/v1', '') || 'http://localhost:8080';

/**
 * Get the full URL for a persona image.
 * If the image_url is already a full URL (http/https), return it as-is.
 * If it's a relative path (starts with /static), prepend the API base URL.
 */
export function getPersonaImageUrl(imageUrl: string | undefined | null): string | null {
  if (!imageUrl) {
    return null;
  }

  // If it's already a full URL, return as-is
  if (imageUrl.startsWith('http://') || imageUrl.startsWith('https://')) {
    return imageUrl;
  }

  // If it's a relative path, prepend the API base URL
  if (imageUrl.startsWith('/static')) {
    return `${API_BASE_URL}${imageUrl}`;
  }

  // If it's just a filename or path, assume it's in static/images/personas
  if (imageUrl.startsWith('persona_')) {
    return `${API_BASE_URL}/static/images/personas/${imageUrl}`;
  }

  // Default: treat as relative path
  return `${API_BASE_URL}${imageUrl.startsWith('/') ? imageUrl : '/' + imageUrl}`;
}

