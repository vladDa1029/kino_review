import { getPasswordStrengthColor, getPasswordHint } from '../utils/passwordValidator';

const PasswordStrength = ({ password, requirements, strength }) => {
  const color = getPasswordStrengthColor(strength);

  return (
    <div className="password-feedback">
      <div className="password-strength">
        <span>Надежность: </span>
        <div className="strength-meter">
          {[1, 2, 3, 4].map((level) => (
            <div
              key={level}
              className="strength-segment"
              style={{ backgroundColor: strength >= level ? color : '#e0e0e0' }}
            />
          ))}
        </div>
        <span className="strength-label" style={{ color }}>
          {['Очень слабый', 'Слабый', 'Средний', 'Хороший', 'Сильный'][strength] || 'Очень слабый'}
        </span>
      </div>
      <div className="password-hints">
        <p className="hint-text">{getPasswordHint(password, requirements)}</p>
        <div className="requirement-list">
          <span className={requirements.length ? 'met' : ''}>✓ Минимум 8 символов</span>
          <span className={requirements.uppercase ? 'met' : ''}>✓ Заглавная буква</span>
          <span className={requirements.number ? 'met' : ''}>✓ Цифра</span>
          <span className={requirements.specialChar ? 'met' : ''}>✓ Спецсимвол</span>
        </div>
      </div>
    </div>
  );
};

export default PasswordStrength;
