import apiClient from './httpClient';

export const register = async (email, password) =>
  apiClient('/auth/register', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });

export const login = async (username, password) => {
  const formData = new URLSearchParams();
  formData.append('username', username);
  formData.append('password', password);
  formData.append('grant_type', 'password');

  return apiClient('/auth/login', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: formData,
  });
};

export const refreshToken = async () =>
  apiClient('/auth/refresh', {
    method: 'POST',
    withCredentials: true,
    skipAuth: true,
    skipJsonContentType: true,
  });

export const logout = async () =>
  apiClient('/auth/logout', {
    method: 'GET',
    withCredentials: true,
  });

export const getUsers = async (page = 1, pageSize = 5) => {
  const params = new URLSearchParams({
    page: page.toString(),
    page_size: pageSize.toString(),
  });

  return apiClient(`/auth/users?${params.toString()}`, {
    method: 'GET',
  });
};

export const createUserDescription = async (payload) =>
  apiClient('/user/users/me/description', {
    method: 'POST',
    body: JSON.stringify(payload),
  });

export const getUserDescription = async () =>
  apiClient('/user/users/me/description', {
    method: 'GET',
  });

export const updateUserDescription = async (descriptionId, payload) =>
  apiClient(`/user/users/me/description/${descriptionId}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });

export const createMicrofon = async (payload) =>
  apiClient('/user/users/me/microfons', {
    method: 'POST',
    body: JSON.stringify(payload),
  });

export const listMicrofons = async ({
  page = 1,
  pageSize = 20,
  sortBy,
  sortDir = 'asc',
  type,
  search,
  createdFrom,
  createdTo,
} = {}) => {
  const params = new URLSearchParams({
    page: page.toString(),
    page_size: pageSize.toString(),
    sort_dir: sortDir,
  });

  if (sortBy) params.set('sort_by', sortBy);
  if (type) params.set('type', type);
  if (search) params.set('search', search);
  if (createdFrom) params.set('created_from', createdFrom);
  if (createdTo) params.set('created_to', createdTo);

  return apiClient(`/user/users/me/microfons?${params.toString()}`, {
    method: 'GET',
  });
};

export const updateMicrofon = async (microfonId, payload) =>
  apiClient(`/user/users/me/microfons/${microfonId}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });

export const deleteMicrofon = async (microfonId) =>
  apiClient(`/user/users/me/microfons/${microfonId}`, {
    method: 'DELETE',
  });
