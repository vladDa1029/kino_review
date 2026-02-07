// src/services/authService.js

import apiClient from './api';

export const login = async (email, password) => {
  const formData = new FormData();
  formData.append('username', email);
  formData.append('password', password);
  
  return apiClient('/auth/login', {
    method: 'POST',
    body: formData,
  });
};

export const register = async (email, password) => {
  return apiClient('/auth/register', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
};

export const refreshToken = async () => {
  // Refresh токен передается через куки, поэтому нам не нужно явно передавать его
  return apiClient('/auth/refresh', {
    method: 'POST',
  });
};

export const logout = async () => {
  return apiClient('/auth/logout', {
    method: 'GET',
  });
};

// Добавляем функцию для получения всех пользователей (для администратора)
export const getUsers = async (page = 1, pageSize = 5) => {
  const params = new URLSearchParams({ page, page_size: pageSize });
  return apiClient(`/auth/users?${params.toString()}`, {
    method: 'GET',
  });
};
