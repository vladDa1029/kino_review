import { useAuth } from '../context/useAuth';
import { Navigate } from 'react-router-dom';

const ProtectedRoute = ({ children, requireSuperuser = false }) => {
  const { token, isAuthReady, userData } = useAuth();

  if (!isAuthReady) {
    return null;
  }

  if (!token) {
    return <Navigate to="/" replace />;
  }

  if (requireSuperuser && !userData?.is_superuser) {
    return <Navigate to="/my-projects" replace />;
  }

  return children;
};

export default ProtectedRoute;
