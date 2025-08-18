import { createContext, useContext, useState, useEffect } from 'react';
import { toast } from 'react-toastify';
import authService from '../services/api/authService';

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [token, setToken] = useState(localStorage.getItem('token') || null);
  const [userData, setUserData] = useState(null);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [isLogin, setIsLogin] = useState(true);
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    confirmPassword: ''
  });
  const [showPassword, setShowPassword] = useState(false);

  useEffect(() => {
    if (token) {
      fetchUserData();
    }
  }, [token]);

  const fetchUserData = async () => {
    try {
      const data = await authService.getUserData(token);
      setUserData(data);
    } catch (error) {
      console.error('Error fetching user data:', error);
      if (token) {
        handleLogout();
      }
    }
  };

  const handleLogin = async () => {
    try {
      const { access_token } = await authService.login(formData.email, formData.password);
      setToken(access_token);
      localStorage.setItem('token', access_token);
      toast.success('Successfully logged in!');
      setIsAuthModalOpen(false);
    } catch (error) {
      toast.error(error.message || 'Login failed');
      throw error;
    }
  };

  const handleRegister = async () => {
    try {
      await authService.register(formData.email, formData.password);
      toast.success('Registration successful! Please login.');
      setIsLogin(true);
      setFormData({ ...formData, password: '', confirmPassword: '' });
    } catch (error) {
      toast.error(error.message || 'Registration failed');
      throw error;
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
    if (!isLogin && formData.password !== formData.confirmPassword) {
      toast.warning('Passwords do not match');
      return;
    }
    if (isLogin) {
      await handleLogin();
    } else {
      await handleRegister();
    }
  };

  return (
    <AuthContext.Provider value={{
      token,
      userData,
      isAuthModalOpen,
      setIsAuthModalOpen,
      isLogin,
      setIsLogin,
      formData,
      setFormData,
      showPassword,
      setShowPassword,
      handleSubmit,
      handleLogout,
      handleInputChange: (e) => {
        const { name, value } = e.target;
        setFormData(prev => ({ ...prev, [name]: value }));
      },
      togglePasswordVisibility: () => setShowPassword(!showPassword)
    }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);