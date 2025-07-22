import { useState, useEffect } from 'react';
import './App.css';

function App() {
  const [showAuth, setShowAuth] = useState(false);
  const [isLogin, setIsLogin] = useState(true);
  const [darkMode, setDarkMode] = useState(false);


  useEffect(() => {

    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    

    const savedMode = localStorage.getItem('darkMode');
    

    setDarkMode(savedMode ? savedMode === 'true' : prefersDark);
    

    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    const handleChange = (e) => setDarkMode(e.matches);
    mediaQuery.addListener(handleChange);
    
    return () => mediaQuery.removeListener(handleChange);
  }, []);


  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark-theme');
    } else {
      document.documentElement.classList.remove('dark-theme');
    }
    localStorage.setItem('darkMode', darkMode.toString());
  }, [darkMode]);

  const toggleTheme = () => {
    setDarkMode(!darkMode);
  };

  return (
    <div className="app-container">
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
          <button 
            className="theme-toggle"
            onClick={toggleTheme}
            aria-label={darkMode ? 'Switch to light mode' : 'Switch to dark mode'}
          >
            {darkMode ? (
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <path d="M12 3c.132 0 .263 0 .393 0a7.5 7.5 0 0 0 7.92 12.446a9 9 0 1 1-8.313-12.454z" />
              </svg>
            ) : (
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <circle cx="12" cy="12" r="5" />
                <path d="M12 1v2" />
                <path d="M12 21v2" />
                <path d="M4.22 4.22l1.42 1.42" />
                <path d="M18.36 18.36l1.42 1.42" />
                <path d="M1 12h2" />
                <path d="M21 12h2" />
                <path d="M4.22 19.78l1.42-1.42" />
                <path d="M18.36 5.64l1.42-1.42" />
              </svg>
            )}
          </button>
          <button 
            className="auth-btn"
            onClick={() => setShowAuth(true)}
          >
            Sign In
          </button>
        </div>
      </header>

      <main className="hero-section">
        <div className="hero-content">
          <h1>Smart Video Project Management</h1>
          <p className="subtitle">Organize, track and collaborate on your video projects with ease</p>
          <div className="cta-buttons">
            <button className="primary-btn">Get Started</button>
            <button className="secondary-btn">Watch Demo</button>
          </div>
        </div>
        <div className="hero-image">
          <div className="network-animation">
            <div className="node node1"></div>
            <div className="node node2"></div>
            <div className="node node3"></div>
            <div className="node node4"></div>
            <div className="node node5"></div>
            
            <svg className="connections" width="100%" height="100%">
              <line className="line line1" x1="50%" y1="30%" x2="30%" y2="50%"/>
              <line className="line line2" x1="50%" y1="30%" x2="70%" y2="50%"/>
              <line className="line line3" x1="30%" y1="50%" x2="50%" y2="70%"/>
              <line className="line line4" x1="70%" y1="50%" x2="50%" y2="70%"/>
              <line className="line line5" x1="50%" y1="70%" x2="50%" y2="90%"/>
            </svg>
          </div>
        </div>
      </main>

      {showAuth && (
        <div className="auth-modal">
          <div className="auth-container">
            <button 
              className="close-btn"
              onClick={() => setShowAuth(false)}
            >
              &times;
            </button>
            <h2>{isLogin ? 'Welcome Back' : 'Create Account'}</h2>
            
            <form onSubmit={(e) => e.preventDefault()}>
              {!isLogin && (
                <div className="form-group">
                  <input 
                    type="text" 
                    placeholder="Full Name" 
                    className="form-input"
                  />
                </div>
              )}
              
              <div className="form-group">
                <input 
                  type="email" 
                  placeholder="Email Address" 
                  className="form-input"
                />
              </div>
              
              <div className="form-group">
                <input 
                  type="password" 
                  placeholder="Password" 
                  className="form-input"
                />
              </div>
              
              {!isLogin && (
                <div className="form-group">
                  <input 
                    type="password" 
                    placeholder="Confirm Password" 
                    className="form-input"
                  />
                </div>
              )}
              
              {isLogin && (
                <div className="remember-forgot">
                  <label className="remember-me">
                    <input type="checkbox" /> Remember me
                  </label>
                  <a href="#forgot" className="forgot-password">Forgot password?</a>
                </div>
              )}
              
              <button type="submit" className="auth-submit-btn">
                {isLogin ? 'Sign In' : 'Sign Up'}
              </button>
            </form>
            
            <div className="auth-divider">
              <span>or</span>
            </div>
            
            <button className="social-auth-btn google-btn">
              Continue with Google
            </button>
            
            <button className="social-auth-btn github-btn">
              Continue with GitHub
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
          </div>
        </div>
      )}
    </div>
  );
}

export default App;