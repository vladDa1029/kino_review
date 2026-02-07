// src/utils/tokenUtils.js

/**
 * Декодирует JWT токен для получения его содержимого
 * @param {string} token - JWT токен
 * @returns {Object|null} - Раскодированные данные токена или null в случае ошибки
 */
export const decodeToken = (token) => {
  try {
    const base64Url = token.split('.')[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(atob(base64).split('').map(function(c) {
      return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
    }).join(''));
    return JSON.parse(jsonPayload);
  } catch (e) {
    console.error('Error decoding token:', e);
    return null;
  }
};

/**
 * Проверяет, истек ли токен
 * @param {string} token - JWT токен
 * @returns {boolean} - true если токен истек, иначе false
 */
export const isTokenExpired = (token) => {
  const decoded = decodeToken(token);
  if (!decoded || !decoded.exp) {
    return true; // Если не можем декодировать или нет времени истечения, считаем просроченным
  }

  const currentTime = Math.floor(Date.now() / 1000);
  return decoded.exp < currentTime;
};

/**
 * Проверяет, нужно ли обновить токен (истекает в ближайшие n секунд)
 * @param {string} token - JWT токен
 * @param {number} bufferSeconds - количество секунд до истечения, когда нужно обновить (по умолчанию 300 = 5 минут)
 * @returns {boolean} - true если токен нужно обновить, иначе false
 */
export const shouldRefreshToken = (token, bufferSeconds = 300) => {
  const decoded = decodeToken(token);
  if (!decoded || !decoded.exp) {
    return true; // Если не можем декодировать или нет времени истечения, нужно обновить
  }

  const currentTime = Math.floor(Date.now() / 1000);
  return decoded.exp - currentTime < bufferSeconds;
};
