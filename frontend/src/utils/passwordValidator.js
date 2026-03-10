export const checkPasswordStrength = (pass) => {
  const requirements = {
    length: pass.length >= 8,
    uppercase: /[A-Z]/.test(pass),
    number: /[0-9]/.test(pass),
    specialChar: /[^A-Za-z0-9]/.test(pass),
  };
  const strength = Object.values(requirements).filter(Boolean).length;
  return { requirements, strength };
};

export const getPasswordStrengthColor = (strength) => {
  const colors = ['#ff4757', '#ff6b81', '#feca57', '#2ecc71', '#1dd1a1'];
  return colors[strength] || colors[0];
};

export const getPasswordHint = (pass, requirements) => {
  if (!pass) return 'Введите пароль';
  const missing = [];
  if (!requirements.length) missing.push('не менее 8 символов');
  if (!requirements.uppercase) missing.push('одну заглавную букву');
  if (!requirements.number) missing.push('одну цифру');
  if (!requirements.specialChar) missing.push('один спецсимвол');
  return missing.length > 0 ? `Нужно добавить: ${missing.join(', ')}` : 'Пароль достаточно надежный';
};
