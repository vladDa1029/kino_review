import { useCallback, useEffect, useMemo, useState } from 'react';
import { toast } from 'react-toastify';
import { ApiError } from '../services/httpClient';
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

const initialProfile = {
  username: '',
  phone: '',
};

const initialSpareTimeForm = {
  startTime: '',
  endTime: '',
};

const weekDayLabels = ['П', 'В', 'С', 'Ч', 'П', 'С', 'В'];

const pad = (value) => String(value).padStart(2, '0');

const toDateKey = (date) =>
  `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;

const fromDateKey = (dateKey) => {
  const [year, month, day] = dateKey.split('-').map(Number);
  return new Date(year, month - 1, day);
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

const ProfilePage = () => {
  const [profile, setProfile] = useState(initialProfile);
  const [savedProfile, setSavedProfile] = useState(initialProfile);
  const [descriptionId, setDescriptionId] = useState(null);
  const [isProfileLoading, setIsProfileLoading] = useState(true);
  const [isSubmittingProfile, setIsSubmittingProfile] = useState(false);
  const [avatarPreview, setAvatarPreview] = useState('');

  const [spareTimes, setSpareTimes] = useState([]);
  const [spareTimeForm, setSpareTimeForm] = useState(initialSpareTimeForm);
  const [editingSpareTimeId, setEditingSpareTimeId] = useState(null);
  const [isSpareTimesLoading, setIsSpareTimesLoading] = useState(true);
  const [isSubmittingSpareTime, setIsSubmittingSpareTime] = useState(false);
  const [loadingSpareTimeId, setLoadingSpareTimeId] = useState(null);
  const [deletingSpareTimeId, setDeletingSpareTimeId] = useState(null);

  const [visibleMonth, setVisibleMonth] = useState(() => startOfDay(new Date()));
  const [selectedDateKey, setSelectedDateKey] = useState(() => toDateKey(new Date()));
  const [isAvailabilityFormVisible, setIsAvailabilityFormVisible] = useState(false);

  const handleProfileChange = (event) => {
    const { name, value } = event.target;
    setProfile((prev) => ({ ...prev, [name]: value }));
  };

  const handleSpareTimeChange = (event) => {
    const { name, value } = event.target;
    setSpareTimeForm((prev) => ({ ...prev, [name]: value }));
  };

  const resetSpareTimeForm = () => {
    setSpareTimeForm(initialSpareTimeForm);
    setEditingSpareTimeId(null);
  };

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
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) {
        setDescriptionId(null);
        setProfile(initialProfile);
        setSavedProfile(initialProfile);
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

  const handleAvatarChange = (event) => {
    const file = event.target.files?.[0];

    if (!file) {
      return;
    }

    const reader = new FileReader();
    reader.onload = () => {
      if (typeof reader.result === 'string') {
        setAvatarPreview(reader.result);
      }
    };
    reader.readAsDataURL(file);
  };

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

  useEffect(() => {
    const keysInMonth = [...availabilityMap.keys()]
      .filter((key) => {
        const date = fromDateKey(key);
        return (
          date.getFullYear() === visibleMonth.getFullYear() &&
          date.getMonth() === visibleMonth.getMonth()
        );
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
        return (
          start.getFullYear() === visibleMonth.getFullYear() &&
          start.getMonth() === visibleMonth.getMonth()
        );
      }),
    [spareTimes, visibleMonth],
  );

  const selectedDateWindows = useMemo(
    () => sortSpareTimes(availabilityMap.get(selectedDateKey) || []),
    [availabilityMap, selectedDateKey],
  );

  const monthLabel = capitalize(monthFormatter.format(visibleMonth));
  const selectedDateLabel = selectedDateFormatter.format(fromDateKey(selectedDateKey));
  const completionPercent = [profile.username, profile.phone].filter((value) => value.trim()).length * 50;
  const isProfileDirty =
    profile.username.trim() !== savedProfile.username.trim() ||
    profile.phone.trim() !== savedProfile.phone.trim();

  const handleProfileSubmit = async (event) => {
    event.preventDefault();
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
      toast.success('Описание профиля сохранено');
    } catch (error) {
      toast.error(error.message || 'Не удалось сохранить описание профиля');
    } finally {
      setIsSubmittingProfile(false);
    }
  };

  const handleSpareTimeSubmit = async (event) => {
    event.preventDefault();

    const startTime = toIsoDateTime(spareTimeForm.startTime);
    const endTime = toIsoDateTime(spareTimeForm.endTime);

    if (!startTime || !endTime) {
      toast.error('Укажите корректные дату и время');
      return;
    }

    if (new Date(startTime) >= new Date(endTime)) {
      toast.error('Время окончания должно быть позже времени начала');
      return;
    }

    setIsSubmittingSpareTime(true);

    try {
      const payload = { start_time: startTime, end_time: endTime };

      if (editingSpareTimeId) {
        await updateSpareTime(editingSpareTimeId, payload);
        toast.success('Окно доступности обновлено');
      } else {
        await createSpareTime(payload);
        toast.success('Окно доступности добавлено');
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
    setVisibleMonth(
      (prev) => new Date(prev.getFullYear(), prev.getMonth() + direction, 1),
    );
  };

  const handleCreateAvailability = () => {
    resetSpareTimeForm();
    setIsAvailabilityFormVisible((prev) => !prev);
  };

  const handleCancelProfileEdit = () => {
    setProfile(savedProfile);
  };

  return (
    <section className="profile-route-page">
      <div className="profile-modal-shell profile-reference-shell profile-route-shell">
        <div className="profile-modal-scroll profile-reference-scroll profile-route-scroll">
          <form className="profile-hero-card profile-hero-form" onSubmit={handleProfileSubmit}>
            <div className="profile-hero-avatar">
              <label
                className={`profile-avatar-preview profile-reference-avatar ${avatarPreview ? '' : 'is-empty'}`}
                htmlFor="avatar-upload"
              >
                {avatarPreview ? <img src={avatarPreview} alt="Предпросмотр аватара" /> : null}
              </label>
              <input
                id="avatar-upload"
                className="profile-avatar-input"
                type="file"
                accept="image/*"
                onChange={handleAvatarChange}
              />
            </div>

            <div className="profile-hero-content">
              <p className="profile-modal-kicker">Profile</p>
              <div className="profile-hero-inputs">
                <input
                  id="profile-modal-title"
                  name="username"
                  type="text"
                  value={profile.username}
                  onChange={handleProfileChange}
                  placeholder="Введите ФИО"
                  className="profile-hero-input profile-hero-name-input"
                  required
                />
                <input
                  name="phone"
                  type="tel"
                  value={profile.phone}
                  onChange={handleProfileChange}
                  placeholder="+79991234567"
                  className="profile-hero-input profile-hero-phone-input"
                  required
                />
              </div>
              <div className="profile-hero-meta">
                <span>{monthlyWindows.length} окон в месяце</span>
                <span>Заполнено: {completionPercent}%</span>
              </div>
            </div>

            <div className="profile-hero-actions">
              <button
                type="submit"
                className="profile-save-btn compact profile-hero-submit"
                disabled={isSubmittingProfile || !isProfileDirty || isProfileLoading}
              >
                {isSubmittingProfile ? 'Сохранение...' : 'Сохранить'}
              </button>
              <button
                type="button"
                className="secondary-btn profile-hero-action"
                onClick={handleCancelProfileEdit}
                disabled={!isProfileDirty || isSubmittingProfile}
              >
                Сбросить
              </button>
              {!isProfileDirty ? (
                <button
                  type="button"
                  className="profile-hero-hint-btn"
                  disabled
                >
                  Редактируйте прямо здесь
                </button>
              ) : null}
            </div>
          </form>

          <section className="profile-reference-layout profile-reference-layout-single">
            <div className="profile-reference-column">
              <div className="profile-panel-header">
                <div>
                  <h3>Calendar</h3>
                  <p>Личная доступность по дням</p>
                </div>
                <button
                  type="button"
                  className="secondary-btn profile-panel-action"
                  onClick={handleCreateAvailability}
                >
                  {isAvailabilityFormVisible ? 'Скрыть форму' : 'Добавить окно'}
                </button>
              </div>

              <div className="profile-calendar-card">
                <div className="profile-calendar-toolbar">
                  <button
                    type="button"
                    className="calendar-nav-btn"
                    onClick={() => handleMonthChange(-1)}
                    aria-label="Предыдущий месяц"
                  >
                    ‹
                  </button>
                  <strong>{monthLabel}</strong>
                  <button
                    type="button"
                    className="calendar-nav-btn"
                    onClick={() => handleMonthChange(1)}
                    aria-label="Следующий месяц"
                  >
                    ›
                  </button>
                </div>

                <div className="profile-weekdays">
                  {weekDayLabels.map((day, index) => (
                    <span key={`${day}-${index}`}>{day}</span>
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
                      ]
                        .filter(Boolean)
                        .join(' ')}
                      onClick={() => setSelectedDateKey(day.dateKey)}
                    >
                      <span>{day.label}</span>
                      {day.availabilityCount > 0 ? (
                        <small>{day.availabilityCount}</small>
                      ) : null}
                    </button>
                  ))}
                </div>
              </div>

              <div className="profile-day-summary">
                <h4>{selectedDateLabel}</h4>
                <p>
                  {selectedDateWindows.length > 0
                    ? `На этот день найдено ${selectedDateWindows.length} окно(а).`
                    : 'На этот день пока нет доступных окон.'}
                </p>
              </div>

              {isSpareTimesLoading ? (
                <div className="profile-empty-card">Загрузка окон доступности...</div>
              ) : selectedDateWindows.length > 0 ? (
                <div className="profile-window-list">
                  {selectedDateWindows.map((item) => (
                    <article key={item.oid} className="profile-window-card">
                      <div>
                        <strong>{formatDateTime(item.start_time)}</strong>
                        <p>{formatDateTime(item.end_time)}</p>
                      </div>
                      <div className="profile-window-actions">
                        <button
                          type="button"
                          className="ghost-action-btn"
                          onClick={() => handleEditSpareTime(item.oid)}
                          disabled={loadingSpareTimeId === item.oid}
                        >
                          {loadingSpareTimeId === item.oid ? '...' : 'Edit'}
                        </button>
                        <button
                          type="button"
                          className="ghost-action-btn danger"
                          onClick={() => handleDeleteSpareTime(item.oid)}
                          disabled={deletingSpareTimeId === item.oid}
                        >
                          {deletingSpareTimeId === item.oid ? '...' : 'Delete'}
                        </button>
                      </div>
                    </article>
                  ))}
                </div>
              ) : (
                <div className="profile-empty-card">
                  Окна на выбранный день появятся здесь.
                </div>
              )}

              {isAvailabilityFormVisible ? (
                <form className="profile-editor-card" onSubmit={handleSpareTimeSubmit}>
                  <div className="profile-editor-head">
                    <h4>{editingSpareTimeId ? 'Редактирование окна' : 'Новое окно доступности'}</h4>
                    <p>Добавьте диапазон времени, который попадёт в личный календарь.</p>
                  </div>

                  <div className="grid-two-columns">
                    <label className="field-block" htmlFor="spare-time-start">
                      <span>Начало</span>
                      <input
                        id="spare-time-start"
                        name="startTime"
                        type="datetime-local"
                        value={spareTimeForm.startTime}
                        onChange={handleSpareTimeChange}
                        className="profile-input"
                        required
                      />
                    </label>

                    <label className="field-block" htmlFor="spare-time-end">
                      <span>Окончание</span>
                      <input
                        id="spare-time-end"
                        name="endTime"
                        type="datetime-local"
                        value={spareTimeForm.endTime}
                        onChange={handleSpareTimeChange}
                        className="profile-input"
                        required
                      />
                    </label>
                  </div>

                  <div className="inline-actions">
                    <button
                      type="submit"
                      className="profile-save-btn compact"
                      disabled={isSubmittingSpareTime}
                    >
                      {isSubmittingSpareTime
                        ? 'Сохранение...'
                        : editingSpareTimeId
                          ? 'Обновить окно'
                          : 'Добавить окно'}
                    </button>
                    {editingSpareTimeId ? (
                      <button
                        type="button"
                        className="secondary-btn"
                        onClick={resetSpareTimeForm}
                      >
                        Сбросить
                      </button>
                    ) : null}
                  </div>
                </form>
              ) : null}

              {!isAvailabilityFormVisible ? (
                <div className="profile-empty-card subtle">
                  ФИО и телефон редактируются прямо в верхней карточке. Здесь можно открыть только
                  форму доступности.
                </div>
              ) : null}
            </div>
          </section>
        </div>
      </div>
    </section>
  );
};

export default ProfilePage;
