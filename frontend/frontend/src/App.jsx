import { useState, useEffect } from 'react';
import './App.css';

function App() {
  const [showAuth, setShowAuth] = useState(false);
  const [isLogin, setIsLogin] = useState(true);

  useEffect(() => {
    // Анимация будет работать автоматически благодаря CSS
  }, []);

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
        <button 
          className="auth-btn"
          onClick={() => setShowAuth(true)}
        >
          Sign In
        </button>
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