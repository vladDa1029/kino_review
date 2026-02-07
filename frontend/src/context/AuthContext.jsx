import { createContext, useContext, useState, useEffect } from 'react';
import { toast } from 'react-toastify';
import * as authService from '../services/authService';
import { shouldRefreshToken } from '../utils/tokenUtils';

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [token, setToken] = useState(localStorage.getItem('access_token') || null);
  const [userData, setUserData] = useState(null);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [isLogin, setIsLogin] = useState(true);

  useEffect(() => {
    // Проверяем возможность обновления токена при загрузке приложения
    // Только если токен был сохранен ранее и возможно его обновление
    if (token && shouldRefreshToken(token, 300)) { // Обновляем, если токен истекает в течение 5 минут
      handleRefreshToken();
    }
  }, [token]);

  const handleRefreshToken = async () => {
    try {
      const response = await authService.refreshToken();
      if (response.access_token) {
        setToken(response.access_token);
        localStorage.setItem('access_token', response.access_token);
      }
    } catch (error) {
      console.log('Could not refresh token, user not logged in');
    }
  };

  const handleLogin = async (email, password) => {
    try {
      const response = await authService.login(email, password);
      if (response.access_token) {
        setToken(response.access_token);
        localStorage.setItem('access_token', response.access_token);
        toast.success('Successfully logged in!');
        setIsAuthModalOpen(false);
        return response;
      }
    } catch (error) {
      toast.error(error.message || 'Login failed');
      throw error;
    }
  };

  const handleRegister = async (email, password) => {
    try {
      const response = await authService.register(email, password);
      toast.success('Registration successful! Please login.');
      return response;
    } catch (error) {
      toast.error(error.message || 'Registration failed');
      throw error;
    }
  };

  const handleLogout = async () => {
    try {
      await authService.logout();
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      setToken(null);
      setUserData(null);
      localStorage.removeItem('access_token');
      toast.info('Logged out successfully');
      setIsAuthModalOpen(false);
    }
  };

  return (
    <AuthContext.Provider value={{
      token,
      userData,
      isAuthModalOpen,
      setIsAuthModalOpen,
      isLogin,
      setIsLogin,
      setUserData,
      handleLogin,
      handleRegister,
      handleLogout,
      handleRefreshToken
    }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
