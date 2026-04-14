import { API_BASE_URL } from '../constants';
import { shouldRefreshToken } from '../utils/tokenUtils';
import { clearAccessToken, getAccessToken, setAuthSession } from './tokenStorage';

const getValidationMessage = (detail) => {
  if (!Array.isArray(detail)) {
    return null;
  }

  const messages = detail
    .map((item) => item?.msg)
    .filter(Boolean);

  return messages.length > 0 ? messages.join('; ') : null;
};

const createSessionError = (message, status, data) => {
  const error = new Error(message);
  error.name = 'AuthSessionError';
  error.status = status;
  error.data = data;
  return error;
};

const parseResponsePayload = async (response) => {
  const contentType = response.headers.get('content-type') || '';
  return contentType.includes('application/json') ? response.json() : response.text();
};

let refreshPromise = null;

export const refreshAccessToken = async ({ preserveSessionOnNetworkError = false } = {}) => {
  if (refreshPromise) {
    return refreshPromise;
  }

  const currentToken = getAccessToken();

  refreshPromise = (async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
        method: 'POST',
        credentials: 'include',
      });

      const data = await parseResponsePayload(response);

      if (!response.ok) {
        const validationMessage =
          typeof data === 'object' && data !== null ? getValidationMessage(data.detail) : null;
        const errorMessage =
          typeof data === 'object' && data !== null
            ? validationMessage || data.detail || data.message || JSON.stringify(data)
            : data || 'Не удалось обновить токен';

        throw createSessionError(errorMessage, response.status, data);
      }

      if (data?.access_token) {
        setAuthSession(data.access_token, data.token_type);
        return data.access_token;
      }

      clearAccessToken();
      return null;
    } catch (error) {
      if (error?.status === 401 || error?.status === 403) {
        clearAccessToken();
        return null;
      }

      if (preserveSessionOnNetworkError) {
        return currentToken;
      }

      if (error?.status) {
        throw error;
      }

      throw createSessionError(error.message || 'Ошибка сети', 0, null);
    } finally {
      refreshPromise = null;
    }
  })();

  return refreshPromise;
};

export const ensureFreshAccessToken = async (bufferSeconds = 60) => {
  const currentToken = getAccessToken();

  if (!currentToken) {
    return null;
  }

  if (!shouldRefreshToken(currentToken, bufferSeconds)) {
    return currentToken;
  }

  return refreshAccessToken({ preserveSessionOnNetworkError: true });
};
