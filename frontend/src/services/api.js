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
