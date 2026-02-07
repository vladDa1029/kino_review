// src/hooks/useAuth.js

import { useState, useEffect, useCallback } from 'react';
import { login, register, refreshToken, logout as apiLogout } from '../services/authService';
import { toast } from 'react-toastify';
import { decodeToken, shouldRefreshToken } from '../utils/tokenUtils';

export const useAuth = () => {
  const [token, setToken] = useState(localStorage.getItem('access_token') || null);
  const [userData, setUserData] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleLogin = useCallback(async (email, password) => {
    setLoading(true);
    try {
      const data = await login(email, password);
      const accessToken = data.access_token;

      setToken(accessToken);
      localStorage.setItem('access_token', accessToken);

      const decoded = decodeToken(accessToken);
      setUserData(decoded || { email });

      toast.success('Successfully logged in!');
    } catch (error) {
      toast.error(error.message || 'Login failed');
    } finally {
      setLoading(false);
    }
  }, []);

  const handleRegister = useCallback(async (email, password) => {
    setLoading(true);
    try {
      await register(email, password);
      toast.success('Registration successful! Please log in.');
    } catch (error) {
      toast.error(error.message || 'Registration failed');
    } finally {
      setLoading(false);
    }
  }, []);

  const handleLogout = useCallback(async () => {
    try {
      await apiLogout();
    } catch (error) {
      console.warn('Logout API failed, proceeding with local logout');
    }
    setToken(null);
    setUserData(null);
    localStorage.removeItem('access_token');
    toast.info('Logged out successfully');
  }, []);

  const handleRefreshToken = useCallback(async () => {
    try {
      const data = await refreshToken();
      const newAccessToken = data.access_token;
      setToken(newAccessToken);
      localStorage.setItem('access_token', newAccessToken);
      return newAccessToken;
    } catch (error) {
      console.error('Token refresh failed:', error);
      handleLogout();
      return null;
    }
  }, [handleLogout]);

  // Автоматически обновляем токен за 1 минуту до истечения
  useEffect(() => {
    if (!token) return;

    if (shouldRefreshToken(token, 60)) { // Обновляем за 1 минуту до истечения
      handleRefreshToken();
    }
  }, [token, handleRefreshToken]);

  // Загружаем данные пользователя при изменении токена
  useEffect(() => {
    if (token) {
      if (shouldRefreshToken(token)) {
        handleRefreshToken();
      } else {
        const decoded = decodeToken(token);
        setUserData(decoded || { email: 'user@example.com' });
      }
    }
  }, [token, handleRefreshToken]);

  return {
    token,
    userData,
    loading,
    handleLogin,
    handleRegister,
    handleLogout,
    refreshToken: handleRefreshToken,
  };
};
