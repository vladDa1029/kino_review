import { API_BASE_URL } from '../constants';

const apiClient = async (endpoint, options = {}) => {
  // Получаем токен из localStorage
  const token = localStorage.getItem('access_token');

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    credentials: 'include', // Важно для передачи куки с refresh токеном
    headers: {
      'Content-Type': options.body instanceof FormData ? 'multipart/form-data' : 'application/json',
      ...(token && { 'Authorization': `Bearer ${token}` }),
      ...options.headers,
    },
  });

  let data;
  const contentType = response.headers.get('content-type');
  if (contentType && contentType.includes('application/json')) {
    data = await response.json();
  } else {
    data = await response.text();
  }

  if (!response.ok) {
    const error = new Error(data.detail || data || 'Request failed');
    error.status = response.status;
    throw error;
  }

  return data;
};

export default apiClient;
