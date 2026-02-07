import { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import PasswordStrength from './PasswordStrength';
import { checkPasswordStrength } from '../utils/passwordValidator';

const AuthModal = ({ showAuth, setShowAuth }) => {
  const { isLogin, setIsLogin, handleLogin, handleRegister } = useAuth();
  const [formData, setFormData] = useState({
    email: '',
    password: '',
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

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!isLogin) {
      if (passwordStrength < 3) {
        return;
      }
    }

    try {
      if (isLogin) {
        await handleLogin(formData.email, formData.password);
      } else {
        await handleRegister(formData.email, formData.password);
        setIsLogin(true); // Переключаемся на форму входа после регистрации
      }
      setFormData({ email: '', password: '' });
    } catch (error) {
      // Обработка ошибок уже осуществляется в соответствующих функциях
    }
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
                    {showPassword ? '🙈' : '👁️'}
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

              <button
                type="submit"
                className="auth-submit-btn"
                disabled={!isLogin && passwordStrength < 3}
              >
                {isLogin ? 'Sign In' : 'Sign Up'}
              </button>

              <p className="auth-switch">
                {isLogin ? "Don't have an account? " : "Already have an account? "}
                <span
                  onClick={() => setIsLogin(!isLogin)}
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
