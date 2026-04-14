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

const createInitialResourceForm = () => ({
  title: '',
  description: '',
  type: '',
  size: '',
});

const createInitialWindowForm = () => ({
  startTime: '',
  endTime: '',
});

const createInitialImageForm = () => ({
  file: null,
  title: '',
  description: '',
});

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
    titlePlaceholder: 'Rode NT1',
    descriptionPlaceholder: 'Например: студийный конденсаторный микрофон',
    typePlaceholder: 'Например: condenser',
    columns: tableColumns.equipment,
    buildPayload: (form) => ({
      title: form.title.trim(),
      description: form.description.trim(),
      type: form.type.trim(),
    }),
  },
  cameras: {
    label: 'Камеры',
    one: 'камера',
    create: createCamera,
    list: listCameras,
    update: updateCamera,
    remove: deleteCamera,
    addFreeTime: addCameraFreeTime,
    titlePlaceholder: 'Sony A7S III',
    descriptionPlaceholder: 'Например: полнокадровая беззеркальная камера',
    typePlaceholder: 'Например: mirrorless',
    columns: tableColumns.equipment,
    buildPayload: (form) => ({
      title: form.title.trim(),
      description: form.description.trim(),
      type: form.type.trim(),
    }),
  },
  'camera-tripods': {
    label: 'Штативы для камер',
    one: 'штатив для камеры',
    create: createCameraTripod,
    list: listCameraTripods,
    update: updateCameraTripod,
    remove: deleteCameraTripod,
    addFreeTime: addCameraTripodFreeTime,
    titlePlaceholder: 'Manfrotto 190X',
    descriptionPlaceholder: 'Например: алюминиевый штатив для видео и фото',
    typePlaceholder: 'Например: fluid-head',
    columns: tableColumns.equipment,
    buildPayload: (form) => ({
      title: form.title.trim(),
      description: form.description.trim(),
      type: form.type.trim(),
    }),
  },
  lights: {
    label: 'Свет',
    one: 'источник света',
    create: createLight,
    list: listLights,
    update: updateLight,
    remove: deleteLight,
    addFreeTime: addLightFreeTime,
    titlePlaceholder: 'Aputure 120d',
    descriptionPlaceholder: 'Например: светодиодный источник постоянного света',
    typePlaceholder: 'Например: led',
    columns: tableColumns.equipment,
    buildPayload: (form) => ({
      title: form.title.trim(),
      description: form.description.trim(),
      type: form.type.trim(),
    }),
  },
  'light-tripods': {
    label: 'Стойки для света',
    one: 'стойка для света',
    create: createLightTripod,
    list: listLightTripods,
    update: updateLightTripod,
    remove: deleteLightTripod,
    addFreeTime: addLightTripodFreeTime,
    titlePlaceholder: 'C-Stand Avenger',
    descriptionPlaceholder: 'Например: тяжелая стойка для светового оборудования',
    typePlaceholder: 'Например: c-stand',
    columns: tableColumns.equipment,
    buildPayload: (form) => ({
      title: form.title.trim(),
      description: form.description.trim(),
      type: form.type.trim(),
    }),
  },
  sounds: {
    label: 'Звук',
    one: 'звуковое устройство',
    create: createSound,
    list: listSounds,
    update: updateSound,
    remove: deleteSound,
    addFreeTime: addSoundFreeTime,
    titlePlaceholder: 'Zoom H6',
    descriptionPlaceholder: 'Например: портативный рекордер с XLR-входами',
    typePlaceholder: 'Например: recorder',
    columns: tableColumns.equipment,
    buildPayload: (form) => ({
      title: form.title.trim(),
      description: form.description.trim(),
      type: form.type.trim(),
    }),
  },
  requisites: {
    label: 'Реквизит',
    one: 'элемент реквизита',
    create: createRequisite,
    list: listRequisites,
    update: updateRequisite,
    remove: deleteRequisite,
    addFreeTime: addRequisiteFreeTime,
    titlePlaceholder: 'Vintage lamp',
    descriptionPlaceholder: 'Например: тёплая декоративная лампа для кадра',
    typePlaceholder: 'Например: decor',
    sizePlaceholder: 'Например: m',
    columns: tableColumns.requisites,
    supportsImages: true,
    buildPayload: (form) => ({
      title: form.title.trim(),
      description: form.description.trim(),
      type: form.type.trim(),
      size: form.size.trim(),
    }),
  },
};

const getColumnValue = (item, column) => {
  if (typeof column.render === 'function') {
    return column.render(item);
  }

  return item[column.key] || '-';
};

const getPreviewSource = (image) => {
  const candidate = image?.file || image?.storage_key || '';
  return /^(https?:\/\/|\/)/i.test(candidate) ? candidate : '';
};

const Projects = () => {
  const [activeResource, setActiveResource] = useState('microfons');
  const [form, setForm] = useState(() => createInitialResourceForm());
  const [editingId, setEditingId] = useState(null);
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [deletingId, setDeletingId] = useState(null);
  const [pagination, setPagination] = useState({
    page: 1,
    pageSize: 10,
    totalPages: 1,
    totalCount: 0,
  });

  const [selectedItemId, setSelectedItemId] = useState(null);
  const [freeTimeForm, setFreeTimeForm] = useState(() => createInitialWindowForm());
  const [reserveForm, setReserveForm] = useState(() => createInitialWindowForm());
  const [isSubmittingFreeTime, setIsSubmittingFreeTime] = useState(false);
  const [isSubmittingReservation, setIsSubmittingReservation] = useState(false);

  const [images, setImages] = useState([]);
  const [imageForm, setImageForm] = useState(() => createInitialImageForm());
  const [imageInputKey, setImageInputKey] = useState(0);
  const [isImagesLoading, setIsImagesLoading] = useState(false);
  const [isUploadingImage, setIsUploadingImage] = useState(false);
  const [selectedImage, setSelectedImage] = useState(null);
  const [loadingImageId, setLoadingImageId] = useState(null);
  const [removingImageId, setRemovingImageId] = useState(null);

  const currentResource = useMemo(() => resourceMeta[activeResource], [activeResource]);
  const selectedItem = useMemo(
    () => items.find((item) => item.oid === selectedItemId) || null,
    [items, selectedItemId],
  );

  const resetForm = () => {
    setForm(createInitialResourceForm());
    setEditingId(null);
  };

  const resetManagementState = () => {
    setSelectedItemId(null);
    setFreeTimeForm(createInitialWindowForm());
    setReserveForm(createInitialWindowForm());
    setImages([]);
    setImageForm(createInitialImageForm());
    setImageInputKey((prev) => prev + 1);
    setSelectedImage(null);
  };

  const fetchItems = useCallback(async () => {
    try {
      setLoading(true);
      const data = await currentResource.list({
        page: pagination.page,
        pageSize: pagination.pageSize,
        sortBy: 'create_at',
        sortDir: 'desc',
      });

      setItems(data.items || []);
      setPagination((prev) => ({
        ...prev,
        totalPages: data.pages || 1,
        totalCount: data.total_count || 0,
      }));
    } catch (error) {
      toast.error(error.message || `Не удалось загрузить раздел «${currentResource.label}»`);
    } finally {
      setLoading(false);
    }
  }, [currentResource, pagination.page, pagination.pageSize]);

  const loadRequisiteImages = useCallback(async (requisiteId) => {
    try {
      setIsImagesLoading(true);
      const data = await listRequisiteImages(requisiteId);
      setImages(data.items || []);
    } catch (error) {
      toast.error(error.message || 'Не удалось загрузить изображения реквизита');
    } finally {
      setIsImagesLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchItems();
  }, [fetchItems]);

  useEffect(() => {
    if (selectedItemId && !items.some((item) => item.oid === selectedItemId)) {
      resetManagementState();
    }
  }, [items, selectedItemId]);

  useEffect(() => {
    if (activeResource !== 'requisites' || !selectedItem) {
      setImages([]);
      setSelectedImage(null);
      return;
    }

    loadRequisiteImages(selectedItem.oid);
  }, [activeResource, loadRequisiteImages, selectedItem]);

  const switchResource = (nextResource) => {
    if (nextResource === activeResource) {
      return;
    }

    setActiveResource(nextResource);
    resetForm();
    resetManagementState();
    setPagination((prev) => ({
      ...prev,
      page: 1,
      totalPages: 1,
      totalCount: 0,
    }));
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

    setImageForm((prev) => ({
      ...prev,
      [name]: name === 'file' ? files?.[0] || null : value,
    }));
  };

  const getWindowPayload = (windowForm) => {
    const startTime = toIsoDateTime(windowForm.startTime);
    const endTime = toIsoDateTime(windowForm.endTime);

    if (!startTime || !endTime) {
      toast.error('Укажите корректные дату и время');
      return null;
    }

    if (new Date(startTime) >= new Date(endTime)) {
      toast.error('Время окончания должно быть позже времени начала');
      return null;
    }

    return {
      start_time: startTime,
      end_time: endTime,
    };
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setSubmitting(true);

    try {
      const payload = currentResource.buildPayload(form);

      if (editingId) {
        await currentResource.update(editingId, payload);
        toast.success(`${currentResource.one} обновлен(а)`);
      } else {
        await currentResource.create(payload);
        toast.success(`${currentResource.one} добавлен(а)`);
      }

      resetForm();
      await fetchItems();
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) {
        toast.info('Запись не найдена. Список обновлен.');
        resetForm();
        await fetchItems();
        return;
      }

      toast.error(error.message || 'Не удалось сохранить запись');
    } finally {
      setSubmitting(false);
    }
  };

  const handleEdit = (item) => {
    setEditingId(item.oid);
    setSelectedItemId(item.oid);
    setForm({
      title: item.title || '',
      description: item.description || '',
      type: item.type || '',
      size: item.size || '',
    });
  };

  const handleDelete = async (itemId) => {
    const confirmed = window.confirm('Удалить запись?');

    if (!confirmed) {
      return;
    }

    try {
      setDeletingId(itemId);
      await currentResource.remove(itemId);
      toast.success('Запись удалена');

      if (selectedItemId === itemId) {
        resetManagementState();
      }

      if (editingId === itemId) {
        resetForm();
      }

      if (items.length === 1 && pagination.page > 1) {
        setPagination((prev) => ({ ...prev, page: prev.page - 1 }));
      } else {
        await fetchItems();
      }
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) {
        setItems((prev) => prev.filter((item) => item.oid !== itemId));

        if (editingId === itemId) {
          resetForm();
        }

        if (selectedItemId === itemId) {
          resetManagementState();
        }

        toast.info('Запись уже удалена на сервере');
        return;
      }

      toast.error(error.message || 'Не удалось удалить запись');
    } finally {
      setDeletingId(null);
    }
  };

  const handleSelectItem = (item) => {
    setSelectedItemId(item.oid);
    setFreeTimeForm(createInitialWindowForm());
    setReserveForm(createInitialWindowForm());
    setSelectedImage(null);
  };

  const handleAddFreeTime = async (event) => {
    event.preventDefault();

    if (!selectedItem) {
      toast.info('Сначала выберите запись из списка');
      return;
    }

    const payload = getWindowPayload(freeTimeForm);

    if (!payload) {
      return;
    }

    try {
      setIsSubmittingFreeTime(true);
      await currentResource.addFreeTime(selectedItem.oid, payload);
      setFreeTimeForm(createInitialWindowForm());
      toast.success('Окно доступности добавлено');
    } catch (error) {
      toast.error(error.message || 'Не удалось добавить окно доступности');
    } finally {
      setIsSubmittingFreeTime(false);
    }
  };

  const handleReserve = async (event) => {
    event.preventDefault();

    if (!selectedItem) {
      toast.info('Сначала выберите запись из списка');
      return;
    }

    const payload = getWindowPayload(reserveForm);

    if (!payload) {
      return;
    }

    try {
      setIsSubmittingReservation(true);
      await reserveAvailability({
        owner_id: selectedItem.user_id,
        obj_id: selectedItem.oid,
        ...payload,
      });
      setReserveForm(createInitialWindowForm());
      toast.success('Бронирование отправлено');
    } catch (error) {
      toast.error(error.message || 'Не удалось забронировать окно');
    } finally {
      setIsSubmittingReservation(false);
    }
  };

  const handleImageSubmit = async (event) => {
    event.preventDefault();

    if (!selectedItem) {
      toast.info('Сначала выберите реквизит');
      return;
    }

    if (!imageForm.file) {
      toast.error('Выберите файл изображения');
      return;
    }

    try {
      setIsUploadingImage(true);
      await addRequisiteImage(selectedItem.oid, {
        file: imageForm.file,
        title: imageForm.title.trim(),
        description: imageForm.description.trim(),
      });
      setImageForm(createInitialImageForm());
      setImageInputKey((prev) => prev + 1);
      await loadRequisiteImages(selectedItem.oid);
      toast.success('Изображение загружено');
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

    try {
      setLoadingImageId(imageId);
      const data = await getRequisiteImage(selectedItem.oid, imageId);
      setSelectedImage(data);
    } catch (error) {
      toast.error(error.message || 'Не удалось загрузить метаданные изображения');
    } finally {
      setLoadingImageId(null);
    }
  };

  const handleRemoveImage = async (imageId) => {
    if (!selectedItem) {
      return;
    }

    const confirmed = window.confirm('Удалить изображение?');

    if (!confirmed) {
      return;
    }

    try {
      setRemovingImageId(imageId);
      await removeRequisiteImage(selectedItem.oid, imageId);
      setImages((prev) => prev.filter((image) => image.oid !== imageId));

      if (selectedImage?.oid === imageId) {
        setSelectedImage(null);
      }

      toast.success('Изображение удалено');
    } catch (error) {
      toast.error(error.message || 'Не удалось удалить изображение');
    } finally {
      setRemovingImageId(null);
    }
  };

  const handlePageChange = (newPage) => {
    if (newPage >= 1 && newPage <= pagination.totalPages) {
      setPagination((prev) => ({ ...prev, page: newPage }));
    }
  };

  const submitButtonLabel = editingId ? 'Обновить' : 'Добавить';
  const previewSource = getPreviewSource(selectedImage);

  return (
    <section className="projects-wrapper">
      <div className="projects-page">
        <h1>Рабочая зона</h1>
        <p>
          Здесь подключены все CRUD-ручки по оборудованию и реквизиту, а также добавление free-time,
          резервирование и изображения реквизита.
        </p>

        <div className="equipment-switcher" role="tablist" aria-label="Тип оборудования">
          {Object.entries(resourceMeta).map(([resourceKey, meta]) => (
            <button
              key={resourceKey}
              type="button"
              className={`switcher-btn ${activeResource === resourceKey ? 'active' : ''}`}
              onClick={() => switchResource(resourceKey)}
            >
              {meta.label}
            </button>
          ))}
        </div>

        <p>Текущий раздел: {currentResource.label}</p>

        <form className="stacked-form resource-form" onSubmit={handleSubmit}>
          <div className="grid-two-columns">
            <label className="field-block" htmlFor="equipment-title">
              <span>Название</span>
              <input
                id="equipment-title"
                name="title"
                value={form.title}
                onChange={handleChange}
                className="profile-input"
                placeholder={currentResource.titlePlaceholder}
                required
              />
            </label>

            <label className="field-block" htmlFor="equipment-type">
              <span>Тип</span>
              <input
                id="equipment-type"
                name="type"
                value={form.type}
                onChange={handleChange}
                className="profile-input"
                placeholder={currentResource.typePlaceholder}
                required
              />
            </label>
          </div>

          <label className="field-block" htmlFor="equipment-description">
            <span>Описание</span>
            <textarea
              id="equipment-description"
              name="description"
              value={form.description}
              onChange={handleChange}
              className="profile-textarea"
              placeholder={currentResource.descriptionPlaceholder}
              rows={3}
              required
            />
          </label>

          {currentResource.sizePlaceholder ? (
            <label className="field-block" htmlFor="equipment-size">
              <span>Размер</span>
              <input
                id="equipment-size"
                name="size"
                value={form.size}
                onChange={handleChange}
                className="profile-input"
                placeholder={currentResource.sizePlaceholder}
                required
              />
            </label>
          ) : null}

          <div className="inline-actions">
            <button type="submit" className="profile-save-btn compact" disabled={submitting}>
              {submitting ? 'Сохранение...' : submitButtonLabel}
            </button>
            {editingId ? (
              <button type="button" className="secondary-btn" onClick={resetForm}>
                Отмена
              </button>
            ) : null}
          </div>
        </form>

        {loading ? (
          <p>Загрузка...</p>
        ) : (
          <>
            <p className="microfon-count">Всего записей: {pagination.totalCount}</p>

            <div className="table-shell">
              <table className="user-table microfon-table">
                <thead>
                  <tr>
                    {currentResource.columns.map((column) => (
                      <th key={column.key}>{column.label}</th>
                    ))}
                    <th>Действия</th>
                  </tr>
                </thead>
                <tbody>
                  {items.length === 0 ? (
                    <tr>
                      <td colSpan={currentResource.columns.length + 1}>Список пока пуст</td>
                    </tr>
                  ) : (
                    items.map((item) => (
                      <tr
                        key={item.oid}
                        className={selectedItemId === item.oid ? 'table-row-selected' : ''}
                      >
                        {currentResource.columns.map((column) => (
                          <td key={column.key}>{getColumnValue(item, column)}</td>
                        ))}
                        <td>
                          <div className="table-actions">
                            <button
                              type="button"
                              className="ghost-action-btn"
                              onClick={() => handleEdit(item)}
                            >
                              Редактировать
                            </button>
                            <button
                              type="button"
                              className="ghost-action-btn"
                              onClick={() => handleSelectItem(item)}
                            >
                              Управление
                            </button>
                            <button
                              type="button"
                              className="ghost-action-btn danger"
                              onClick={() => handleDelete(item.oid)}
                              disabled={deletingId === item.oid}
                            >
                              {deletingId === item.oid ? 'Удаление...' : 'Удалить'}
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            <div className="pagination">
              <button
                type="button"
                onClick={() => handlePageChange(pagination.page - 1)}
                disabled={pagination.page === 1}
              >
                Назад
              </button>
              <span>
                Страница {pagination.page} из {pagination.totalPages}
              </span>
              <button
                type="button"
                onClick={() => handlePageChange(pagination.page + 1)}
                disabled={pagination.page === pagination.totalPages}
              >
                Вперед
              </button>
            </div>
          </>
        )}

        <section className="profile-card management-card">
          <div className="section-heading">
            <div>
              <h2>Управление доступностью</h2>
              <p>
                Выберите запись из таблицы, чтобы добавить свободное окно через `/free-times` и
                отправить бронирование через `/availability/reserve`.
              </p>
            </div>
          </div>

          {selectedItem ? (
            <>
              <div className="selected-entity-summary">
                <div>
                  <strong>{selectedItem.title}</strong>
                  <p>
                    {selectedItem.description || 'Без описания'} · тип: {selectedItem.type || '-'}
                  </p>
                </div>
                <div className="entity-meta-list">
                  <span>owner_id: {selectedItem.user_id}</span>
                  <span>obj_id: {selectedItem.oid}</span>
                </div>
              </div>

              <p className="helper-note">
                В текущей спецификации для окон техники и реквизита есть только `POST`, поэтому
                интерфейс поддерживает добавление и бронирование, но не выводит историю этих окон.
              </p>

              <div className="management-grid">
                <form className="stacked-form management-panel" onSubmit={handleAddFreeTime}>
                  <h3>Добавить свободное окно</h3>

                  <label className="field-block" htmlFor="free-time-start">
                    <span>Начало</span>
                    <input
                      id="free-time-start"
                      name="startTime"
                      type="datetime-local"
                      value={freeTimeForm.startTime}
                      onChange={handleWindowChange(setFreeTimeForm)}
                      className="profile-input"
                      required
                    />
                  </label>

                  <label className="field-block" htmlFor="free-time-end">
                    <span>Окончание</span>
                    <input
                      id="free-time-end"
                      name="endTime"
                      type="datetime-local"
                      value={freeTimeForm.endTime}
                      onChange={handleWindowChange(setFreeTimeForm)}
                      className="profile-input"
                      required
                    />
                  </label>

                  <button
                    type="submit"
                    className="profile-save-btn compact"
                    disabled={isSubmittingFreeTime}
                  >
                    {isSubmittingFreeTime ? 'Отправка...' : 'Добавить окно'}
                  </button>
                </form>

                <form className="stacked-form management-panel" onSubmit={handleReserve}>
                  <h3>Забронировать окно</h3>

                  <label className="field-block" htmlFor="reserve-start">
                    <span>Начало брони</span>
                    <input
                      id="reserve-start"
                      name="startTime"
                      type="datetime-local"
                      value={reserveForm.startTime}
                      onChange={handleWindowChange(setReserveForm)}
                      className="profile-input"
                      required
                    />
                  </label>

                  <label className="field-block" htmlFor="reserve-end">
                    <span>Окончание брони</span>
                    <input
                      id="reserve-end"
                      name="endTime"
                      type="datetime-local"
                      value={reserveForm.endTime}
                      onChange={handleWindowChange(setReserveForm)}
                      className="profile-input"
                      required
                    />
                  </label>

                  <button
                    type="submit"
                    className="profile-save-btn compact"
                    disabled={isSubmittingReservation}
                  >
                    {isSubmittingReservation ? 'Отправка...' : 'Забронировать'}
                  </button>
                </form>
              </div>

              {currentResource.supportsImages ? (
                <section className="requisite-media-section">
                  <div className="section-heading">
                    <div>
                      <h3>Изображения реквизита</h3>
                      <p>
                        Здесь подключены `POST`, `GET list`, `GET item` и `DELETE` для
                        `/requisites/:requisiteId/images`.
                      </p>
                    </div>
                  </div>

                  <form className="stacked-form management-panel" onSubmit={handleImageSubmit}>
                    <div className="grid-two-columns">
                      <label className="field-block" htmlFor="image-title">
                        <span>Название изображения</span>
                        <input
                          id="image-title"
                          name="title"
                          value={imageForm.title}
                          onChange={handleImageFieldChange}
                          className="profile-input"
                          placeholder="Например: front view"
                          required
                        />
                      </label>

                      <label className="field-block" htmlFor="image-file">
                        <span>Файл</span>
                        <input
                          key={imageInputKey}
                          id="image-file"
                          name="file"
                          type="file"
                          accept="image/*"
                          onChange={handleImageFieldChange}
                          className="profile-input"
                          required
                        />
                      </label>
                    </div>

                    <label className="field-block" htmlFor="image-description">
                      <span>Описание</span>
                      <textarea
                        id="image-description"
                        name="description"
                        value={imageForm.description}
                        onChange={handleImageFieldChange}
                        className="profile-textarea"
                        rows={3}
                        placeholder="Короткое описание изображения"
                        required
                      />
                    </label>

                    <button
                      type="submit"
                      className="profile-save-btn compact"
                      disabled={isUploadingImage}
                    >
                      {isUploadingImage ? 'Загрузка...' : 'Загрузить изображение'}
                    </button>
                  </form>

                  {isImagesLoading ? (
                    <p>Загрузка изображений...</p>
                  ) : images.length === 0 ? (
                    <p>У этого реквизита пока нет изображений.</p>
                  ) : (
                    <div className="media-grid">
                      {images.map((image) => (
                        <article key={image.oid} className="media-card">
                          <h4>{image.title}</h4>
                          <p>{image.description}</p>
                          <span>Размер: {image.size ?? '-'} байт</span>
                          <span>Создано: {formatDateTime(image.create_at)}</span>
                          <div className="table-actions">
                            <button
                              type="button"
                              className="ghost-action-btn"
                              onClick={() => handleImageDetails(image.oid)}
                              disabled={loadingImageId === image.oid}
                            >
                              {loadingImageId === image.oid ? 'Загрузка...' : 'Подробнее'}
                            </button>
                            <button
                              type="button"
                              className="ghost-action-btn danger"
                              onClick={() => handleRemoveImage(image.oid)}
                              disabled={removingImageId === image.oid}
                            >
                              {removingImageId === image.oid ? 'Удаление...' : 'Удалить'}
                            </button>
                          </div>
                        </article>
                      ))}
                    </div>
                  )}

                  {selectedImage ? (
                    <div className="image-details-card">
                      <div className="section-heading">
                        <div>
                          <h3>Метаданные изображения</h3>
                          <p>Загружено через `GET /requisites/:id/images/:imageId`.</p>
                        </div>
                      </div>

                      {previewSource ? (
                        <img
                          src={previewSource}
                          alt={selectedImage.title}
                          className="requisite-image-preview"
                        />
                      ) : null}

                      <dl className="details-list">
                        <div>
                          <dt>ID</dt>
                          <dd>{selectedImage.oid}</dd>
                        </div>
                        <div>
                          <dt>Файл</dt>
                          <dd>{selectedImage.file}</dd>
                        </div>
                        <div>
                          <dt>Bucket</dt>
                          <dd>{selectedImage.bucket}</dd>
                        </div>
                        <div>
                          <dt>Storage key</dt>
                          <dd>{selectedImage.storage_key}</dd>
                        </div>
                        <div>
                          <dt>MIME type</dt>
                          <dd>{selectedImage.mime_type}</dd>
                        </div>
                        <div>
                          <dt>Размер</dt>
                          <dd>{selectedImage.size}</dd>
                        </div>
                        <div>
                          <dt>Создано</dt>
                          <dd>{formatDateTime(selectedImage.create_at)}</dd>
                        </div>
                      </dl>
                    </div>
                  ) : null}
                </section>
              ) : null}
            </>
          ) : (
            <p className="helper-note">
              Выберите запись из таблицы, чтобы управлять её доступностью. Для реквизита здесь же
              откроется блок изображений.
            </p>
          )}
        </section>
      </div>
    </section>
  );
};

export default Projects;
