import { useAuth } from '../context/useAuth';
import { Navigate } from 'react-router-dom';

const ProtectedRoute = ({ children }) => {
  const { token, isAuthReady } = useAuth();

  if (!isAuthReady) {
    return null;
  }

  if (!token) {
    return <Navigate to="/" replace />;
  }

  return children;
};

export default ProtectedRoute;
