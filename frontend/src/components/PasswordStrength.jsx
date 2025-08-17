import { getPasswordStrengthColor, getPasswordHint } from '../utils/passwordValidator';

const PasswordStrength = ({ password, requirements, strength }) => {
  const color = getPasswordStrengthColor(strength);

  return (
    <div className="password-feedback">
      <div className="password-strength">
        <span>Strength: </span>
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
          {['Very Weak', 'Weak', 'Fair', 'Good', 'Strong'][strength] || 'Very Weak'}
        </span>
      </div>
      <div className="password-hints">
        <p className="hint-text">{getPasswordHint(password, requirements)}</p>
        <div className="requirement-list">
          <span className={requirements.length ? 'met' : ''}>✓ 8+ characters</span>
          <span className={requirements.uppercase ? 'met' : ''}>✓ Uppercase letter</span>
          <span className={requirements.number ? 'met' : ''}>✓ Number</span>
          <span className={requirements.specialChar ? 'met' : ''}>✓ Special char</span>
        </div>
      </div>
    </div>
  );
};

export default PasswordStrength;