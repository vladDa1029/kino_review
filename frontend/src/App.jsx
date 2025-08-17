import { useState, useEffect } from 'react';
import { useAuth } from './hooks/useAuth';
import HomePage from './pages/HomePage';
import AuthModal from './components/AuthModal';
import ThemeToggle from './components/ThemeToggle';
import AppToastContainer from './components/ToastContainer';
import './App.css';

function App() {
  const [darkMode, setDarkMode] = useState(false);
  const [showAuth, setShowAuth] = useState(false);
  const [isLogin, setIsLogin] = useState(true);

  const { token, userData, handleLogin, handleRegister, handleLogout } = useAuth();

  useEffect(() => {
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const savedMode = localStorage.getItem('darkMode');
    setDarkMode(savedMode ? savedMode === 'true' : prefersDark);
  }, []);

  useEffect(() => {
    document.body.className = darkMode ? 'dark-theme' : '';
  }, [darkMode]);

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
          <h1 className="logo">ShotTracker</h1>
        </div>
        <nav className="nav-links">
          <a href="#features">Features</a>
          <a href="#pricing">Pricing</a>
          <a href="#about">About</a>
        </nav>
        <div className="header-controls">
          <ThemeToggle darkMode={darkMode} onToggle={toggleTheme} />
          {token ? (
            <button className="auth-btn" onClick={handleLogout}>Logout</button>
          ) : (
            <button
              className="auth-btn"
              onClick={() => {
                setShowAuth(true);
                setIsLogin(true);
              }}
            >
              Sign In
            </button>
          )}
        </div>
      </header>

      <HomePage />

      <AuthModal
        isLogin={isLogin}
        setIsLogin={setIsLogin}
        showAuth={showAuth}
        setShowAuth={setShowAuth}
        onLogin={handleLogin}
        onRegister={handleRegister}
      />
    </div>
  );
}

export default App;