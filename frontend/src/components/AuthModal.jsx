import { useState } from 'react';
import PasswordStrength from './PasswordStrength';
import { checkPasswordStrength } from '../utils/passwordValidator';

const AuthModal = ({
  isLogin,
  setIsLogin,
  showAuth,
  setShowAuth,
  onLogin,
  onRegister,
}) => {
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    confirmPassword: '',
  });
  const [showPassword, setShowPassword] = useState(false);
  const [passwordRequirements, setPasswordRequirements] = useState({
    length: false,
    uppercase: false,
    number: false,
    specialChar: false,
  });
  const [passwordStrength, setPasswordStrength] = useState(0);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));

    if (name === 'password' && !isLogin) {
      const { requirements, strength } = checkPasswordStrength(value);
      setPasswordRequirements(requirements);
      setPasswordStrength(strength);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!isLogin) {
      if (passwordStrength < 3) {
        alert('Password is too weak');
        return;
      }
      if (formData.password !== formData.confirmPassword) {
        alert('Passwords do not match');
        return;
      }
    }

    if (isLogin) {
      onLogin(formData.email, formData.password);
    } else {
      onRegister(formData.email, formData.password);
    }

    setFormData({ email: '', password: '', confirmPassword: '' });
  };

  return (
    showAuth && (
      <div className="auth-modal open">
        <div className="auth-container">
          <div className="auth-content">
            <button
              className="close-btn"
              onClick={() => setShowAuth(false)}
            >
              &times;
            </button>
            <h2>{isLogin ? 'Welcome Back' : 'Create Account'}</h2>
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <input
                  type="email"
                  name="email"
                  placeholder="Email Address"
                  className="form-input"
                  value={formData.email}
                  onChange={handleInputChange}
                  required
                />
              </div>

              <div className="form-group password-input-container">
                <div className="password-input-wrapper">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    name="password"
                    placeholder="Password"
                    className="form-input"
                    value={formData.password}
                    onChange={handleInputChange}
                    required
                  />
                  <button
                    type="button"
                    className="password-toggle"
                    onClick={() => setShowPassword(!showPassword)}
                  >
                    {showPassword ? (
                      <svg>...</svg>
                    ) : (
                      <svg>...</svg>
                    )}
                  </button>
                </div>
                {!isLogin && (
                  <PasswordStrength
                    password={formData.password}
                    requirements={passwordRequirements}
                    strength={passwordStrength}
                  />
                )}
              </div>

              {!isLogin && (
                <div className="form-group password-input-container">
                  <div className="password-input-wrapper">
                    <input
                      type={showPassword ? 'text' : 'password'}
                      name="confirmPassword"
                      placeholder="Confirm Password"
                      className="form-input"
                      value={formData.confirmPassword}
                      onChange={handleInputChange}
                      required
                    />
                    <button
                      type="button"
                      className="password-toggle"
                      onClick={() => setShowPassword(!showPassword)}
                    >
                      {showPassword ? <svg>...</svg> : <svg>...</svg>}
                    </button>
                  </div>
                  {formData.confirmPassword && formData.password !== formData.confirmPassword && (
                    <p className="password-error">Passwords don't match</p>
                  )}
                </div>
              )}

              <button
                type="submit"
                className="auth-submit-btn"
                disabled={!isLogin && (passwordStrength < 3 || formData.password !== formData.confirmPassword)}
              >
                {isLogin ? 'Sign In' : 'Sign Up'}
              </button>

              <div className="auth-divider"><span>or</span></div>

              <button className="social-auth-btn google-btn">Continue with Google</button>
              <button className="social-auth-btn github-btn">Continue with GitHub</button>

              <p className="auth-switch">
                {isLogin ? "Don't have an account? " : "Already have an account? "}
                <span
                  onClick={() => {
                    setIsLogin(!isLogin);
                    setFormData({ ...formData, password: '', confirmPassword: '' });
                  }}
                  className="switch-link"
                >
                  {isLogin ? 'Sign up' : 'Sign in'}
                </span>
              </p>
            </form>
          </div>
        </div>
      </div>
    )
  );
};

export default AuthModal;