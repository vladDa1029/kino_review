const rawApiBaseUrl = import.meta.env.VITE_API_BASE_URL || '/api';

export const API_BASE_URL = rawApiBaseUrl.replace(/\/+$/, '');
export const ADMIN_AUTH_BYPASS = import.meta.env.VITE_BYPASS_ADMIN_AUTH === 'true';
