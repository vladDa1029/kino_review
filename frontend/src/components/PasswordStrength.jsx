import { getPasswordStrengthColor, getPasswordHint } from '../utils/passwordValidator';

const PasswordStrength = ({ password, requirements, strength }) => {
  const color = getPasswordStrengthColor(strength);

  return (
    <div className="password-feedback">
      <div className="password-strength">
        <span>Проверка: </span>
        <div className="strength-meter">
          {[1, 2].map((level) => (
            <div
              key={level}
              className="strength-segment"
              style={{ backgroundColor: strength >= level ? color : '#e0e0e0' }}
            />
          ))}
        </div>
        <span className="strength-label" style={{ color }}>
          {['Невалидный', 'Почти готово', 'Подходит'][strength] || 'Невалидный'}
        </span>
      </div>
      <div className="password-hints">
        <p className="hint-text">{getPasswordHint(password, requirements)}</p>
        <div className="requirement-list">
          <span className={requirements.minLength ? 'met' : ''}>✓ Минимум 4 символа</span>
          <span className={requirements.maxLength ? 'met' : ''}>✓ Максимум 24 символа</span>
        </div>
      </div>
    </div>
  );
};

export default PasswordStrength;
