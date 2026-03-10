import { useState, useEffect } from 'react';
import { Routes, Route } from 'react-router-dom';
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

function App() {
  const { token, handleLogout, isAuthModalOpen, setIsAuthModalOpen } = useAuth();
  const [darkMode, setDarkMode] = useState(false);

  useEffect(() => {
    const savedMode = localStorage.getItem('darkMode');
    setDarkMode(savedMode ? savedMode === 'true' : true);
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
            <button className="auth-btn" onClick={handleLogout}>Выйти</button>
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
        <Route path="/profile" element={<ProtectedRoute><ProfilePage /></ProtectedRoute>} />
        <Route path="/users" element={<ProtectedRoute><UserList /></ProtectedRoute>} />
        <Route path="/welcome" element={<ProtectedRoute><UserList /></ProtectedRoute>} />
      </Routes>

      <AuthModal
        showAuth={isAuthModalOpen}
        setShowAuth={setIsAuthModalOpen}
      />
    </div>
  );
}

export default App;
