let accessToken = null;
let tokenType = 'Bearer';

export const getAccessToken = () => accessToken;

export const setAccessToken = (token) => {
  accessToken = token || null;
};

export const getTokenType = () => tokenType;

export const setTokenType = (nextTokenType) => {
  tokenType = nextTokenType || 'Bearer';
};

export const clearAccessToken = () => {
  accessToken = null;
  tokenType = 'Bearer';
};
