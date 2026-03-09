import { useCallback, useEffect, useMemo, useState } from 'react';
import { toast } from 'react-toastify';
import * as authApi from '../services/api';
import { decodeToken, shouldRefreshToken } from '../utils/tokenUtils';
import { clearAccessToken, getAccessToken, setAccessToken, setTokenType } from '../services/tokenStorage';
import { AuthContext } from './authContextInstance';

export const AuthProvider = ({ children }) => {
  const [token, setTokenState] = useState(() => getAccessToken());
  const [userData, setUserData] = useState(null);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [isLogin, setIsLogin] = useState(true);
  const [isAuthReady, setIsAuthReady] = useState(false);

  const applyToken = useCallback((nextToken, nextTokenType = 'Bearer') => {
    setTokenType(nextToken ? nextTokenType : 'Bearer');
    setAccessToken(nextToken);
    setTokenState(nextToken || null);
    setUserData(nextToken ? decodeToken(nextToken) : null);
  }, []);

  const handleRefreshToken = useCallback(async () => {
    try {
      const response = await authApi.refreshToken();
      if (response?.access_token) {
        applyToken(response.access_token, response.token_type);
        return response.access_token;
      }
      applyToken(null);
      return null;
    } catch {
      applyToken(null);
      return null;
    }
  }, [applyToken]);

  useEffect(() => {
    setIsAuthReady(true);
  }, []);

  useEffect(() => {
    if (!token) {
      return undefined;
    }

    const interval = setInterval(() => {
      if (shouldRefreshToken(token, 300)) {
        handleRefreshToken();
      }
    }, 30_000);

    return () => clearInterval(interval);
  }, [handleRefreshToken, token]);

  const handleLogin = useCallback(
    async (email, password) => {
      try {
        const response = await authApi.login(email, password);
        if (response?.access_token) {
          applyToken(response.access_token, response.token_type);
          toast.success('Вы успешно вошли в систему');
          setIsAuthModalOpen(false);
          return response;
        }
        throw new Error('Сервер не вернул токен доступа');
      } catch (error) {
        toast.error(error.message || 'Ошибка входа');
        throw error;
      }
    },
    [applyToken],
  );

  const handleRegister = useCallback(
    async (email, password) => {
      try {
        const response = await authApi.register(email, password);
        if (response?.access_token) {
          applyToken(response.access_token, response.token_type);
          toast.success('Регистрация и вход выполнены успешно');
          setIsAuthModalOpen(false);
          return response;
        }
        toast.success('Регистрация завершена. Выполните вход.');
        return response;
      } catch (error) {
        toast.error(error.message || 'Ошибка регистрации');
        throw error;
      }
    },
    [applyToken],
  );

  const handleLogout = useCallback(async () => {
    try {
      await authApi.logout();
    } catch {
      // Ошибки выхода на бэкенде игнорируем и очищаем локальное состояние.
    } finally {
      clearAccessToken();
      applyToken(null);
      toast.info('Вы вышли из системы');
      setIsAuthModalOpen(false);
    }
  }, [applyToken]);

  const contextValue = useMemo(
    () => ({
      token,
      userData,
      isAuthReady,
      isAuthModalOpen,
      setIsAuthModalOpen,
      isLogin,
      setIsLogin,
      setUserData,
      handleLogin,
      handleRegister,
      handleLogout,
      handleRefreshToken,
    }),
    [
      handleLogin,
      handleLogout,
      handleRefreshToken,
      handleRegister,
      isAuthModalOpen,
      isAuthReady,
      isLogin,
      token,
      userData,
    ],
  );

  return <AuthContext.Provider value={contextValue}>{children}</AuthContext.Provider>;
};
