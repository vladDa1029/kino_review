import { useEffect, useState } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import { useAuth } from './context/useAuth';
import HomePage from './pages/HomePage';
import Projects from './pages/Projects';
import ProfilePage from './pages/ProfilePage';
import AuthModal from './components/AuthModal';
import ProtectedRoute from './components/ProtectedRoute';
import ThemeToggle from './components/ThemeToggle';
import AppToastContainer from './components/ToastContainer';
import UserList from './components/UserList';
import './App.css';

const ProfileIcon = () => (
  <svg
    viewBox="0 0 24 24"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    aria-hidden="true"
  >
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

function App() {
  const { token, handleLogout, isAuthModalOpen, setIsAuthModalOpen } = useAuth();
  const [darkMode, setDarkMode] = useState(false);
  const [isProfileOpen, setIsProfileOpen] = useState(false);

  useEffect(() => {
    const savedMode = localStorage.getItem('darkMode');
    setDarkMode(savedMode ? savedMode === 'true' : true);
  }, []);

  useEffect(() => {
    document.body.className = darkMode ? 'dark-theme' : '';
  }, [darkMode]);

  useEffect(() => {
    if (!token) {
      setIsProfileOpen(false);
    }
  }, [token]);

  const toggleTheme = () => {
    const newMode = !darkMode;
    setDarkMode(newMode);
    localStorage.setItem('darkMode', newMode);
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
        <div className="header-controls">
          <ThemeToggle darkMode={darkMode} onToggle={toggleTheme} />
          {token ? (
            <>
              <button
                type="button"
                className="icon-circle-btn profile-trigger-btn"
                onClick={() => setIsProfileOpen(true)}
                aria-label="Открыть профиль"
                title="Профиль"
              >
                <ProfileIcon />
              </button>
              <button className="auth-btn" onClick={handleLogout}>Выйти</button>
            </>
          ) : (
            <button
              className="auth-btn"
              onClick={() => setIsAuthModalOpen(true)}
            >
              Войти
            </button>
          )}
        </div>
      </header>

      <Routes>
        <Route path="/" element={<HomePage onOpenAuth={() => setIsAuthModalOpen(true)} />} />
        <Route path="/projects" element={<ProtectedRoute><Projects /></ProtectedRoute>} />
        <Route path="/profile" element={<Navigate to="/projects" replace />} />
        <Route path="/users" element={<ProtectedRoute><UserList /></ProtectedRoute>} />
        <Route path="/welcome" element={<ProtectedRoute><UserList /></ProtectedRoute>} />
      </Routes>

      <ProfilePage isOpen={isProfileOpen} onClose={() => setIsProfileOpen(false)} />

      <AuthModal
        showAuth={isAuthModalOpen}
        setShowAuth={setIsAuthModalOpen}
      />
    </div>
  );
}

export default App;
