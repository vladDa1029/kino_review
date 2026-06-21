import { useEffect, useRef, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import EmailActionLayout from '../components/EmailActionLayout';
import { confirmReservationByToken } from '../services/api';

const STATUS_COPY = {
  success: {
    tone: 'success',
    title: 'Участие подтверждено',
    message: 'Вы подтвердили участие в смене. Эту страницу можно закрыть.',
  },
  'already-processed': {
    tone: 'info',
    title: 'Уже обработано',
    message: 'Эта бронь уже была обработана ранее. Повторное подтверждение не требуется.',
  },
  expired: {
    tone: 'error',
    title: 'Ссылка устарела',
    message: 'Срок действия ссылки истёк. Попросите организатора прислать новое письмо.',
  },
  invalid: {
    tone: 'error',
    title: 'Ссылка недействительна',
    message: 'Эта ссылка подтверждения недействительна или больше не соответствует брони.',
  },
  error: {
    tone: 'error',
    title: 'Не удалось подтвердить',
    message: 'Сейчас не получилось подтвердить бронь. Попробуйте открыть ссылку позже.',
  },
};

const LOADING = {
  tone: 'loading',
  title: 'Подтверждаем участие…',
  message: 'Пожалуйста, подождите — это займёт пару секунд.',
};

const ReservationConfirmPage = () => {
  const { token } = useParams();
  const [state, setState] = useState(LOADING);
  const requestedRef = useRef(false);

  useEffect(() => {
    if (requestedRef.current) {
      return;
    }
    requestedRef.current = true;

    confirmReservationByToken(token)
      .then((data) => {
        setState(STATUS_COPY[data?.status] ?? STATUS_COPY.error);
      })
      .catch(() => {
        setState(STATUS_COPY.error);
      });
  }, [token]);

  return (
    <EmailActionLayout
      eyebrow="Бронирование"
      tone={state.tone}
      title={state.title}
      message={state.message}
    >
      {state.tone !== 'loading' ? (
        <Link to="/" className="primary-btn">
          На главную
        </Link>
      ) : null}
    </EmailActionLayout>
  );
};

export default ReservationConfirmPage;
