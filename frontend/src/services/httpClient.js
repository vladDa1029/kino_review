import { API_BASE_URL } from '../constants';
import { getAccessToken, getTokenType } from './tokenStorage';

export class ApiError extends Error {
  constructor(message, status, data) {
    super(message);
    this.status = status;
    this.data = data;
    this.name = 'ApiError';
  }
}

const getValidationMessage = (detail) => {
  if (!Array.isArray(detail)) {
    return null;
  }

  const messages = detail
    .map((item) => item?.msg)
    .filter(Boolean);

  return messages.length > 0 ? messages.join('; ') : null;
};

const apiClient = async (endpoint, options = {}) => {
  const { withCredentials = false, ...fetchOptions } = options;
  const token = getAccessToken();
  const tokenType = getTokenType();
  const headers = {
    ...(token ? { Authorization: `${tokenType} ${token}` } : {}),
    ...fetchOptions.headers,
  };

  if (!(fetchOptions.body instanceof FormData) && !(fetchOptions.body instanceof URLSearchParams) && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json';
  }

  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...fetchOptions,
      credentials: withCredentials ? 'include' : 'omit',
      headers,
    });

    const contentType = response.headers.get('content-type') || '';
    const data = contentType.includes('application/json') ? await response.json() : await response.text();

    if (!response.ok) {
      const validationMessage = typeof data === 'object' && data !== null ? getValidationMessage(data.detail) : null;
      const errorMessage =
        typeof data === 'object' && data !== null
          ? validationMessage || data.detail || data.message || JSON.stringify(data)
          : data || 'Request failed';

      throw new ApiError(errorMessage, response.status, data);
    }

    return data;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    throw new ApiError(error.message || 'Network error', 0, null);
  }
};

export default apiClient;
