import { useCallback, useEffect, useMemo, useState } from 'react';
import { toast } from 'react-toastify';
import { ApiError } from '../services/httpClient';
import {
  addCameraFreeTime,
  addCameraTripodFreeTime,
  addLightFreeTime,
  addLightTripodFreeTime,
  addMicrofonFreeTime,
  addRequisiteFreeTime,
  addRequisiteImage,
  addSoundFreeTime,
  createCamera,
  createCameraTripod,
  createLight,
  createLightTripod,
  createMicrofon,
  createRequisite,
  createSound,
  deleteCamera,
  deleteCameraTripod,
  deleteLight,
  deleteLightTripod,
  deleteMicrofon,
  deleteRequisite,
  deleteSound,
  getRequisiteImage,
  listCameras,
  listCameraTripods,
  listLights,
  listLightTripods,
  listMicrofons,
  listRequisiteImages,
  listRequisites,
  listSounds,
  removeRequisiteImage,
  reserveAvailability,
  updateCamera,
  updateCameraTripod,
  updateLight,
  updateLightTripod,
  updateMicrofon,
  updateRequisite,
  updateSound,
} from '../services/api';
import { formatDateTime, toIsoDateTime } from '../utils/dateTime';

const resourceOrder = ['microfons', 'cameras', 'camera-tripods', 'lights', 'light-tripods', 'sounds', 'requisites'];

const createInitialResourceForm = () => ({ title: '', description: '', type: '', size: '' });
const createInitialWindowForm = () => ({ startTime: '', endTime: '' });
const createInitialImageForm = () => ({ file: null, title: '', description: '' });

const tableColumns = {
  equipment: [
    { key: 'title', label: 'Название' },
    { key: 'description', label: 'Описание' },
    { key: 'type', label: 'Тип' },
    { key: 'create_at', label: 'Создано', render: (item) => formatDateTime(item.create_at) },
  ],
  requisites: [
    { key: 'title', label: 'Название' },
    { key: 'description', label: 'Описание' },
    { key: 'type', label: 'Тип' },
    { key: 'size', label: 'Размер' },
    { key: 'create_at', label: 'Создано', render: (item) => formatDateTime(item.create_at) },
  ],
};

const resourceMeta = {
  microfons: {
    label: 'Микрофоны',
    one: 'микрофон',
    create: createMicrofon,
    list: listMicrofons,
    update: updateMicrofon,
    remove: deleteMicrofon,
    addFreeTime: addMicrofonFreeTime,
    columns: tableColumns.equipment,
    placeholders: { title: 'Rode NTG5', description: 'Пушка для съемок на площадке', type: 'shotgun' },
    buildPayload: (form) => ({ title: form.title.trim(), description: form.description.trim(), type: form.type.trim() }),
  },
  cameras: {
    label: 'Камеры',
    one: 'камера',
    create: createCamera,
    list: listCameras,
    update: updateCamera,
    remove: deleteCamera,
    addFreeTime: addCameraFreeTime,
    columns: tableColumns.equipment,
    placeholders: { title: 'Sony A7S III', description: 'Основная камера для съемочного дня', type: 'mirrorless' },
    buildPayload: (form) => ({ title: form.title.trim(), description: form.description.trim(), type: form.type.trim() }),
  },
  'camera-tripods': {
    label: 'Штативы для камер',
    one: 'штатив для камеры',
    create: createCameraTripod,
    list: listCameraTripods,
    update: updateCameraTripod,
    remove: deleteCameraTripod,
    addFreeTime: addCameraTripodFreeTime,
    columns: tableColumns.equipment,
    placeholders: { title: 'Manfrotto 190', description: 'Штатив для статичных планов', type: 'tripod' },
    buildPayload: (form) => ({ title: form.title.trim(), description: form.description.trim(), type: form.type.trim() }),
  },
  lights: {
    label: 'Свет',
    one: 'осветитель',
    create: createLight,
    list: listLights,
    update: updateLight,
    remove: deleteLight,
    addFreeTime: addLightFreeTime,
    columns: tableColumns.equipment,
    placeholders: { title: 'Aputure 300D', description: 'Постоянный свет для ключевой сцены', type: 'led' },
    buildPayload: (form) => ({ title: form.title.trim(), description: form.description.trim(), type: form.type.trim() }),
  },
  'light-tripods': {
    label: 'Стойки для света',
    one: 'стойка для света',
    create: createLightTripod,
    list: listLightTripods,
    update: updateLightTripod,
    remove: deleteLightTripod,
    addFreeTime: addLightTripodFreeTime,
    columns: tableColumns.equipment,
    placeholders: { title: 'C-Stand', description: 'Стойка для световых приборов', type: 'stand' },
    buildPayload: (form) => ({ title: form.title.trim(), description: form.description.trim(), type: form.type.trim() }),
  },
  sounds: {
    label: 'Звук',
    one: 'звуковое устройство',
    create: createSound,
    list: listSounds,
    update: updateSound,
    remove: deleteSound,
    addFreeTime: addSoundFreeTime,
    columns: tableColumns.equipment,
    placeholders: { title: 'Zoom F6', description: 'Рекордер для полевого звука', type: 'recorder' },
    buildPayload: (form) => ({ title: form.title.trim(), description: form.description.trim(), type: form.type.trim() }),
  },
  requisites: {
    label: 'Реквизит',
    one: 'реквизит',
    create: createRequisite,
    list: listRequisites,
    update: updateRequisite,
    remove: deleteRequisite,
    addFreeTime: addRequisiteFreeTime,
    columns: tableColumns.requisites,
    supportsImages: true,
    placeholders: { title: 'Винтажная лампа', description: 'Декоративная лампа в теплых тонах', type: 'decor', size: 'm' },
    buildPayload: (form) => ({
      title: form.title.trim(),
      description: form.description.trim(),
      type: form.type.trim(),
      size: form.size.trim(),
    }),
  },
};

const pad = (value) => String(value).padStart(2, '0');
const toDateKey = (value) => {
  const date = value instanceof Date ? value : new Date(value);
  return Number.isNaN(date.getTime()) ? '' : `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
};
const startOfMonth = (date) => new Date(date.getFullYear(), date.getMonth(), 1);

const monthFormatter = new Intl.DateTimeFormat('ru-RU', { month: 'long', year: 'numeric' });
const selectedDateFormatter = new Intl.DateTimeFormat('ru-RU', { day: 'numeric', month: 'long' });
const weekDayLabels = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];

const getColumnValue = (item, column) => (typeof column.render === 'function' ? column.render(item) : item[column.key] || '-');

const getPreviewSource = (image) => {
  const candidate = image?.file || image?.storage_key || '';
  return /^https?:\/\//i.test(candidate) || candidate.startsWith('data:') ? candidate : '';
};

const buildItemCalendarMap = (items) => {
  const map = new Map();

  items.forEach((item) => {
    const dateKey = toDateKey(item.create_at);
    if (!dateKey) return;
    const currentItems = map.get(dateKey) || [];
    currentItems.push(item);
    map.set(dateKey, currentItems);
  });

  return map;
};

const buildCalendarDays = (visibleMonth, itemMap, selectedDateKey, todayKey) => {
  const firstDayOfMonth = new Date(visibleMonth.getFullYear(), visibleMonth.getMonth(), 1);
  const firstWeekDay = (firstDayOfMonth.getDay() + 6) % 7;
  const gridStart = new Date(firstDayOfMonth);
  gridStart.setDate(firstDayOfMonth.getDate() - firstWeekDay);

  return Array.from({ length: 35 }, (_, index) => {
    const date = new Date(gridStart);
    date.setDate(gridStart.getDate() + index);
    const dateKey = toDateKey(date);
    const dayItems = itemMap.get(dateKey) || [];

    return {
      date,
      dateKey,
      label: date.getDate(),
      isCurrentMonth: date.getMonth() === visibleMonth.getMonth(),
      isToday: dateKey === todayKey,
      isSelected: dateKey === selectedDateKey,
      itemCount: dayItems.length,
    };
  });
};

const getWindowPayload = (windowForm) => {
  const start_time = toIsoDateTime(windowForm.startTime);
  const end_time = toIsoDateTime(windowForm.endTime);

  if (!start_time || !end_time) {
    toast.error('Укажите корректные дату и время');
    return null;
  }

  if (new Date(start_time) >= new Date(end_time)) {
    toast.error('Время окончания должно быть позже времени начала');
    return null;
  }

  return { start_time, end_time };
};

const Projects = () => {
  const [activeResource, setActiveResource] = useState(resourceOrder[0]);
  const [form, setForm] = useState(createInitialResourceForm);
  const [editingId, setEditingId] = useState(null);
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [deletingId, setDeletingId] = useState(null);
  const [pagination, setPagination] = useState({ page: 1, pageSize: 20, totalPages: 1, totalCount: 0 });
  const [selectedItemId, setSelectedItemId] = useState(null);
  const [freeTimeForm, setFreeTimeForm] = useState(createInitialWindowForm);
  const [reserveForm, setReserveForm] = useState(createInitialWindowForm);
  const [isSubmittingFreeTime, setIsSubmittingFreeTime] = useState(false);
  const [isSubmittingReservation, setIsSubmittingReservation] = useState(false);
  const [images, setImages] = useState([]);
  const [imageForm, setImageForm] = useState(createInitialImageForm);
  const [imageInputKey, setImageInputKey] = useState(0);
  const [isImagesLoading, setIsImagesLoading] = useState(false);
  const [isUploadingImage, setIsUploadingImage] = useState(false);
  const [selectedImage, setSelectedImage] = useState(null);
  const [loadingImageId, setLoadingImageId] = useState(null);
  const [removingImageId, setRemovingImageId] = useState(null);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [visibleMonth, setVisibleMonth] = useState(() => startOfMonth(new Date()));
  const [selectedDateKey, setSelectedDateKey] = useState(() => toDateKey(new Date()));
  const [activeDateFilterKey, setActiveDateFilterKey] = useState(null);

  const currentResource = useMemo(() => resourceMeta[activeResource], [activeResource]);
  const todayKey = useMemo(() => toDateKey(new Date()), []);

  const selectedItem = useMemo(
    () => items.find((item) => item.oid === selectedItemId) || null,
    [items, selectedItemId],
  );

  const itemsByDate = useMemo(() => buildItemCalendarMap(items), [items]);
  const calendarDays = useMemo(
    () => buildCalendarDays(visibleMonth, itemsByDate, selectedDateKey, todayKey),
    [itemsByDate, selectedDateKey, todayKey, visibleMonth],
  );
  const filteredItems = useMemo(
    () => (activeDateFilterKey ? items.filter((item) => toDateKey(item.create_at) === activeDateFilterKey) : items),
    [activeDateFilterKey, items],
  );
  const selectedDayItems = useMemo(
    () => itemsByDate.get(activeDateFilterKey || selectedDateKey) || [],
    [activeDateFilterKey, itemsByDate, selectedDateKey],
  );

  const resetForm = useCallback(() => {
    setForm(createInitialResourceForm());
    setEditingId(null);
  }, []);

  const resetManagementState = useCallback(() => {
    setSelectedItemId(null);
    setFreeTimeForm(createInitialWindowForm());
    setReserveForm(createInitialWindowForm());
    setImages([]);
    setImageForm(createInitialImageForm());
    setImageInputKey((prev) => prev + 1);
    setSelectedImage(null);
  }, []);

  const fetchItems = useCallback(async () => {
    setLoading(true);

    try {
      const response = await currentResource.list({
        page: pagination.page,
        pageSize: pagination.pageSize,
        sortBy: 'create_at',
        sortDir: 'desc',
      });

      setItems(response.items || []);
      setPagination((prev) => ({
        ...prev,
        totalPages: response.pages || 1,
        totalCount: response.total_count || 0,
      }));
    } catch (error) {
      toast.error(error.message || `Не удалось загрузить ${currentResource.label.toLowerCase()}`);
    } finally {
      setLoading(false);
    }
  }, [currentResource, pagination.page, pagination.pageSize]);

  const loadRequisiteImages = useCallback(async (requisiteId) => {
    if (!requisiteId) {
      setImages([]);
      return;
    }

    setIsImagesLoading(true);

    try {
      const response = await listRequisiteImages(requisiteId);
      setImages(response.items || []);
    } catch (error) {
      toast.error(error.message || 'Не удалось загрузить изображения реквизита');
      setImages([]);
    } finally {
      setIsImagesLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchItems();
  }, [fetchItems]);

  useEffect(() => {
    if (!selectedItemId) {
      return;
    }

    if (!items.some((item) => item.oid === selectedItemId)) {
      resetManagementState();
    }
  }, [items, resetManagementState, selectedItemId]);

  useEffect(() => {
    if (activeResource !== 'requisites' || !selectedItem) {
      setImages([]);
      setSelectedImage(null);
      return;
    }

    loadRequisiteImages(selectedItem.oid);
  }, [activeResource, loadRequisiteImages, selectedItem]);

  useEffect(() => {
    if (activeDateFilterKey && !items.some((item) => toDateKey(item.create_at) === activeDateFilterKey)) {
      setActiveDateFilterKey(null);
    }
  }, [activeDateFilterKey, items]);

  const switchResource = (nextResource) => {
    if (nextResource === activeResource) {
      return;
    }

    setActiveResource(nextResource);
    resetForm();
    resetManagementState();
    setPagination((prev) => ({ ...prev, page: 1, totalPages: 1, totalCount: 0 }));
    setVisibleMonth(startOfMonth(new Date()));
    setSelectedDateKey(toDateKey(new Date()));
    setActiveDateFilterKey(null);
  };

  const handleChange = (event) => {
    const { name, value } = event.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleWindowChange = (setter) => (event) => {
    const { name, value } = event.target;
    setter((prev) => ({ ...prev, [name]: value }));
  };

  const handleImageFieldChange = (event) => {
    const { name, value, files } = event.target;
    setImageForm((prev) => ({ ...prev, [name]: name === 'file' ? files?.[0] || null : value }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();

    const payload = currentResource.buildPayload(form);
    if (!payload.title || !payload.description || !payload.type || (activeResource === 'requisites' && !payload.size)) {
      toast.error('Заполните обязательные поля');
      return;
    }

    setSubmitting(true);

    try {
      if (editingId) {
        await currentResource.update(editingId, payload);
        toast.success(`${currentResource.one} обновлен`);
      } else {
        await currentResource.create(payload);
        toast.success(`${currentResource.one} добавлен`);
      }

      resetForm();
      await fetchItems();
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) {
        toast.error('Объект не найден, список обновлен');
        resetForm();
        await fetchItems();
      } else {
        toast.error(error.message || 'Не удалось сохранить данные');
      }
    } finally {
      setSubmitting(false);
    }
  };

  const handleEdit = (item) => {
    setEditingId(item.oid);
    setForm({
      title: item.title || '',
      description: item.description || '',
      type: item.type || '',
      size: item.size || '',
    });
    setSelectedItemId(item.oid);
  };

  const handleDelete = async (itemId) => {
    if (!window.confirm('Удалить выбранный объект?')) {
      return;
    }

    setDeletingId(itemId);

    try {
      await currentResource.remove(itemId);
      toast.success(`${currentResource.one} удален`);

      if (selectedItemId === itemId) {
        resetManagementState();
      }

      const isLastItemOnPage = items.length === 1 && pagination.page > 1;
      setPagination((prev) => ({ ...prev, page: isLastItemOnPage ? prev.page - 1 : prev.page }));

      if (!isLastItemOnPage) {
        await fetchItems();
      }
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) {
        toast.error('Объект уже удален, список обновлен');
        if (selectedItemId === itemId) {
          resetManagementState();
        }
        await fetchItems();
      } else {
        toast.error(error.message || 'Не удалось удалить объект');
      }
    } finally {
      setDeletingId(null);
    }
  };

  const handleSelectItem = (item) => {
    setSelectedItemId(item.oid);
    setFreeTimeForm(createInitialWindowForm());
    setReserveForm(createInitialWindowForm());
    setImageForm(createInitialImageForm());
    setImageInputKey((prev) => prev + 1);
    setSelectedImage(null);
  };

  const handleAddFreeTime = async (event) => {
    event.preventDefault();

    if (!selectedItem) {
      toast.error('Сначала выберите объект из таблицы');
      return;
    }

    const payload = getWindowPayload(freeTimeForm);
    if (!payload) {
      return;
    }

    setIsSubmittingFreeTime(true);

    try {
      await currentResource.addFreeTime(selectedItem.oid, payload);
      toast.success('Окно доступности добавлено');
      setFreeTimeForm(createInitialWindowForm());
    } catch (error) {
      toast.error(error.message || 'Не удалось добавить окно доступности');
    } finally {
      setIsSubmittingFreeTime(false);
    }
  };

  const handleReserve = async (event) => {
    event.preventDefault();

    if (!selectedItem) {
      toast.error('Сначала выберите объект из таблицы');
      return;
    }

    const payload = getWindowPayload(reserveForm);
    if (!payload) {
      return;
    }

    setIsSubmittingReservation(true);

    try {
      await reserveAvailability({
        owner_id: selectedItem.user_id,
        obj_id: selectedItem.oid,
        ...payload,
      });
      toast.success('Бронирование отправлено');
      setReserveForm(createInitialWindowForm());
    } catch (error) {
      toast.error(error.message || 'Не удалось забронировать окно');
    } finally {
      setIsSubmittingReservation(false);
    }
  };

  const handleImageSubmit = async (event) => {
    event.preventDefault();

    if (!selectedItem) {
      toast.error('Сначала выберите реквизит');
      return;
    }

    if (!imageForm.file || !imageForm.title.trim() || !imageForm.description.trim()) {
      toast.error('Заполните данные изображения и выберите файл');
      return;
    }

    setIsUploadingImage(true);

    try {
      await addRequisiteImage(selectedItem.oid, {
        file: imageForm.file,
        title: imageForm.title.trim(),
        description: imageForm.description.trim(),
      });
      toast.success('Изображение загружено');
      setImageForm(createInitialImageForm());
      setImageInputKey((prev) => prev + 1);
      await loadRequisiteImages(selectedItem.oid);
    } catch (error) {
      toast.error(error.message || 'Не удалось загрузить изображение');
    } finally {
      setIsUploadingImage(false);
    }
  };

  const handleImageDetails = async (imageId) => {
    if (!selectedItem) {
      return;
    }

    setLoadingImageId(imageId);

    try {
      const image = await getRequisiteImage(selectedItem.oid, imageId);
      setSelectedImage(image);
    } catch (error) {
      toast.error(error.message || 'Не удалось получить информацию об изображении');
    } finally {
      setLoadingImageId(null);
    }
  };

  const handleRemoveImage = async (imageId) => {
    if (!selectedItem || !window.confirm('Удалить изображение реквизита?')) {
      return;
    }

    setRemovingImageId(imageId);

    try {
      await removeRequisiteImage(selectedItem.oid, imageId);
      toast.success('Изображение удалено');
      setImages((prev) => prev.filter((image) => image.oid !== imageId));
      setSelectedImage((prev) => (prev?.oid === imageId ? null : prev));
    } catch (error) {
      toast.error(error.message || 'Не удалось удалить изображение');
    } finally {
      setRemovingImageId(null);
    }
  };

  const handlePageChange = (newPage) => {
    if (newPage < 1 || newPage > pagination.totalPages || newPage === pagination.page) {
      return;
    }

    setPagination((prev) => ({ ...prev, page: newPage }));
  };

  const handleCalendarDayClick = (dateKey, date) => {
    setSelectedDateKey(dateKey);
    setVisibleMonth(startOfMonth(date));
    setActiveDateFilterKey((current) => (current === dateKey ? null : dateKey));
  };

  const activeDayLabel = activeDateFilterKey
    ? selectedDateFormatter.format(new Date(`${activeDateFilterKey}T00:00:00`))
    : null;
  const activeResourcePosition = resourceOrder.indexOf(activeResource) + 1;

  return (
    <section className="projects-wrapper">
      <div className={`projects-page projects-dashboard-layout${isSidebarCollapsed ? ' is-sidebar-collapsed' : ''}`}>
        <div className="dashboard-panel projects-overview-panel">
          <div className="projects-overview-copy">
            <span className="projects-panel-eyebrow">Рабочая область</span>
            <h1>{currentResource.label}</h1>
            <p>
              {activeDateFilterKey
                ? `Таблица отфильтрована по дате: ${activeDayLabel}.`
                : 'Добавляйте инвентарь, выбирайте объект и управляйте доступностью в одном экране.'}
            </p>
          </div>

          <div className="projects-overview-stats" aria-label="Сводка рабочей области">
            <div className="projects-stat-card">
              <span>Категория</span>
              <strong>{activeResourcePosition}/{resourceOrder.length}</strong>
            </div>
            <div className="projects-stat-card">
              <span>Всего</span>
              <strong>{pagination.totalCount}</strong>
            </div>
            <div className="projects-stat-card">
              <span>{activeDateFilterKey ? 'В фильтре' : 'На экране'}</span>
              <strong>{filteredItems.length}</strong>
            </div>
          </div>

          <button
            type="button"
            className="secondary-btn projects-layout-toggle"
            onClick={() => setIsSidebarCollapsed((prev) => !prev)}
            aria-expanded={!isSidebarCollapsed}
            aria-controls="projects-categories-panel"
          >
            <span className="projects-layout-toggle-icon" aria-hidden="true">
              {isSidebarCollapsed ? '→' : '←'}
            </span>
            <span>{isSidebarCollapsed ? 'Категории' : 'Скрыть'}</span>
          </button>
        </div>

        <aside id="projects-categories-panel" className="dashboard-panel projects-sidebar">
          <div className="projects-sidebar-heading">
            <span className="projects-panel-eyebrow">Навигация</span>
            <h1>Категории</h1>
          </div>

          <div className="projects-sidebar-nav" role="tablist" aria-label="Категории инвентаря">
            {resourceOrder.map((resourceKey) => {
              const resource = resourceMeta[resourceKey];
              const isActive = resourceKey === activeResource;

              return (
                <button
                  key={resourceKey}
                  type="button"
                  className={`projects-sidebar-button ${isActive ? 'is-active' : ''}`}
                  onClick={() => switchResource(resourceKey)}
                >
                  <span>{resource.label}</span>
                  <small>{isActive ? `${pagination.totalCount} позиций` : 'Открыть'}</small>
                </button>
              );
            })}
          </div>

          <div className="projects-sidebar-note">
            <strong>{currentResource.label}</strong>
            <span>{pagination.totalCount} позиций</span>
          </div>
        </aside>

        <div className="projects-center-column">
          <section className="dashboard-panel">
            <div className="section-heading">
              <h2>{editingId ? `Редактирование: ${currentResource.one}` : `Новый объект: ${currentResource.one}`}</h2>
              <p>Центральная панель отвечает за создание и редактирование элементов выбранной категории.</p>
            </div>

            <form className="stacked-form resource-form" onSubmit={handleSubmit}>
              <label className="field-block">
                <span>Название</span>
                <input
                  name="title"
                  value={form.title}
                  onChange={handleChange}
                  placeholder={currentResource.placeholders.title}
                />
              </label>

              <label className="field-block">
                <span>Описание</span>
                <textarea
                  name="description"
                  value={form.description}
                  onChange={handleChange}
                  placeholder={currentResource.placeholders.description}
                  rows={4}
                />
              </label>

              <div className="grid-two-columns">
                <label className="field-block">
                  <span>Тип</span>
                  <input
                    name="type"
                    value={form.type}
                    onChange={handleChange}
                    placeholder={currentResource.placeholders.type}
                  />
                </label>

                {activeResource === 'requisites' ? (
                  <label className="field-block">
                    <span>Размер</span>
                    <input
                      name="size"
                      value={form.size}
                      onChange={handleChange}
                      placeholder={currentResource.placeholders.size}
                    />
                  </label>
                ) : (
                  <div className="projects-form-placeholder" aria-hidden="true" />
                )}
              </div>

              <div className="inline-actions">
                <button type="submit" className="profile-save-btn compact" disabled={submitting}>
                  {submitting ? 'Сохраняем...' : editingId ? 'Сохранить изменения' : 'Добавить объект'}
                </button>
                <button
                  type="button"
                  className="secondary-btn"
                  onClick={resetForm}
                  disabled={submitting || (!editingId && !form.title && !form.description && !form.type && !form.size)}
                >
                  Очистить
                </button>
              </div>
            </form>
          </section>

          <section className="dashboard-panel management-card">
            <div className="section-heading">
              <h2>Управление выбранным объектом</h2>
              <p>
                {selectedItem
                  ? `Сейчас выбран: ${selectedItem.title}`
                  : 'Выберите запись справа, чтобы открыть управление доступностью, бронированием и медиа.'}
              </p>
            </div>

            {selectedItem ? (
              <>
                <div className="selected-entity-summary">
                  <div>
                    <strong>{selectedItem.title}</strong>
                    <p>{selectedItem.description || 'Без описания'}</p>
                  </div>

                  <dl className="entity-meta-list">
                    <div>
                      <dt>Тип</dt>
                      <dd>{selectedItem.type || '-'}</dd>
                    </div>
                    {activeResource === 'requisites' ? (
                      <div>
                        <dt>Размер</dt>
                        <dd>{selectedItem.size || '-'}</dd>
                      </div>
                    ) : null}
                    <div>
                      <dt>Создано</dt>
                      <dd>{formatDateTime(selectedItem.create_at)}</dd>
                    </div>
                  </dl>
                </div>

                <div className="management-grid projects-management-grid">
                  <section className="management-panel">
                    <h3>Добавить окно доступности</h3>
                    <p className="helper-note">Для техники и реквизита API отдает только добавление окна, без списка истории.</p>
                    <form className="stacked-form" onSubmit={handleAddFreeTime}>
                      <label className="field-block">
                        <span>Начало</span>
                        <input
                          type="datetime-local"
                          name="startTime"
                          value={freeTimeForm.startTime}
                          onChange={handleWindowChange(setFreeTimeForm)}
                        />
                      </label>
                      <label className="field-block">
                        <span>Окончание</span>
                        <input
                          type="datetime-local"
                          name="endTime"
                          value={freeTimeForm.endTime}
                          onChange={handleWindowChange(setFreeTimeForm)}
                        />
                      </label>
                      <button type="submit" className="profile-save-btn compact" disabled={isSubmittingFreeTime}>
                        {isSubmittingFreeTime ? 'Добавляем...' : 'Добавить окно'}
                      </button>
                    </form>
                  </section>

                  <section className="management-panel">
                    <h3>Забронировать интервал</h3>
                    <p className="helper-note">Бронь отправляется на общий endpoint `availability/reserve`.</p>
                    <form className="stacked-form" onSubmit={handleReserve}>
                      <label className="field-block">
                        <span>Начало</span>
                        <input
                          type="datetime-local"
                          name="startTime"
                          value={reserveForm.startTime}
                          onChange={handleWindowChange(setReserveForm)}
                        />
                      </label>
                      <label className="field-block">
                        <span>Окончание</span>
                        <input
                          type="datetime-local"
                          name="endTime"
                          value={reserveForm.endTime}
                          onChange={handleWindowChange(setReserveForm)}
                        />
                      </label>
                      <button type="submit" className="profile-save-btn compact" disabled={isSubmittingReservation}>
                        {isSubmittingReservation ? 'Отправляем...' : 'Забронировать'}
                      </button>
                    </form>
                  </section>
                </div>

                {currentResource.supportsImages ? (
                  <section className="requisite-media-section">
                    <div className="management-panel">
                      <h3>Изображения реквизита</h3>
                      <form className="stacked-form" onSubmit={handleImageSubmit}>
                        <label className="field-block">
                          <span>Файл</span>
                          <input
                            key={imageInputKey}
                            type="file"
                            name="file"
                            accept="image/*"
                            onChange={handleImageFieldChange}
                          />
                        </label>

                        <div className="grid-two-columns">
                          <label className="field-block">
                            <span>Название</span>
                            <input
                              name="title"
                              value={imageForm.title}
                              onChange={handleImageFieldChange}
                              placeholder="Основное фото"
                            />
                          </label>
                          <label className="field-block">
                            <span>Описание</span>
                            <input
                              name="description"
                              value={imageForm.description}
                              onChange={handleImageFieldChange}
                              placeholder="Крупный план"
                            />
                          </label>
                        </div>

                        <button type="submit" className="profile-save-btn compact" disabled={isUploadingImage}>
                          {isUploadingImage ? 'Загружаем...' : 'Загрузить изображение'}
                        </button>
                      </form>
                    </div>

                    <div className="media-grid">
                      <section className="management-panel">
                        <h3>Галерея</h3>
                        <p className="helper-note">
                          {isImagesLoading ? 'Загружаем изображения...' : `Всего изображений: ${images.length}`}
                        </p>
                        <div className="media-grid media-grid-compact">
                          {images.map((image) => (
                            <article key={image.oid} className="media-card">
                              {getPreviewSource(image) ? (
                                <img
                                  className="requisite-image-preview"
                                  src={getPreviewSource(image)}
                                  alt={image.title}
                                />
                              ) : null}
                              <h4>{image.title}</h4>
                              <p>{image.description}</p>
                              <div className="table-actions">
                                <button
                                  type="button"
                                  className="ghost-action-btn"
                                  onClick={() => handleImageDetails(image.oid)}
                                  disabled={loadingImageId === image.oid}
                                >
                                  {loadingImageId === image.oid ? 'Загрузка...' : 'Детали'}
                                </button>
                                <button
                                  type="button"
                                  className="ghost-action-btn danger"
                                  onClick={() => handleRemoveImage(image.oid)}
                                  disabled={removingImageId === image.oid}
                                >
                                  {removingImageId === image.oid ? 'Удаляем...' : 'Удалить'}
                                </button>
                              </div>
                            </article>
                          ))}

                          {!isImagesLoading && images.length === 0 ? (
                            <p className="helper-note">Изображения еще не добавлены.</p>
                          ) : null}
                        </div>
                      </section>

                      {selectedImage ? (
                        <section className="image-details-card">
                          <h3>Детали изображения</h3>
                          {getPreviewSource(selectedImage) ? (
                            <img
                              className="requisite-image-preview"
                              src={getPreviewSource(selectedImage)}
                              alt={selectedImage.title}
                            />
                          ) : null}
                          <dl className="details-list">
                            <div>
                              <dt>Название</dt>
                              <dd>{selectedImage.title}</dd>
                            </div>
                            <div>
                              <dt>Описание</dt>
                              <dd>{selectedImage.description}</dd>
                            </div>
                            <div>
                              <dt>MIME</dt>
                              <dd>{selectedImage.mime_type}</dd>
                            </div>
                            <div>
                              <dt>Размер файла</dt>
                              <dd>{selectedImage.size}</dd>
                            </div>
                            <div>
                              <dt>Storage key</dt>
                              <dd>{selectedImage.storage_key}</dd>
                            </div>
                            <div>
                              <dt>Создано</dt>
                              <dd>{formatDateTime(selectedImage.create_at)}</dd>
                            </div>
                          </dl>
                        </section>
                      ) : null}
                    </div>
                  </section>
                ) : null}
              </>
            ) : (
              <div className="management-panel">
                <p className="helper-note">После выбора строки здесь появятся быстрые действия для объекта.</p>
              </div>
            )}
          </section>
        </div>

        <aside className="projects-right-column">
          <section className="dashboard-panel profile-calendar-card projects-calendar-panel">
            <div className="projects-calendar-header">
              <div>
                <span className="projects-panel-eyebrow">Календарь</span>
                <h2>{currentResource.label}</h2>
              </div>
              <div className="profile-calendar-toolbar">
                <button
                  type="button"
                  className="ghost-action-btn"
                  onClick={() => setVisibleMonth((prev) => new Date(prev.getFullYear(), prev.getMonth() - 1, 1))}
                >
                  ‹
                </button>
                <strong>{monthFormatter.format(visibleMonth)}</strong>
                <button
                  type="button"
                  className="ghost-action-btn"
                  onClick={() => setVisibleMonth((prev) => new Date(prev.getFullYear(), prev.getMonth() + 1, 1))}
                >
                  ›
                </button>
              </div>
            </div>

            <div className="profile-weekdays">
              {weekDayLabels.map((dayLabel) => (
                <span key={dayLabel}>{dayLabel}</span>
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
                    day.itemCount > 0 ? 'has-availability' : '',
                  ].filter(Boolean).join(' ')}
                  onClick={() => handleCalendarDayClick(day.dateKey, day.date)}
                >
                  <span>{day.label}</span>
                  {day.itemCount > 0 ? <small>{day.itemCount}</small> : null}
                </button>
              ))}
            </div>

            <div className="projects-calendar-summary">
              <p>
                {activeDateFilterKey
                  ? `Фильтр по дате: ${activeDayLabel}. Элементов: ${selectedDayItems.length}.`
                  : 'Нажмите на день, чтобы отфильтровать таблицу по дате создания.'}
              </p>
              {activeDateFilterKey ? (
                <button type="button" className="ghost-action-btn" onClick={() => setActiveDateFilterKey(null)}>
                  Показать все
                </button>
              ) : null}
            </div>
          </section>
        </aside>

        <section className="dashboard-panel projects-table-panel projects-table-full">
          <div className="section-heading projects-table-heading">
            <div>
              <span className="projects-panel-eyebrow">Таблица</span>
              <h2>{currentResource.label}</h2>
            </div>
            <p>
              {loading
                ? 'Загружаем список...'
                : activeDateFilterKey
                  ? `Показаны записи за ${activeDayLabel}`
                  : `Показана страница ${pagination.page} из ${pagination.totalPages}`}
            </p>
          </div>

          <div className="table-shell">
            <table className="user-table">
              <thead>
                <tr>
                  {currentResource.columns.map((column) => (
                    <th key={column.key}>{column.label}</th>
                  ))}
                  <th>Действия</th>
                </tr>
              </thead>
              <tbody>
                {filteredItems.map((item) => {
                  const isSelected = selectedItemId === item.oid;

                  return (
                    <tr key={item.oid} className={isSelected ? 'table-row-selected' : ''}>
                      {currentResource.columns.map((column) => (
                        <td key={column.key} data-label={column.label}>{getColumnValue(item, column)}</td>
                      ))}
                      <td data-label="Действия">
                        <div className="table-actions">
                          <button type="button" className="ghost-action-btn" onClick={() => handleEdit(item)}>
                            Изменить
                          </button>
                          <button type="button" className="ghost-action-btn" onClick={() => handleSelectItem(item)}>
                            {isSelected ? 'Выбрано' : 'Выбрать'}
                          </button>
                          <button
                            type="button"
                            className="ghost-action-btn danger"
                            onClick={() => handleDelete(item.oid)}
                            disabled={deletingId === item.oid}
                          >
                            {deletingId === item.oid ? 'Удаляем...' : 'Удалить'}
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>

            {!loading && filteredItems.length === 0 ? (
              <p className="helper-note projects-empty-state">
                {activeDateFilterKey
                  ? 'На выбранную дату записей нет. Снимите фильтр или выберите другой день.'
                  : 'Список пока пуст. Добавьте первый объект через центральную панель.'}
              </p>
            ) : null}
          </div>

          {!activeDateFilterKey ? (
            <div className="pagination">
              <button
                type="button"
                onClick={() => handlePageChange(pagination.page - 1)}
                disabled={pagination.page <= 1 || loading}
              >
                Назад
              </button>
              <span>Страница {pagination.page} из {pagination.totalPages}</span>
              <button
                type="button"
                onClick={() => handlePageChange(pagination.page + 1)}
                disabled={pagination.page >= pagination.totalPages || loading}
              >
                Вперед
              </button>
            </div>
          ) : null}
        </section>
      </div>
    </section>
  );
};

export default Projects;
