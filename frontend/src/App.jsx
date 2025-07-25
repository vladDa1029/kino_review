import { useState, useEffect } from 'react';
import './App.css';
import { toast, ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

function App() {
  const [showAuth, setShowAuth] = useState(false);
  const [isLogin, setIsLogin] = useState(true);
  const [darkMode, setDarkMode] = useState(false);
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    confirmPassword: ''
  });
  const [passwordRequirements, setPasswordRequirements] = useState({
    length: false,
    uppercase: false,
    number: false,
    specialChar: false
  });
  const [passwordStrength, setPasswordStrength] = useState(0);
  const [showPassword, setShowPassword] = useState(false);
  const [animationStep, setAnimationStep] = useState(0);
  const [token, setToken] = useState(localStorage.getItem('token') || null);
  const [userData, setUserData] = useState(null);

  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);

  useEffect(() => {
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const savedMode = localStorage.getItem('darkMode');
    setDarkMode(savedMode ? savedMode === 'true' : prefersDark);
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    const handleChange = (e) => setDarkMode(e.matches);
    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, []);


  useEffect(() => {
    const timer = setTimeout(() => {
      setAnimationStep((prev) => (prev < 5 ? prev + 1 : prev));
    }, 500);
    return () => clearTimeout(timer);
  }, [animationStep]);

  useEffect(() => {
    if (!isLogin && formData.password) {
      checkPasswordStrength(formData.password);

    }
  }, [formData.password, formData.confirmPassword, isLogin]); 

  useEffect(() => {
    if (token) {
      fetchUserData();
    }
  }, [token]);

  const API_BASE_URL = 'http://127.0.0.1:8000';

  const checkPasswordStrength = (pass) => {
    const requirements = {
      length: pass.length >= 8,
      uppercase: /[A-Z]/.test(pass),
      number: /[0-9]/.test(pass),
      specialChar: /[^A-Za-z0-9]/.test(pass)
    };
    setPasswordRequirements(requirements);
    const strength = Object.values(requirements).filter(Boolean).length;
    setPasswordStrength(strength);
  };


  const getPasswordStrengthColor = () => {
    const colors = ['#ff4757', '#ff6b81', '#feca57', '#2ecc71', '#1dd1a1'];
    return colors[passwordStrength] || colors[0];
  };

  const getPasswordHint = () => {
    if (formData.password.length === 0) return 'Enter your password';
    const missing = [];
    if (!passwordRequirements.length) missing.push('at least 8 characters');
    if (!passwordRequirements.uppercase) missing.push('one uppercase letter');
    if (!passwordRequirements.number) missing.push('one number');
    if (!passwordRequirements.specialChar) missing.push('one special character');
    return missing.length > 0 
      ? `Missing: ${missing.join(', ')}`
      : 'Strong password!';
  };

  const toggleTheme = () => {
    const newMode = !darkMode;
    setDarkMode(newMode);
    localStorage.setItem('darkMode', newMode);
  };

  const togglePasswordVisibility = () => {
    setShowPassword(!showPassword);
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleLogin = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: new URLSearchParams({
          grant_type: 'password',
          username: formData.email, 
          password: formData.password
        })
      });
      let data;
      const contentType = response.headers.get("content-type");
      if (contentType && contentType.indexOf("application/json") !== -1) {
        data = await response.json();
      } else {
        data = await response.text();
      }

      if (!response.ok) {
        let errorMessage = 'Login failed';
        if (data && typeof data === 'object' && data.detail) {
          errorMessage = data.detail;
        } else if (typeof data === 'string') {
          errorMessage = data || errorMessage;
        }
        throw new Error(errorMessage);
      }

      setToken(data.access_token);
      localStorage.setItem('token', data.access_token);
      toast.success('Successfully logged in!');
      setShowAuth(false);
      setIsAuthModalOpen(false); 
    } catch (error) {
      console.error('Login error:', error);

      if (error instanceof TypeError && error.message === 'Failed to fetch') {
             toast.error('Network error: Could not connect to the server. Please check if the server is running and CORS is configured.');
      } else {
             toast.error(error.message || 'Login failed');
      }
    }
  };


  const handleRegister = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/user`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({

          email: formData.email,
          password: formData.password,

        })
      });

      let data;
      const contentType = response.headers.get("content-type");
      if (contentType && contentType.indexOf("application/json") !== -1) {
          data = await response.json();
      } else {
          data = await response.text();
      }

      if (!response.ok) {
        let errorMessage = 'Registration failed';
        if (data && typeof data === 'object' && data.detail) {
          errorMessage = data.detail;
        } else if (typeof data === 'string') {
          errorMessage = data || errorMessage;
        }
        throw new Error(errorMessage);
      }


      toast.success('Registration successful! Please login.');
      setIsLogin(true); 
      setIsAuthModalOpen(true); 

      setFormData({ ...formData, password: '', confirmPassword: '' }); 
    } catch (error) {
      console.error('Registration error:', error);

      if (error instanceof TypeError && error.message === 'Failed to fetch') {
             toast.error('Network error: Could not connect to the server. Please check if the server is running and CORS is configured.');
      } else {
             toast.error(error.message || 'Registration failed');
      }
    }
  };


  const fetchUserData = async () => {

    if (!token) {
       console.log('Нет токена для получения данных пользователя');
       setUserData(null);
       return;
    }

    console.log('Получение данных пользователя с токеном:', token);
    try {
      const response = await fetch(`${API_BASE_URL}/user`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
         const errorText = await response.text();
         console.error('Ошибка получения данных пользователя:', response.status, errorText);
         if(response.status === 401) {

             handleLogout();
             toast.error('Session expired. Please log in again.');
         } else {

             toast.error(`Failed to fetch user data: ${response.status}: ${errorText}`);
         }

        return; 
      }

      const data = await response.json();
      console.log('Данные пользователя получены:', data);
      
      // --- ПРОВЕРКА is_active ---
      if (data.is_active === false) {
          console.warn('Пользователь заблокирован:', data.email);
          toast.error('Your account has been deactivated. Please contact support.');
          handleLogout(); 
          return;
      }

      
      setUserData(data);
    } catch (error) {

      console.error('Ошибка сети или обработки при получении данных пользователя:', error);

      if(token) {
          handleLogout();
          toast.error('Error loading user data. Please log in again.');
      }

    }
  };

  const handleLogout = () => {
    setToken(null);
    setUserData(null);
    localStorage.removeItem('token');
    toast.info('Logged out successfully');
    setIsAuthModalOpen(false); 
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!isLogin && (passwordStrength < 3 || formData.password !== formData.confirmPassword)) {
      toast.warning('Please fix password errors before submitting');
      return;
    }
    if (isLogin) {
      await handleLogin();
    } else {
      await handleRegister();
    }
  };

  const handleNodeClick = (nodeNumber) => {
    setAnimationStep(nodeNumber);
  };

  return (
    <div className={`app-container ${darkMode ? 'dark-theme' : ''}`}>
      <ToastContainer 
        position="top-right"
        autoClose={5000}
        hideProgressBar={false}
        newestOnTop={false}
        closeOnClick
        rtl={false}
        pauseOnFocusLoss
        draggable
        pauseOnHover
        theme={darkMode ? 'dark' : 'light'}
      />
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
          {token ? (
            <button 
              className="auth-btn"
              onClick={handleLogout}
            >
              Logout
            </button>
          ) : (
            <button 
              className="auth-btn"
              onClick={() => {
                setShowAuth(true);
                setIsAuthModalOpen(true); 
              }}
            >
              Sign In
            </button>
          )}
        </div>
      </header>
      <main className="hero-section">
        <div className="hero-content">
          <h1 className={animationStep >= 1 ? 'fade-in' : ''}>Smart Video Project Management</h1>
          <p className={`subtitle ${animationStep >= 2 ? 'fade-in' : ''}`}>
            Organize, track and collaborate on your video projects with ease
          </p>
          <div className={`cta-buttons ${animationStep >= 3 ? 'fade-in' : ''}`}>
            <button className="primary-btn">Get Started</button>
            <button className="secondary-btn">Watch Demo</button>
          </div>
        </div>
        <div className="hero-image">
          <div className="network-animation">
            {}
            <svg className="connections" width="100%" height="100%">
              <defs>
                <linearGradient id="gradientLine" x1="0%" y1="0%" x2="100%" y2="0%">
                  <stop offset="0%" style={{ stopColor: '#3498db', stopOpacity: 1 }} />
                  <stop offset="100%" style={{ stopColor: '#8e44ad', stopOpacity: 1 }} />
                </linearGradient>
              </defs>
              <line 
                className={`line line1 ${animationStep >= 1 ? 'draw' : ''}`} 
                x1="50%" y1="30%" x2="30%" y2="50%"
              />
              <line 
                className={`line line2 ${animationStep >= 2 ? 'draw' : ''}`} 
                x1="50%" y1="30%" x2="70%" y2="50%"
              />
              <line 
                className={`line line3 ${animationStep >= 3 ? 'draw' : ''}`} 
                x1="30%" y1="50%" x2="50%" y2="70%"
              />
              <line 
                className={`line line4 ${animationStep >= 4 ? 'draw' : ''}`} 
                x1="70%" y1="50%" x2="50%" y2="70%"
              />
              <line 
                className={`line line5 ${animationStep >= 5 ? 'draw' : ''}`} 
                x1="50%" y1="70%" x2="50%" y2="90%"
              />
            </svg>
            {[1, 2, 3, 4, 5].map((node) => (
              <div 
                key={node}
                className={`node node${node} ${animationStep >= node ? 'active' : ''}`}
                onClick={() => handleNodeClick(node)}
              />
            ))}
          </div>
        </div>
      </main>
      {}
      {showAuth && (
        <div className={`auth-modal ${isAuthModalOpen ? 'open' : ''}`}>
          <div className="auth-container">
            <div className="auth-content">
              <button 
                className="close-btn"
                onClick={() => {
                  setShowAuth(false);
                  setIsAuthModalOpen(false); // Закрываем модалку с анимацией
                }}
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
                      type={showPassword ? "text" : "password"}
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
                      onClick={togglePasswordVisibility}
                      aria-label={showPassword ? "Hide password" : "Show password"}
                    >
                      {showPassword ? (
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                          <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                          <line x1="1" y1="1" x2="23" y2="23" />
                        </svg>
                      ) : (
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                          <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                          <circle cx="12" cy="12" r="3" />
                        </svg>
                      )}
                    </button>
                  </div>
                  {!isLogin && (
                    <div className="password-feedback">
                      <div className="password-strength">
                        <span>Strength: </span>
                        <div className="strength-meter">
                          {[1, 2, 3, 4].map((level) => (
                            <div 
                              key={level}
                              className="strength-segment"
                              style={{
                                backgroundColor: passwordStrength >= level 
                                  ? getPasswordStrengthColor() 
                                  : '#e0e0e0'
                              }}
                            />
                          ))}
                        </div>
                        <span className="strength-label" style={{color: getPasswordStrengthColor()}}>
                          {['Weak', 'Fair', 'Good', 'Strong'][passwordStrength - 1] || 'Very Weak'}
                        </span>
                      </div>
                      <div className="password-hints">
                        <p className="hint-text">{getPasswordHint()}</p>
                        <div className="requirement-list">
                          <span className={passwordRequirements.length ? 'met' : ''}>✓ 8+ characters</span>
                          <span className={passwordRequirements.uppercase ? 'met' : ''}>✓ Uppercase letter</span>
                          <span className={passwordRequirements.number ? 'met' : ''}>✓ Number</span>
                          <span className={passwordRequirements.specialChar ? 'met' : ''}>✓ Special char</span>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
                {!isLogin && (
                  <div className="form-group password-input-container">
                    <div className="password-input-wrapper">
                      <input 
                        type={showPassword ? "text" : "password"}
                        name="confirmPassword"
                        placeholder="Confirm Password" 
                        className="form-input"
                        value={formData.confirmPassword}
                        onChange={handleInputChange}
                        required
                      />
                      <button 
                        type="button"
                        className="password-toggle"
                        onClick={togglePasswordVisibility}
                        aria-label={showPassword ? "Hide password" : "Show password"}
                      >
                        {showPassword ? (
                          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                            <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                            <line x1="1" y1="1" x2="23" y2="23" />
                          </svg>
                        ) : (
                          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                            <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                            <circle cx="12" cy="12" r="3" />
                          </svg>
                        )}
                      </button>
                    </div>
                    {formData.confirmPassword && formData.password !== formData.confirmPassword && (
                      <p className="password-error">Passwords don't match</p>
                    )}
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
                <button 
                  type="submit" 
                  className="auth-submit-btn"
                  disabled={!isLogin && (passwordStrength < 3 || formData.password !== formData.confirmPassword)}
                >
                  {isLogin ? 'Sign In' : 'Sign Up'}
                </button>
              </form>
              <div className="auth-divider">
                <span>or</span>
              </div>
              <button className="social-auth-btn google-btn">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                  <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
                  <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
                  <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
                  <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
                </svg>
                Continue with Google
              </button>
              <button className="social-auth-btn github-btn">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                  <path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22" />
                </svg>
                Continue with GitHub
              </button>
              <p className="auth-switch">
                {isLogin ? "Don't have an account? " : "Already have an account? "}
                <span 
                  onClick={() => {
                    setIsLogin(!isLogin);
                    setFormData({...formData, password: '', confirmPassword: '' /* , name: '' */ });
                  }}
                  className="switch-link"
                >
                  {isLogin ? 'Sign up' : 'Sign in'}
                </span>
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;