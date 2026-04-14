import { API_BASE_URL } from '../constants';
import { ensureFreshAccessToken, refreshAccessToken } from './authSession';
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

const createErrorMessage = (data) => {
  const validationMessage =
    typeof data === 'object' && data !== null ? getValidationMessage(data.detail) : null;

  return typeof data === 'object' && data !== null
    ? validationMessage || data.detail || data.message || JSON.stringify(data)
    : data || 'Ошибка запроса';
};

const parseResponseData = async (response) => {
  const contentType = response.headers.get('content-type') || '';
  return contentType.includes('application/json') ? response.json() : response.text();
};

const buildHeaders = ({
  skipAuth,
  skipJsonContentType,
  fetchOptions,
  tokenOverride,
}) => {
  const activeToken = tokenOverride ?? getAccessToken();
  const tokenType = getTokenType();
  const hasBody = fetchOptions.body !== undefined && fetchOptions.body !== null;

  const headers = {
    ...(!skipAuth && activeToken ? { Authorization: `${tokenType} ${activeToken}` } : {}),
    ...fetchOptions.headers,
  };

  if (
    hasBody &&
    !skipJsonContentType &&
    !(fetchOptions.body instanceof FormData) &&
    !(fetchOptions.body instanceof URLSearchParams) &&
    !headers['Content-Type']
  ) {
    headers['Content-Type'] = 'application/json';
  }

  return headers;
};

const executeRequest = async ({
  endpoint,
  withCredentials,
  skipAuth,
  skipJsonContentType,
  fetchOptions,
  tokenOverride,
}) =>
  fetch(`${API_BASE_URL}${endpoint}`, {
    ...fetchOptions,
    credentials: withCredentials ? 'include' : 'omit',
    headers: buildHeaders({
      skipAuth,
      skipJsonContentType,
      fetchOptions,
      tokenOverride,
    }),
  });

const apiClient = async (endpoint, options = {}) => {
  const {
    withCredentials = false,
    skipAuth = false,
    skipJsonContentType = false,
    ...fetchOptions
  } = options;

  try {
    let tokenForRequest = getAccessToken();

    if (!skipAuth && tokenForRequest) {
      tokenForRequest = await ensureFreshAccessToken(60);
    }

    let response = await executeRequest({
      endpoint,
      withCredentials,
      skipAuth,
      skipJsonContentType,
      fetchOptions,
      tokenOverride: tokenForRequest,
    });

    if (response.status === 401 && !skipAuth) {
      const refreshedToken = await refreshAccessToken();

      if (refreshedToken) {
        response = await executeRequest({
          endpoint,
          withCredentials,
          skipAuth,
          skipJsonContentType,
          fetchOptions,
          tokenOverride: refreshedToken,
        });
      }
    }

    const data = await parseResponseData(response);

    if (!response.ok) {
      throw new ApiError(createErrorMessage(data), response.status, data);
    }

    return data;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }

    if (error?.status) {
      throw new ApiError(error.message || 'Ошибка запроса', error.status, error.data ?? null);
    }

    throw new ApiError(error.message || 'Ошибка сети', 0, null);
  }
};

export default apiClient;
