import { useAuth, useTheme } from './hooks';

const Header = () => {
  const { token, setIsAuthModalOpen, handleLogout } = useAuth();
  const { darkMode } = useTheme();

  return (
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
        <ThemeToggle />
        {token ? (
          <button className="auth-btn" onClick={handleLogout}>
            Logout
          </button>
        ) : (
          <button 
            className="auth-btn"
            onClick={() => setIsAuthModalOpen(true)}
          >
            Sign In
          </button>
        )}
      </div>
    </header>
  );
};

export default Header;