let accessToken = null;
let tokenType = 'Bearer';

const listeners = new Set();

const notifyListeners = () => {
  const snapshot = {
    accessToken,
    tokenType,
  };

  listeners.forEach((listener) => {
    listener(snapshot);
  });
};

export const getAccessToken = () => accessToken;

export const getTokenType = () => tokenType;

export const setAuthSession = (token, nextTokenType = 'Bearer') => {
  accessToken = token || null;
  tokenType = token ? nextTokenType || 'Bearer' : 'Bearer';
  notifyListeners();
};

export const setAccessToken = (token) => {
  accessToken = token || null;
  notifyListeners();
};

export const setTokenType = (nextTokenType) => {
  tokenType = nextTokenType || 'Bearer';
  notifyListeners();
};

export const clearAccessToken = () => {
  accessToken = null;
  tokenType = 'Bearer';
  notifyListeners();
};

export const subscribeToTokenChanges = (listener) => {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
};
