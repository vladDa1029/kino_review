import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/useAuth';
import { useProjectContext } from '../context/useProjectContext';
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
    <path d="M2 2L22 22" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
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
  const {
    projects,
    activeProjectId,
    isProjectsLoading,
    refreshProjects,
    setActiveProjectId,
  } = useProjectContext();
  const navigate = useNavigate();
  const [step, setStep] = useState('auth');
  const [formData, setFormData] = useState({ email: '', password: '' });
  const [showPassword, setShowPassword] = useState(false);
  const [passwordRequirements, setPasswordRequirements] = useState({
    length: false,
    uppercase: false,
    number: false,
    specialChar: false,
  });
  const [passwordStrength, setPasswordStrength] = useState(0);

  const handleInputChange = (event) => {
    const { name, value } = event.target;
    setFormData((prev) => ({ ...prev, [name]: value }));

    if (name === 'password' && !isLogin) {
      const { requirements, strength } = checkPasswordStrength(value);
      setPasswordRequirements(requirements);
      setPasswordStrength(strength);
    }
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!isLogin && passwordStrength < 3) {
      return;
    }

    try {
      const response = isLogin
        ? await handleLogin(formData.email, formData.password)
        : await handleRegister(formData.email, formData.password);

      if (response?.access_token) {
        setFormData({ email: '', password: '' });
        setStep('projects');
        await refreshProjects();
      }
    } catch {
      // Ошибки уже показаны в auth-методах.
    }
  };

  const handleClose = () => {
    setShowAuth(false);
    setStep('auth');
  };

  const handleChooseProject = (projectId) => {
    setActiveProjectId(projectId);
    setShowAuth(false);
    setStep('auth');
    navigate('/projects');
  };

  const handleCreateProject = () => {
    setShowAuth(false);
    setStep('auth');
    navigate('/my-projects');
  };

  return (
    showAuth && (
      <div className="auth-modal open">
        <div className={`auth-container ${step === 'projects' ? 'auth-container-wide' : ''}`}>
          <div className="auth-content">
            <button className="close-btn" onClick={handleClose} aria-label="Закрыть окно">
              &times;
            </button>

            {step === 'projects' ? (
              <>
                <div className="project-choice-header">
                  <span className="projects-panel-eyebrow">Выбор проекта</span>
                  <h2>Где будем работать?</h2>
                  <p>
                    Выберите проект, в котором вы участвуете. Рабочая область откроется уже с
                    этим контекстом.
                  </p>
                </div>

                <div className="project-choice-list">
                  {isProjectsLoading ? <p className="helper-note">Загружаем проекты...</p> : null}

                  {!isProjectsLoading && projects.length === 0 ? (
                    <div className="project-choice-empty">
                      <p>У вас пока нет проектов для выбора.</p>
                      <button type="button" className="profile-save-btn compact" onClick={handleCreateProject}>
                        Перейти к проектам
                      </button>
                    </div>
                  ) : null}

                  {!isProjectsLoading &&
                    projects.map((project) => {
                      const projectId = project.oid || project.id;
                      const isActive = activeProjectId === projectId;

                      return (
                        <button
                          key={projectId}
                          type="button"
                          className={`project-choice-card${isActive ? ' is-active' : ''}`}
                          onClick={() => handleChooseProject(projectId)}
                        >
                          <span>{isActive ? 'Выбран сейчас' : 'Проект'}</span>
                          <strong>{project.title}</strong>
                          <small>{project.description || 'Описание не указано'}</small>
                        </button>
                      );
                    })}
                </div>
              </>
            ) : (
              <>
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
                    {isLogin ? 'Нет аккаунта? ' : 'Уже есть аккаунт? '}
                    <span onClick={() => setIsLogin(!isLogin)} className="switch-link">
                      {isLogin ? 'Регистрация' : 'Вход'}
                    </span>
                  </p>
                </form>
              </>
            )}
          </div>
        </div>
      </div>
    )
  );
};

export default AuthModal;
