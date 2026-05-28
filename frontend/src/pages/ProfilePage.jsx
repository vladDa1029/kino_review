import { useCallback, useEffect, useMemo, useState } from 'react';
import { toast } from 'react-toastify';
import { ApiError } from '../services/httpClient';
import { useAuth } from '../context/useAuth';
import {
  createSpareTime,
  createUserDescription,
  deleteSpareTime,
  getSpareTime,
  getUserDescription,
  listSpareTimes,
  updateSpareTime,
  updateUserDescription,
} from '../services/api';
import { formatDateTime, toDateTimeLocalValue, toIsoDateTime } from '../utils/dateTime';
import { isProfileComplete, setStoredProfileCompletion } from '../utils/profileCompletion';

const initialProfile = {
  username: '',
  phone: '',
};

const initialSpareTimeForm = {
  startTime: '',
  endTime: '',
};

const defaultMultiDayForm = {
  startTime: '09:00',
  endTime: '18:00',
};

const weekDayLabels = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];

const pad = (value) => String(value).padStart(2, '0');

const toDateKey = (date) =>
  `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;

const fromDateKey = (dateKey) => {
  const [year, month, day] = dateKey.split('-').map(Number);
  return new Date(year, month - 1, day);
};

const buildLocalDateTime = (dateKey, timeValue) => {
  const [hours, minutes] = timeValue.split(':').map(Number);
  const date = fromDateKey(dateKey);
  date.setHours(hours, minutes, 0, 0);
  return date;
};

const startOfDay = (date) => new Date(date.getFullYear(), date.getMonth(), date.getDate());

const sortSpareTimes = (items = []) =>
  [...items].sort((left, right) => new Date(left.start_time) - new Date(right.start_time));

const buildAvailabilityMap = (items) => {
  const map = new Map();

  items.forEach((item) => {
    const start = new Date(item.start_time);
    const end = new Date(item.end_time);

    if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) {
      return;
    }

    const cursor = startOfDay(start);
    const lastDay = startOfDay(end);

    while (cursor <= lastDay) {
      const key = toDateKey(cursor);
      const currentItems = map.get(key) || [];
      currentItems.push(item);
      map.set(key, currentItems);
      cursor.setDate(cursor.getDate() + 1);
    }
  });

  return map;
};

const buildCalendarDays = (visibleMonth, availabilityMap, selectedDateKey, todayKey) => {
  const firstDayOfMonth = new Date(visibleMonth.getFullYear(), visibleMonth.getMonth(), 1);
  const firstWeekDay = (firstDayOfMonth.getDay() + 6) % 7;
  const gridStart = new Date(firstDayOfMonth);
  gridStart.setDate(firstDayOfMonth.getDate() - firstWeekDay);

  return Array.from({ length: 35 }, (_, index) => {
    const date = new Date(gridStart);
    date.setDate(gridStart.getDate() + index);

    const dateKey = toDateKey(date);
    const items = availabilityMap.get(dateKey) || [];

    return {
      date,
      dateKey,
      label: date.getDate(),
      isCurrentMonth: date.getMonth() === visibleMonth.getMonth(),
      isToday: dateKey === todayKey,
      isSelected: dateKey === selectedDateKey,
      availabilityCount: items.length,
    };
  });
};

const capitalize = (value) => (value ? `${value[0].toUpperCase()}${value.slice(1)}` : '');

const monthFormatter = new Intl.DateTimeFormat('ru-RU', {
  month: 'long',
  year: 'numeric',
});

const selectedDateFormatter = new Intl.DateTimeFormat('ru-RU', {
  day: 'numeric',
  month: 'long',
});

const CalendarIcon = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true">
    <path d="M7 3v3" />
    <path d="M17 3v3" />
    <path d="M4 9h16" />
    <rect x="4" y="5" width="16" height="15" rx="2" />
  </svg>
);

const CheckCircleIcon = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true">
    <circle cx="12" cy="12" r="9" />
    <path d="M8 12.5l2.5 2.5L16 9.5" />
  </svg>
);

const CopyIcon = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true">
    <rect x="9" y="9" width="10" height="10" rx="2" />
    <path d="M7 15H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h7a2 2 0 0 1 2 2v1" />
  </svg>
);

const InfoIcon = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true">
    <circle cx="12" cy="12" r="9" />
    <path d="M12 10v5" />
    <path d="M12 7h.01" />
  </svg>
);

const SettingsIcon = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true">
    <circle cx="12" cy="12" r="3" />
    <path d="M19.4 15a1 1 0 0 0 .2 1.1l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1 1 0 0 0-1.1-.2 1 1 0 0 0-.6.9V20a2 2 0 1 1-4 0v-.2a1 1 0 0 0-.6-.9 1 1 0 0 0-1.1.2l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1 1 0 0 0 .2-1.1 1 1 0 0 0-.9-.6H4a2 2 0 1 1 0-4h.2a1 1 0 0 0 .9-.6 1 1 0 0 0-.2-1.1l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1 1 0 0 0 1.1.2 1 1 0 0 0 .6-.9V4a2 2 0 1 1 4 0v.2a1 1 0 0 0 .6.9 1 1 0 0 0 1.1-.2l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1 1 0 0 0-.2 1.1 1 1 0 0 0 .9.6H20a2 2 0 1 1 0 4h-.2a1 1 0 0 0-.9.6Z" />
  </svg>
);

const PlusIcon = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true">
    <path d="M12 5v14" />
    <path d="M5 12h14" />
  </svg>
);

const ProfilePage = () => {
  const { userData, authEmail } = useAuth();
  const [profile, setProfile] = useState(initialProfile);
  const [savedProfile, setSavedProfile] = useState(initialProfile);
  const [descriptionId, setDescriptionId] = useState(null);
  const [isProfileLoading, setIsProfileLoading] = useState(true);
  const [isSubmittingProfile, setIsSubmittingProfile] = useState(false);

  const [spareTimes, setSpareTimes] = useState([]);
  const [spareTimeForm, setSpareTimeForm] = useState(initialSpareTimeForm);
  const [editingSpareTimeId, setEditingSpareTimeId] = useState(null);
  const [isSpareTimesLoading, setIsSpareTimesLoading] = useState(true);
  const [isSubmittingSpareTime, setIsSubmittingSpareTime] = useState(false);
  const [loadingSpareTimeId, setLoadingSpareTimeId] = useState(null);
  const [deletingSpareTimeId, setDeletingSpareTimeId] = useState(null);

  const [visibleMonth, setVisibleMonth] = useState(() => startOfDay(new Date()));
  const [selectedDateKey, setSelectedDateKey] = useState(() => toDateKey(new Date()));
  const [selectedAvailabilityDateKeys, setSelectedAvailabilityDateKeys] = useState([]);
  const [isAvailabilityFormVisible, setIsAvailabilityFormVisible] = useState(false);

  const handleProfileChange = (event) => {
    const { name, value } = event.target;
    setProfile((prev) => ({ ...prev, [name]: value }));
  };

  const handleSpareTimeChange = (event) => {
    const { name, value } = event.target;
    setSpareTimeForm((prev) => ({ ...prev, [name]: value }));
  };

  const resetSpareTimeForm = useCallback(() => {
    setSpareTimeForm(initialSpareTimeForm);
    setEditingSpareTimeId(null);
    setSelectedAvailabilityDateKeys([]);
  }, []);

  const loadDescription = useCallback(async () => {
    try {
      const data = await getUserDescription();
      const nextProfile = {
        username: data.username || '',
        phone: data.phone || '',
      };

      setDescriptionId(data.oid);
      setProfile(nextProfile);
      setSavedProfile(nextProfile);
      setStoredProfileCompletion(isProfileComplete(nextProfile));
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) {
        setDescriptionId(null);
        setProfile(initialProfile);
        setSavedProfile(initialProfile);
        setStoredProfileCompletion(false);
      } else {
        toast.error(error.message || 'Не удалось загрузить описание профиля');
      }
    } finally {
      setIsProfileLoading(false);
    }
  }, []);

  const loadSpareTimes = useCallback(async () => {
    try {
      const data = await listSpareTimes();
      setSpareTimes(sortSpareTimes(data.items || []));
    } catch (error) {
      toast.error(error.message || 'Не удалось загрузить личные окна доступности');
    } finally {
      setIsSpareTimesLoading(false);
    }
  }, []);

  useEffect(() => {
    const today = startOfDay(new Date());
    setVisibleMonth(today);
    setSelectedDateKey(toDateKey(today));
    setIsProfileLoading(true);
    setIsSpareTimesLoading(true);
    loadDescription();
    loadSpareTimes();
  }, [loadDescription, loadSpareTimes]);

  const availabilityMap = useMemo(() => buildAvailabilityMap(spareTimes), [spareTimes]);
  const todayKey = toDateKey(new Date());
  const userId =
    userData?.user_id ||
    userData?.userId ||
    userData?.sub ||
    userData?.id ||
    userData?.oid ||
    '';
  const userEmail =
    userData?.email ||
    userData?.preferred_username ||
    userData?.login ||
    userData?.username ||
    authEmail ||
    '';

  useEffect(() => {
    const keysInMonth = [...availabilityMap.keys()]
      .filter((key) => {
        const date = fromDateKey(key);
        return date.getFullYear() === visibleMonth.getFullYear() && date.getMonth() === visibleMonth.getMonth();
      })
      .sort();

    const selectedDate = fromDateKey(selectedDateKey);
    const isSelectedDateVisibleMonth =
      selectedDate.getFullYear() === visibleMonth.getFullYear() &&
      selectedDate.getMonth() === visibleMonth.getMonth();

    if (!isSelectedDateVisibleMonth) {
      const fallbackKey =
        keysInMonth[0] || toDateKey(new Date(visibleMonth.getFullYear(), visibleMonth.getMonth(), 1));
      setSelectedDateKey(fallbackKey);
    }
  }, [availabilityMap, selectedDateKey, visibleMonth]);

  const calendarDays = useMemo(
    () => buildCalendarDays(visibleMonth, availabilityMap, selectedDateKey, todayKey),
    [availabilityMap, selectedDateKey, todayKey, visibleMonth],
  );

  const monthlyWindows = useMemo(
    () =>
      spareTimes.filter((item) => {
        const start = new Date(item.start_time);
        return start.getFullYear() === visibleMonth.getFullYear() && start.getMonth() === visibleMonth.getMonth();
      }),
    [spareTimes, visibleMonth],
  );

  const selectedDateWindows = useMemo(
    () => sortSpareTimes(availabilityMap.get(selectedDateKey) || []),
    [availabilityMap, selectedDateKey],
  );

  const selectedAvailabilityDateSet = useMemo(
    () => new Set(selectedAvailabilityDateKeys),
    [selectedAvailabilityDateKeys],
  );

  const selectedAvailabilityDatesLabel = useMemo(
    () => selectedAvailabilityDateKeys.map((dateKey) => selectedDateFormatter.format(fromDateKey(dateKey))).join(', '),
    [selectedAvailabilityDateKeys],
  );

  const monthLabel = capitalize(monthFormatter.format(visibleMonth));
  const selectedDateLabel = selectedDateFormatter.format(fromDateKey(selectedDateKey));
  const completionPercent = [profile.username, profile.phone].filter((value) => value.trim()).length * 50;
  const isProfileDirty =
    profile.username.trim() !== savedProfile.username.trim() ||
    profile.phone.trim() !== savedProfile.phone.trim();
  const isProfileReady = isProfileComplete(profile);

  const handleCopyUserId = async () => {
    if (!userId || !navigator?.clipboard?.writeText) {
      return;
    }

    try {
      await navigator.clipboard.writeText(userId);
      toast.success('ID пользователя скопирован');
    } catch {
      toast.error('Не удалось скопировать ID');
    }
  };

  const handleProfileSubmit = async (event) => {
    event.preventDefault();

    if (!isProfileReady) {
      toast.warning('Заполните ФИО и телефон, чтобы продолжить работу');
      return;
    }

    setIsSubmittingProfile(true);

    try {
      const payload = {
        username: profile.username.trim(),
        phone: profile.phone.trim(),
      };

      if (descriptionId) {
        await updateUserDescription(descriptionId, payload);
      } else {
        await createUserDescription(payload);
      }

      await loadDescription();
      setStoredProfileCompletion(true);
      toast.success('Профиль сохранен');
    } catch (error) {
      toast.error(error.message || 'Не удалось сохранить профиль');
    } finally {
      setIsSubmittingProfile(false);
    }
  };

  const handleSpareTimeSubmit = async (event) => {
    event.preventDefault();

    const startTime = editingSpareTimeId
      ? toIsoDateTime(spareTimeForm.startTime)
      : toIsoDateTime(buildLocalDateTime(selectedDateKey, spareTimeForm.startTime));
    const endTime = editingSpareTimeId
      ? toIsoDateTime(spareTimeForm.endTime)
      : toIsoDateTime(buildLocalDateTime(selectedDateKey, spareTimeForm.endTime));

    if (!startTime || !endTime) {
      toast.error(editingSpareTimeId ? 'Укажите корректные дату и время' : 'Укажите корректное время');
      return;
    }

    if (new Date(startTime) >= new Date(endTime)) {
      toast.error('Время окончания должно быть позже времени начала');
      return;
    }

    if (!editingSpareTimeId && selectedAvailabilityDateKeys.length === 0) {
      toast.error('Выберите хотя бы один день на календаре');
      return;
    }

    setIsSubmittingSpareTime(true);

    try {
      if (editingSpareTimeId) {
        await updateSpareTime(editingSpareTimeId, { start_time: startTime, end_time: endTime });
        toast.success('Окно доступности обновлено');
      } else {
        await Promise.all(
          selectedAvailabilityDateKeys.map((dateKey) =>
            createSpareTime({
              start_time: buildLocalDateTime(dateKey, spareTimeForm.startTime).toISOString(),
              end_time: buildLocalDateTime(dateKey, spareTimeForm.endTime).toISOString(),
            }),
          ),
        );
        toast.success(`Окна доступности добавлены: ${selectedAvailabilityDateKeys.length}`);
      }

      resetSpareTimeForm();
      setIsAvailabilityFormVisible(false);
      await loadSpareTimes();
    } catch (error) {
      toast.error(error.message || 'Не удалось сохранить окно доступности');
    } finally {
      setIsSubmittingSpareTime(false);
    }
  };

  const handleEditSpareTime = async (spareTimeId) => {
    try {
      setLoadingSpareTimeId(spareTimeId);
      const data = await getSpareTime(spareTimeId);

      setEditingSpareTimeId(data.oid);
      setSpareTimeForm({
        startTime: toDateTimeLocalValue(data.start_time),
        endTime: toDateTimeLocalValue(data.end_time),
      });
      setSelectedAvailabilityDateKeys([]);
      setSelectedDateKey(toDateKey(new Date(data.start_time)));
      setVisibleMonth(startOfDay(new Date(data.start_time)));
      setIsAvailabilityFormVisible(true);
    } catch (error) {
      toast.error(error.message || 'Не удалось загрузить окно доступности');
    } finally {
      setLoadingSpareTimeId(null);
    }
  };

  const handleDeleteSpareTime = async (spareTimeId) => {
    const confirmed = window.confirm('Удалить это окно доступности?');

    if (!confirmed) {
      return;
    }

    try {
      setDeletingSpareTimeId(spareTimeId);
      await deleteSpareTime(spareTimeId);
      setSpareTimes((prev) => prev.filter((item) => item.oid !== spareTimeId));

      if (editingSpareTimeId === spareTimeId) {
        resetSpareTimeForm();
      }

      toast.success('Окно доступности удалено');
    } catch (error) {
      toast.error(error.message || 'Не удалось удалить окно доступности');
    } finally {
      setDeletingSpareTimeId(null);
    }
  };

  const handleMonthChange = (direction) => {
    setVisibleMonth((prev) => new Date(prev.getFullYear(), prev.getMonth() + direction, 1));
  };

  const handleCreateAvailability = () => {
    resetSpareTimeForm();
    setSpareTimeForm(defaultMultiDayForm);
    setSelectedAvailabilityDateKeys([selectedDateKey]);
    setIsAvailabilityFormVisible(true);
  };

  const handleCalendarDaySelect = (dateKey) => {
    setSelectedDateKey(dateKey);

    if (!isAvailabilityFormVisible || editingSpareTimeId) {
      return;
    }

    setSelectedAvailabilityDateKeys((prev) => {
      if (prev.includes(dateKey)) {
        return prev.filter((key) => key !== dateKey);
      }

      return [...prev, dateKey].sort();
    });
  };

  const handleCancelProfileEdit = () => {
    setProfile(savedProfile);
  };

  const handleCancelAvailability = () => {
    resetSpareTimeForm();
    setIsAvailabilityFormVisible(false);
  };

  return (
    <section className="profile-route-page">
      <div className="profile-modal-shell profile-route-shell profile-dashboard-shell">
        <div className="profile-modal-scroll profile-route-scroll profile-dashboard">
          <form className="profile-card-surface profile-top-card" onSubmit={handleProfileSubmit}>
            <div className="profile-top-header">
              <div>
                <h1 className="profile-top-title">Профиль пользователя</h1>
              </div>
              <div className="profile-top-actions">
                <button
                  type="button"
                  className="secondary-btn profile-top-btn"
                  onClick={handleCancelProfileEdit}
                  disabled={!isProfileDirty || isSubmittingProfile}
                >
                  Сбросить
                </button>
                <button
                  type="submit"
                  className="profile-save-btn profile-top-btn"
                  disabled={isSubmittingProfile || !isProfileDirty || isProfileLoading}
                >
                  {isSubmittingProfile ? 'Сохранение...' : 'Сохранить'}
                </button>
              </div>
            </div>

            <div className="profile-top-body">
              <div className="profile-content-grid">
                <div className="profile-field-grid">
                  <label className="field-block profile-dashboard-field">
                    <span>ФИО</span>
                    <input
                      name="username"
                      type="text"
                      value={profile.username}
                      onChange={handleProfileChange}
                      placeholder="Введите ФИО"
                      className="profile-input"
                      required
                    />
                  </label>

                  <label className="field-block profile-dashboard-field">
                    <span>Email</span>
                    <input
                      type="text"
                      value={userEmail || ''}
                      placeholder="Email текущего пользователя"
                      className="profile-input profile-readonly-input"
                      readOnly
                    />
                  </label>

                  <label className="field-block profile-dashboard-field">
                    <span>Телефон</span>
                    <input
                      name="phone"
                      type="tel"
                      value={profile.phone}
                      onChange={handleProfileChange}
                      placeholder="+79991234567"
                      className="profile-input"
                      required
                    />
                  </label>
                </div>

                <div className="profile-meta-grid">
                  {userId ? (
                    <div className="profile-meta-chip profile-id-chip">
                      <span>ID: {userId}</span>
                      <button type="button" className="profile-copy-btn" onClick={handleCopyUserId} aria-label="Скопировать ID">
                        <CopyIcon />
                      </button>
                    </div>
                  ) : null}

                  <div className="profile-meta-chip">
                    <CalendarIcon />
                    <span>Окон в месяце: {monthlyWindows.length}</span>
                  </div>

                  <div className={`profile-meta-chip profile-completion-chip ${isProfileReady ? 'is-complete' : ''}`}>
                    <CheckCircleIcon />
                    <span>Заполнено: {completionPercent}%</span>
                  </div>
                </div>

                {!isProfileReady ? (
                  <div className="profile-warning-banner">
                    Заполните ФИО и телефон. Пока эти поля пустые, переход в другие разделы будет недоступен.
                  </div>
                ) : null}
              </div>
            </div>
          </form>

          <section className="profile-availability-layout">
            <div className="profile-card-surface profile-calendar-section">
              <div className="profile-section-head">
                <div>
                  <h2 className="profile-panel-title">Доступность</h2>
                  <p className="profile-panel-subtitle">Календарь доступности по дням</p>
                </div>
              </div>

              <div className="profile-calendar-card profile-calendar-card-large">
                <div className="profile-calendar-toolbar">
                  <button type="button" className="calendar-nav-btn" onClick={() => handleMonthChange(-1)} aria-label="Предыдущий месяц">
                    ‹
                  </button>
                  <strong>{monthLabel}</strong>
                  <button type="button" className="calendar-nav-btn" onClick={() => handleMonthChange(1)} aria-label="Следующий месяц">
                    ›
                  </button>
                </div>

                <div className="profile-weekdays">
                  {weekDayLabels.map((day) => (
                    <span key={day}>{day}</span>
                  ))}
                </div>

                <div className="profile-calendar-grid">
                  {calendarDays.map((day) => (
                    <button
                      key={day.dateKey}
                      type="button"
                      className={[
                        'calendar-day-btn',
                        day.isCurrentMonth ? '' : 'is-muted',
                        day.isToday ? 'is-today' : '',
                        day.isSelected ? 'is-selected' : '',
                        day.availabilityCount > 0 ? 'has-availability' : '',
                        selectedAvailabilityDateSet.has(day.dateKey) ? 'is-pending-availability' : '',
                      ].filter(Boolean).join(' ')}
                      onClick={() => handleCalendarDaySelect(day.dateKey)}
                    >
                      <span>{day.label}</span>
                      {day.availabilityCount > 1 ? <small>{day.availabilityCount}</small> : null}
                    </button>
                  ))}
                </div>

                <div className="profile-calendar-legend">
                  <span className="profile-legend-item">
                    <i className="is-available" />
                    Доступные окна
                  </span>
                  <span className="profile-legend-item">
                    <i className="is-multiple" />
                    Несколько окон
                  </span>
                  <span className="profile-legend-item">
                    <i className="is-empty" />
                    Нет доступных окон
                  </span>
                  <span className="profile-legend-item">
                    <i className="is-muted" />
                    Вне месяца
                  </span>
                </div>
              </div>
            </div>

            <aside className="profile-card-surface profile-selected-panel">
              <div className="profile-selected-panel-head">
                <div>
                  <h2 className="profile-panel-title">{selectedDateLabel}</h2>
                  <p className="profile-panel-subtitle">
                    {selectedDateWindows.length > 0
                      ? `Найдено окон: ${selectedDateWindows.length}`
                      : 'Нет доступных окон'}
                  </p>
                </div>
                <button type="button" className="profile-save-btn profile-add-window-btn" onClick={handleCreateAvailability}>
                  <PlusIcon />
                  <span>Добавить окно</span>
                </button>
              </div>

              {isSpareTimesLoading ? (
                <div className="profile-day-empty">Загрузка окон доступности...</div>
              ) : selectedDateWindows.length > 0 ? (
                <div className="profile-window-stack">
                  {selectedDateWindows.map((item) => (
                    <article key={item.oid} className="profile-window-item">
                      <div className="profile-window-copy">
                        <strong className="profile-window-time">{formatDateTime(item.start_time)}</strong>
                        <p className="profile-window-range">{formatDateTime(item.end_time)}</p>
                      </div>
                      <div className="profile-window-action-row">
                        <button
                          type="button"
                          className="ghost-action-btn"
                          onClick={() => handleEditSpareTime(item.oid)}
                          disabled={loadingSpareTimeId === item.oid}
                        >
                          {loadingSpareTimeId === item.oid ? '...' : 'Изменить'}
                        </button>
                        <button
                          type="button"
                          className="ghost-action-btn danger"
                          onClick={() => handleDeleteSpareTime(item.oid)}
                          disabled={deletingSpareTimeId === item.oid}
                        >
                          {deletingSpareTimeId === item.oid ? '...' : 'Удалить'}
                        </button>
                      </div>
                    </article>
                  ))}
                </div>
              ) : (
                <div className="profile-day-empty">
                  <CalendarIcon />
                  <strong>Окна на выбранный день появятся здесь</strong>
                  <p>Добавьте окно, чтобы сделать этот день доступным.</p>
                </div>
              )}

              {isAvailabilityFormVisible ? (
                <form className="profile-quick-form" onSubmit={handleSpareTimeSubmit}>
                  <div className="profile-editor-head">
                    <h3>{editingSpareTimeId ? 'Редактирование окна' : 'Быстрое добавление окна'}</h3>
                    <p>
                      {editingSpareTimeId
                        ? 'Измените дату и время для выбранного окна.'
                        : 'Выберите один или несколько дней в календаре и задайте общий интервал времени.'}
                    </p>
                  </div>

                  {!editingSpareTimeId ? (
                    <div className="profile-selected-days">
                      <span>Выбрано дней: {selectedAvailabilityDateKeys.length}</span>
                      <p>{selectedAvailabilityDatesLabel || 'Нажмите на даты в календаре.'}</p>
                    </div>
                  ) : null}

                  <div className="profile-quick-form-grid">
                    <label className="field-block" htmlFor="spare-time-start">
                      <span>Начало</span>
                      <input
                        id="spare-time-start"
                        name="startTime"
                        type={editingSpareTimeId ? 'datetime-local' : 'time'}
                        value={spareTimeForm.startTime}
                        onChange={handleSpareTimeChange}
                        className="profile-input"
                        required
                      />
                    </label>

                    <label className="field-block" htmlFor="spare-time-end">
                      <span>Конец</span>
                      <input
                        id="spare-time-end"
                        name="endTime"
                        type={editingSpareTimeId ? 'datetime-local' : 'time'}
                        value={spareTimeForm.endTime}
                        onChange={handleSpareTimeChange}
                        className="profile-input"
                        required
                      />
                    </label>
                  </div>

                  <div className="inline-actions">
                    <button type="button" className="secondary-btn" onClick={handleCancelAvailability}>
                      Отмена
                    </button>
                    <button type="submit" className="profile-save-btn compact" disabled={isSubmittingSpareTime}>
                      {isSubmittingSpareTime
                        ? 'Сохранение...'
                        : editingSpareTimeId
                          ? 'Обновить окно'
                          : 'Добавить окно'}
                    </button>
                  </div>
                </form>
              ) : (
                <div className="profile-quick-form profile-quick-form-closed">
                  <div className="profile-editor-head">
                    <h3>Быстрое добавление окна</h3>
                    <p>Нажмите кнопку выше, чтобы открыть форму для выбранного дня.</p>
                  </div>
                </div>
              )}
            </aside>
          </section>

          <div className="profile-card-surface profile-footer-bar">
            <div className="profile-footer-note">
              <InfoIcon />
              <span>Время указано по вашему часовому поясу: Москва (GMT+3)</span>
            </div>
            <button type="button" className="ghost-action-btn profile-footer-settings">
              <SettingsIcon />
              <span>Настройки доступности</span>
            </button>
          </div>
        </div>
      </div>
    </section>
  );
};

export default ProfilePage;
