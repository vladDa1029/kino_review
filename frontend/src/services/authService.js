import apiClient from './api';

export const login = async (email, password) => {
  const formData = new URLSearchParams({
    grant_type: 'password',
    username: email,
    password,
  });

  return apiClient('/login', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: formData,
  });
};

export const register = async (email, password) => {
  return apiClient('/user', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
};

export const fetchUserData = async (token) => {
  return apiClient('/user', {
    method: 'GET',
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
};