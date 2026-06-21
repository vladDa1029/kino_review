import { Navigate, useParams } from 'react-router-dom';
import EmailActionLayout from '../components/EmailActionLayout';
import { useAuth } from '../context/useAuth';

const ShiftRedirectPage = () => {
  const { projectId, shiftId } = useParams();
  const { token, isAuthReady, setIsAuthModalOpen } = useAuth();

  if (!isAuthReady) {
    return <EmailActionLayout tone="loading" title="Загрузка…" message="Проверяем вашу сессию." />;
  }

  if (!token) {
    return (
      <EmailActionLayout
        eyebrow="Смена"
        tone="info"
        title="Войдите в аккаунт"
        message="Войдите в KinoFlow, чтобы открыть смену из напоминания."
      >
        <button type="button" className="primary-btn" onClick={() => setIsAuthModalOpen(true)}>
          Войти
        </button>
      </EmailActionLayout>
    );
  }

  return <Navigate to="/shifts" replace state={{ projectId, shiftId }} />;
};

export default ShiftRedirectPage;
