import { useCallback, useEffect, useMemo, useState } from 'react';
import { toast } from 'react-toastify';
import * as authApi from '../services/api';
import { refreshAccessToken } from '../services/authSession';
import {
  clearAccessToken,
  getAccessToken,
  setAuthSession,
  subscribeToTokenChanges,
} from '../services/tokenStorage';
import { decodeToken, shouldRefreshToken } from '../utils/tokenUtils';
import { AuthContext } from './authContextInstance';

const AUTH_EMAIL_KEY = 'kinoflow.authEmail';

const readStoredAuthEmail = () => {
  try {
    return localStorage.getItem(AUTH_EMAIL_KEY) || '';
  } catch {
    return '';
  }
};

const writeStoredAuthEmail = (email) => {
  try {
    if (email) {
      localStorage.setItem(AUTH_EMAIL_KEY, email);
    } else {
      localStorage.removeItem(AUTH_EMAIL_KEY);
    }
  } catch {
    // localStorage can be unavailable in restricted browser modes.
  }
};

export const AuthProvider = ({ children }) => {
  const [token, setTokenState] = useState(() => getAccessToken());
  const [userData, setUserData] = useState(() => {
    const currentToken = getAccessToken();
    return currentToken ? decodeToken(currentToken) : null;
  });
  const [authEmail, setAuthEmail] = useState(readStoredAuthEmail);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [isLogin, setIsLogin] = useState(true);
  const [isAuthReady, setIsAuthReady] = useState(false);

  const applyToken = useCallback((nextToken, nextTokenType = 'Bearer') => {
    setAuthSession(nextToken, nextTokenType);
  }, []);

  const rememberAuthEmail = useCallback((email) => {
    const normalizedEmail = String(email || '').trim().toLowerCase();
    setAuthEmail(normalizedEmail);
    writeStoredAuthEmail(normalizedEmail);
  }, []);

  const handleRefreshToken = useCallback(async () => {
    try {
      return await refreshAccessToken({ preserveSessionOnNetworkError: true });
    } catch {
      return getAccessToken();
    }
  }, []);

  useEffect(() => {
    const unsubscribe = subscribeToTokenChanges(({ accessToken }) => {
      setTokenState(accessToken);
      setUserData(accessToken ? decodeToken(accessToken) : null);
    });

    setIsAuthReady(true);
    return unsubscribe;
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
          rememberAuthEmail(response.email || email);
          toast.success('Вы успешно вошли в систему');
          return response;
        }
        throw new Error('Сервер не вернул токен доступа');
      } catch (error) {
        toast.error(error.message || 'Ошибка входа');
        throw error;
      }
    },
    [applyToken, rememberAuthEmail],
  );

  const handleRegister = useCallback(
    async (email, password) => {
      try {
        const response = await authApi.register(email, password);
        if (response?.access_token) {
          applyToken(response.access_token, response.token_type);
          rememberAuthEmail(response.email || email);
          toast.success('Регистрация и вход выполнены успешно');
          return response;
        }

        const loginResponse = await authApi.login(email, password);
        if (loginResponse?.access_token) {
          applyToken(loginResponse.access_token, loginResponse.token_type);
          rememberAuthEmail(loginResponse.email || email);
          toast.success('Регистрация и вход выполнены успешно');
          return loginResponse;
        }

        throw new Error('Аккаунт создан, но сервер не вернул токен входа');
      } catch (error) {
        toast.error(error.message || 'Ошибка регистрации');
        throw error;
      }
    },
    [applyToken, rememberAuthEmail],
  );

  const handleLogout = useCallback(async () => {
    try {
      await authApi.logout();
    } catch {
      // Ошибки выхода на бэкенде игнорируем и очищаем локальное состояние.
    } finally {
      clearAccessToken();
      rememberAuthEmail('');
      toast.info('Вы вышли из системы');
    }
  }, [rememberAuthEmail]);

  const contextValue = useMemo(
    () => ({
      token,
      userData,
      authEmail,
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
      authEmail,
    ],
  );

  return <AuthContext.Provider value={contextValue}>{children}</AuthContext.Provider>;
};
