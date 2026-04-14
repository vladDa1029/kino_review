import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/useAuth';
import PasswordStrength from './PasswordStrength';
import { checkPasswordStrength } from '../utils/passwordValidator';

const EyeIcon = () => (
  <svg
    className="password-eye-icon"
    viewBox="0 0 24 24"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    aria-hidden="true"
  >
    <path
      d="M1 12C2.73 7.61 7 4.5 12 4.5C17 4.5 21.27 7.61 23 12C21.27 16.39 17 19.5 12 19.5C7 19.5 2.73 16.39 1 12Z"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
    <circle cx="12" cy="12" r="3" stroke="currentColor" strokeWidth="1.8" />
  </svg>
);

const EyeOffIcon = () => (
  <svg
    className="password-eye-icon"
    viewBox="0 0 24 24"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    aria-hidden="true"
  >
    <path
      d="M2 2L22 22"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
    <path
      d="M9.88 9.88C9.34 10.42 9 11.17 9 12C9 13.66 10.34 15 12 15C12.83 15 13.58 14.66 14.12 14.12"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
    <path
      d="M6.45 6.45C4.25 7.77 2.53 9.71 1.5 12C3.23 16.39 7.5 19.5 12.5 19.5C14.16 19.5 15.75 19.16 17.2 18.55"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
    <path
      d="M10.62 4.62C11.24 4.54 11.87 4.5 12.5 4.5C17.5 4.5 21.77 7.61 23.5 12C22.84 13.67 21.85 15.17 20.62 16.41"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);

const AuthModal = ({ showAuth, setShowAuth }) => {
  const { isLogin, setIsLogin, handleLogin, handleRegister } = useAuth();
  const navigate = useNavigate();
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
    if (!isLogin && passwordStrength < 3) {
      return;
    }

    try {
      let response;
      if (isLogin) {
        response = await handleLogin(formData.email, formData.password);
      } else {
        response = await handleRegister(formData.email, formData.password);
        if (!response?.access_token) {
          setIsLogin(true);
        }
      }

      if (response?.access_token) {
        navigate('/projects');
      }

      setFormData({ email: '', password: '' });
    } catch {
      // Обработка ошибок выполняется внутри auth-методов.
    }
  };

  return (
    showAuth && (
      <div className="auth-modal open">
        <div className="auth-container">
          <div className="auth-content">
            <button className="close-btn" onClick={() => setShowAuth(false)}>
              &times;
            </button>
            <h2>{isLogin ? 'С возвращением' : 'Создать аккаунт'}</h2>
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <input
                  type="email"
                  name="email"
                  placeholder="Электронная почта"
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
                    placeholder="Пароль"
                    className="form-input"
                    value={formData.password}
                    onChange={handleInputChange}
                    required
                  />
                  <button
                    type="button"
                    className="password-toggle"
                    aria-label={showPassword ? 'Скрыть пароль' : 'Показать пароль'}
                    onClick={() => setShowPassword(!showPassword)}
                  >
                    {showPassword ? <EyeOffIcon /> : <EyeIcon />}
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
                {isLogin ? 'Войти' : 'Зарегистрироваться'}
              </button>

              <p className="auth-switch">
                {isLogin
                  ? 'Нет аккаунта? '
                  : 'Уже есть аккаунт? '}
                <span onClick={() => setIsLogin(!isLogin)} className="switch-link">
                  {isLogin ? 'Регистрация' : 'Вход'}
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
