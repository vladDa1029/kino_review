export const checkPasswordStrength = (pass) => {
  const requirements = {
    minLength: pass.length >= 4,
    maxLength: pass.length <= 24,
  };

  const strength = Object.values(requirements).filter(Boolean).length;
  return { requirements, strength };
};

export const getPasswordStrengthColor = (strength) => {
  const colors = ['#ff4757', '#feca57', '#2ecc71'];
  return colors[strength] || colors[0];
};

export const getPasswordHint = (pass, requirements) => {
  if (!pass) {
    return 'Введите пароль';
  }

  const missing = [];

  if (!requirements.minLength) {
    missing.push('минимум 4 символа');
  }

  if (!requirements.maxLength) {
    missing.push('максимум 24 символа');
  }

  return missing.length > 0 ? `Нужно добавить: ${missing.join(', ')}` : 'Пароль подходит';
};
