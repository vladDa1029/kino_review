import { useState, useEffect, useCallback } from 'react';
import { login, register, fetchUserData } from '../services/authService';
import { toast } from 'react-toastify';

export const useAuth = () => {
  const [token, setToken] = useState(localStorage.getItem('token') || null);
  const [userData, setUserData] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleLogin = useCallback(async (email, password) => {
    setLoading(true);
    try {
      const data = await login(email, password);
      const accessToken = data.access_token;
      setToken(accessToken);
      localStorage.setItem('token', accessToken);
      toast.success('Successfully logged in!');
    } catch (error) {
      if (error.message.includes('Failed to fetch')) {
        toast.error('Network error: Could not connect to the server.');
      } else {
        toast.error(error.message || 'Login failed');
      }
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

  const handleLogout = useCallback(() => {
    setToken(null);
    setUserData(null);
    localStorage.removeItem('token');
    toast.info('Logged out successfully');
  }, []);

  const refreshUserData = useCallback(async () => {
    if (!token) return;
    try {
      const data = await fetchUserData(token);
      if (data.is_active === false) {
        toast.error('Your account has been deactivated.');
        handleLogout();
        return;
      }
      setUserData(data);
    } catch (error) {
      if (error.status === 401) {
        handleLogout();
        toast.error('Session expired. Please log in again.');
      } else {
        toast.error('Failed to load user data.');
        console.error('Fetch user data error:', error);
      }
    }
  }, [token, handleLogout]);

  useEffect(() => {
    if (token) {
      refreshUserData();
    }
  }, [token, refreshUserData]);

  return {
    token,
    userData,
    loading,
    handleLogin,
    handleRegister,
    handleLogout,
    refreshUserData,
  };
};