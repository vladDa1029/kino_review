import { useEffect, useState } from 'react';
import { Route, Routes, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from './context/useAuth';
import AuthModal from './components/AuthModal';
import ProtectedRoute from './components/ProtectedRoute';
import ThemeToggle from './components/ThemeToggle';
import AppToastContainer from './components/ToastContainer';
import UserList from './components/UserList';
import HomePage from './pages/HomePage';
import ProfilePage from './pages/ProfilePage';
import Projects from './pages/Projects';
import './App.css';

const MenuIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
    <path d="M4 7H20" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    <path d="M4 12H20" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    <path d="M4 17H14" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
  </svg>
);

const HomeIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
    <path
      d="M4 11.5L12 4L20 11.5V20H14.5V14.5H9.5V20H4V11.5Z"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinejoin="round"
    />
  </svg>
);

const WorkspaceIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
    <rect x="3" y="4" width="18" height="16" rx="2.5" stroke="currentColor" strokeWidth="1.8" />
    <path d="M3 10H21" stroke="currentColor" strokeWidth="1.8" />
    <path d="M9 20V10" stroke="currentColor" strokeWidth="1.8" />
  </svg>
);

const ProfileIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
    <path
      d="M12 12C14.7614 12 17 9.76142 17 7C17 4.23858 14.7614 2 12 2C9.23858 2 7 4.23858 7 7C7 9.76142 9.23858 12 12 12Z"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
    <path
      d="M4 21C4.86167 17.5522 8.03827 15 12 15C15.9617 15 19.1383 17.5522 20 21"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);

const LogoutIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
    <path
      d="M10 7V5.5C10 4.67157 10.6716 4 11.5 4H18.5C19.3284 4 20 4.67157 20 5.5V18.5C20 19.3284 19.3284 20 18.5 20H11.5C10.6716 20 10 19.3284 10 18.5V17"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
    />
    <path d="M14 12H4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    <path
      d="M7 9L4 12L7 15"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);

function App() {
  const navigate = useNavigate();
  const location = useLocation();
  const { token, handleLogout, isAuthModalOpen, setIsAuthModalOpen } = useAuth();
  const [darkMode, setDarkMode] = useState(false);
  const [isAppMenuOpen, setIsAppMenuOpen] = useState(false);

  useEffect(() => {
    const savedMode = localStorage.getItem('darkMode');
    setDarkMode(savedMode ? savedMode === 'true' : true);
  }, []);

  useEffect(() => {
    document.body.className = darkMode ? 'dark-theme' : '';
  }, [darkMode]);

  useEffect(() => {
    if (!token) {
      setIsAppMenuOpen(false);
    }
  }, [token]);

  useEffect(() => {
    setIsAppMenuOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    if (!isAppMenuOpen) {
      return undefined;
    }

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    const handleKeyDown = (event) => {
      if (event.key === 'Escape') {
        setIsAppMenuOpen(false);
      }
    };

    window.addEventListener('keydown', handleKeyDown);

    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isAppMenuOpen]);

  const toggleTheme = () => {
    const newMode = !darkMode;
    setDarkMode(newMode);
    localStorage.setItem('darkMode', newMode);
  };

  const handleMenuBackdropMouseDown = (event) => {
    if (event.target === event.currentTarget) {
      setIsAppMenuOpen(false);
    }
  };

  const handleMenuNavigation = (path) => {
    navigate(path);
    setIsAppMenuOpen(false);
  };

  const handleMenuLogout = () => {
    setIsAppMenuOpen(false);
    handleLogout();
  };

  return (
    <div className={`app-container ${darkMode ? 'dark-theme' : ''}`}>
      <AppToastContainer darkMode={darkMode} />

      <header className="app-header">
        <div className="logo-container">
          <h1 className="logo">KinoFlow</h1>
        </div>

        <nav className="nav-links">
          <a href="#features">Возможности</a>
          <a href="#pricing">Тарифы</a>
          <a href="#about">О платформе</a>
        </nav>

        <div className={`header-controls ${token ? 'is-authenticated' : ''}`}>
          <ThemeToggle darkMode={darkMode} onToggle={toggleTheme} />
          {token ? (
            <button
              type="button"
              className="icon-circle-btn menu-trigger-btn"
              onClick={() => setIsAppMenuOpen(true)}
              aria-label="Открыть меню"
              title="Меню"
            >
              <MenuIcon />
            </button>
          ) : (
            <button className="auth-btn" onClick={() => setIsAuthModalOpen(true)}>
              Войти
            </button>
          )}
        </div>
      </header>

      <Routes>
        <Route path="/" element={<HomePage onOpenAuth={() => setIsAuthModalOpen(true)} />} />
        <Route
          path="/projects"
          element={(
            <ProtectedRoute>
              <Projects />
            </ProtectedRoute>
          )}
        />
        <Route
          path="/profile"
          element={(
            <ProtectedRoute>
              <ProfilePage />
            </ProtectedRoute>
          )}
        />
        <Route
          path="/users"
          element={(
            <ProtectedRoute>
              <UserList />
            </ProtectedRoute>
          )}
        />
        <Route
          path="/welcome"
          element={(
            <ProtectedRoute>
              <UserList />
            </ProtectedRoute>
          )}
        />
      </Routes>

      {token && isAppMenuOpen ? (
        <div className="auth-modal app-drawer-backdrop" onMouseDown={handleMenuBackdropMouseDown}>
          <aside
            className="app-drawer-shell"
            role="dialog"
            aria-modal="true"
            aria-labelledby="app-drawer-title"
          >
            <button
              type="button"
              className="close-btn app-drawer-close"
              onClick={() => setIsAppMenuOpen(false)}
              aria-label="Закрыть меню"
            >
              &times;
            </button>

            <div className="app-drawer-scroll">
              <div className="app-drawer-header">
                <div className="app-drawer-brand-mark">K</div>
                <div className="app-drawer-brand-copy">
                  <span className="projects-panel-eyebrow">Меню</span>
                  <h2 id="app-drawer-title">KinoFlow</h2>
                  <p>Быстрый доступ к разделам аккаунта.</p>
                </div>
              </div>

              <nav className="app-drawer-nav" aria-label="Навигация приложения">
                <button
                  type="button"
                  className={`app-drawer-link ${location.pathname === '/' ? 'is-active' : ''}`}
                  onClick={() => handleMenuNavigation('/')}
                >
                  <HomeIcon />
                  <span>Проекты</span>
                </button>

                <button
                  type="button"
                  className={`app-drawer-link ${location.pathname === '/projects' ? 'is-active' : ''}`}
                  onClick={() => handleMenuNavigation('/projects')}
                >
                  <WorkspaceIcon />
                  <span>Рабочая область</span>
                </button>

                <button
                  type="button"
                  className={`app-drawer-link ${location.pathname === '/profile' ? 'is-active' : ''}`}
                  onClick={() => handleMenuNavigation('/profile')}
                >
                  <ProfileIcon />
                  <span>Профиль</span>
                </button>
              </nav>

              <div className="app-drawer-footer">
                <button
                  type="button"
                  className="app-drawer-link is-danger"
                  onClick={handleMenuLogout}
                >
                  <LogoutIcon />
                  <span>Выход из профиля</span>
                </button>
              </div>
            </div>
          </aside>
        </div>
      ) : null}

      <AuthModal showAuth={isAuthModalOpen} setShowAuth={setIsAuthModalOpen} />
    </div>
  );
}

export default App;
