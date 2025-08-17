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
  if (!pass) return 'Enter your password';
  const missing = [];
  if (!requirements.length) missing.push('at least 8 characters');
  if (!requirements.uppercase) missing.push('one uppercase letter');
  if (!requirements.number) missing.push('one number');
  if (!requirements.specialChar) missing.push('one special character');
  return missing.length > 0 ? `Missing: ${missing.join(', ')}` : 'Strong password!';
};