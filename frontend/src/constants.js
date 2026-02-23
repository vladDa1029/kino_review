const rawApiBaseUrl = import.meta.env.VITE_API_BASE_URL;

if (!rawApiBaseUrl) {
  throw new Error('VITE_API_BASE_URL is not set. Add it to your .env file.');
}

export const API_BASE_URL = rawApiBaseUrl.replace(/\/+$/, '');
