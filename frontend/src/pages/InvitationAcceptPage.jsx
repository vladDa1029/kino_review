import { useEffect, useRef, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import EmailActionLayout from '../components/EmailActionLayout';
import { useAuth } from '../context/useAuth';
import { acceptProjectInvitationByToken } from '../services/api';

const STATUS_COPY = {
  success: {
    tone: 'success',
    title: 'Приглашение принято',
    message: 'Теперь вы участник проекта. Откройте «Мои проекты», чтобы продолжить работу.',
  },
  expired: {
    tone: 'error',
    title: 'Ссылка устарела',
    message: 'Срок действия приглашения истёк. Попросите организатора пригласить вас заново.',
  },
  invalid: {
    tone: 'error',
    title: 'Ссылка недействительна',
    message: 'Эта ссылка приглашения недействительна или относится к другому аккаунту.',
  },
  error: {
    tone: 'error',
    title: 'Не удалось принять',
    message: 'Сейчас не получилось принять приглашение. Попробуйте позже.',
  },
};

const LOADING = {
  tone: 'loading',
  title: 'Принимаем приглашение…',
  message: 'Пожалуйста, подождите — это займёт пару секунд.',
};

const InvitationAcceptPage = () => {
  const { token } = useParams();
  const { token: sessionToken, isAuthReady, setIsAuthModalOpen } = useAuth();
  const [state, setState] = useState(null);
  const requestedRef = useRef(false);

  useEffect(() => {
    if (!isAuthReady || !sessionToken || requestedRef.current) {
      return;
    }
    requestedRef.current = true;
    setState(LOADING);

    acceptProjectInvitationByToken(token)
      .then((data) => {
        setState(STATUS_COPY[data?.status] ?? STATUS_COPY.error);
      })
      .catch((error) => {
        if (error?.status === 401) {
          // Session expired between page load and request — let the user re-auth and retry.
          requestedRef.current = false;
          setState(null);
          setIsAuthModalOpen(true);
          return;
        }
        setState(STATUS_COPY.error);
      });
  }, [isAuthReady, sessionToken, token, setIsAuthModalOpen]);

  if (!isAuthReady) {
    return (
      <EmailActionLayout tone="loading" title="Загрузка…" message="Проверяем вашу сессию." />
    );
  }

  if (!sessionToken) {
    return (
      <EmailActionLayout
        eyebrow="Приглашение в проект"
        tone="info"
        title="Войдите в аккаунт"
        message="Чтобы принять приглашение в проект, войдите в свой аккаунт KinoFlow."
      >
        <button type="button" className="primary-btn" onClick={() => setIsAuthModalOpen(true)}>
          Войти
        </button>
      </EmailActionLayout>
    );
  }

  const view = state ?? LOADING;

  return (
    <EmailActionLayout
      eyebrow="Приглашение в проект"
      tone={view.tone}
      title={view.title}
      message={view.message}
    >
      {view.tone !== 'loading' ? (
        <Link to="/my-projects" className="primary-btn">
          Перейти к проектам
        </Link>
      ) : null}
    </EmailActionLayout>
  );
};

export default InvitationAcceptPage;
