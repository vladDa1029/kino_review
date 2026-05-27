import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { toast } from 'react-toastify';
import {
  checkAdminUserExists,
  createAdminCamera,
  createAdminCameraTripod,
  createAdminLight,
  createAdminLightTripod,
  createAdminMicrofon,
  createAdminRequisite,
  createAdminSound,
  createAdminSpareTime,
  createAdminUserDescription,
  deleteAdminCamera,
  deleteAdminCameraTripod,
  deleteAdminLight,
  deleteAdminLightTripod,
  deleteAdminMicrofon,
  deleteAdminRequisite,
  deleteAdminSound,
  deleteAdminSpareTime,
  getAdminUser,
  getAdminUserDescription,
  listAdminCameras,
  listAdminCameraTripods,
  listAdminLights,
  listAdminLightTripods,
  listAdminMicrofons,
  listAdminRequisites,
  listAdminSounds,
  listAdminSpareTimes,
  updateAdminCamera,
  updateAdminCameraTripod,
  updateAdminLight,
  updateAdminLightTripod,
  updateAdminMicrofon,
  updateAdminRequisite,
  updateAdminSound,
  updateAdminSpareTime,
  updateAdminUserDescription,
} from '../services/api';

const createDescriptionForm = () => ({
  username: '',
  phone: '',
});

const createSpareTimeForm = () => ({
  start_time: '',
  end_time: '',
});

const createEquipmentForm = (isRequisite = false) => ({
  title: '',
  description: '',
  type: '',
  ...(isRequisite ? { size: '' } : {}),
});

const resourceConfigs = {
  microfons: {
    label: 'Микрофоны',
    list: listAdminMicrofons,
    create: createAdminMicrofon,
    update: updateAdminMicrofon,
    remove: deleteAdminMicrofon,
    createForm: () => createEquipmentForm(false),
  },
  cameras: {
    label: 'Камеры',
    list: listAdminCameras,
    create: createAdminCamera,
    update: updateAdminCamera,
    remove: deleteAdminCamera,
    createForm: () => createEquipmentForm(false),
  },
  'camera-tripods': {
    label: 'Штативы для камер',
    list: listAdminCameraTripods,
    create: createAdminCameraTripod,
    update: updateAdminCameraTripod,
    remove: deleteAdminCameraTripod,
    createForm: () => createEquipmentForm(false),
  },
  lights: {
    label: 'Свет',
    list: listAdminLights,
    create: createAdminLight,
    update: updateAdminLight,
    remove: deleteAdminLight,
    createForm: () => createEquipmentForm(false),
  },
  'light-tripods': {
    label: 'Стойки для света',
    list: listAdminLightTripods,
    create: createAdminLightTripod,
    update: updateAdminLightTripod,
    remove: deleteAdminLightTripod,
    createForm: () => createEquipmentForm(false),
  },
  sounds: {
    label: 'Звук',
    list: listAdminSounds,
    create: createAdminSound,
    update: updateAdminSound,
    remove: deleteAdminSound,
    createForm: () => createEquipmentForm(false),
  },
  requisites: {
    label: 'Реквизит',
    list: listAdminRequisites,
    create: createAdminRequisite,
    update: updateAdminRequisite,
    remove: deleteAdminRequisite,
    createForm: () => createEquipmentForm(true),
  },
};

const AdminUserDetailsPage = () => {
  const { userId } = useParams();
  const [authUser, setAuthUser] = useState(null);
  const [userExists, setUserExists] = useState(null);
  const [description, setDescription] = useState(null);
  const [descriptionForm, setDescriptionForm] = useState(createDescriptionForm);
  const [descriptionSaving, setDescriptionSaving] = useState(false);
  const [spareTimes, setSpareTimes] = useState([]);
  const [spareTimeForm, setSpareTimeForm] = useState(createSpareTimeForm);
  const [editingSpareTimeId, setEditingSpareTimeId] = useState(null);
  const [spareTimeSaving, setSpareTimeSaving] = useState(false);
  const [selectedResourceKey, setSelectedResourceKey] = useState('microfons');
  const [resourceItems, setResourceItems] = useState([]);
  const [resourceForm, setResourceForm] = useState(createEquipmentForm(false));
  const [editingResourceId, setEditingResourceId] = useState(null);
  const [resourceLoading, setResourceLoading] = useState(true);
  const [resourceSaving, setResourceSaving] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const activeResourceConfig = useMemo(() => resourceConfigs[selectedResourceKey], [selectedResourceKey]);

  const loadResourceItems = useCallback(async () => {
    try {
      setResourceLoading(true);
      const response = await activeResourceConfig.list(userId, { pageSize: 50 });
      setResourceItems(response.items || []);
    } catch (err) {
      toast.error(err.message || `Не удалось загрузить раздел "${activeResourceConfig.label}"`);
    } finally {
      setResourceLoading(false);
    }
  }, [activeResourceConfig, userId]);

  useEffect(() => {
    let cancelled = false;

    const run = async () => {
      try {
        setLoading(true);
        setError('');

        const [authResponse, existsResponse, descriptionResponse, spareTimesResponse] = await Promise.all([
          getAdminUser(userId),
          checkAdminUserExists(userId),
          getAdminUserDescription(userId).catch((err) => (err.status === 404 ? null : Promise.reject(err))),
          listAdminSpareTimes(userId),
        ]);

        if (cancelled) {
          return;
        }

        setAuthUser(authResponse);
        setUserExists(existsResponse);
        setDescription(descriptionResponse);
        setDescriptionForm(
          descriptionResponse
            ? {
                username: descriptionResponse.username || '',
                phone: descriptionResponse.phone || '',
              }
            : createDescriptionForm(),
        );
        setSpareTimes(spareTimesResponse.items || []);
      } catch (err) {
        if (!cancelled) {
          setError(err.message || 'Не удалось загрузить пользователя');
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    run();
    return () => {
      cancelled = true;
    };
  }, [userId]);

  useEffect(() => {
    setEditingResourceId(null);
    setResourceForm(activeResourceConfig.createForm());
    loadResourceItems();
  }, [activeResourceConfig, loadResourceItems]);

  const handleDescriptionSubmit = async (event) => {
    event.preventDefault();
    setDescriptionSaving(true);

    try {
      if (description?.oid) {
        await updateAdminUserDescription(userId, description.oid, descriptionForm);
      } else {
        await createAdminUserDescription(userId, descriptionForm);
      }

      const freshDescription = await getAdminUserDescription(userId);
      setDescription(freshDescription);
      setDescriptionForm({
        username: freshDescription.username || '',
        phone: freshDescription.phone || '',
      });
      toast.success('Описание пользователя сохранено');
    } catch (err) {
      toast.error(err.message || 'Не удалось сохранить описание');
    } finally {
      setDescriptionSaving(false);
    }
  };

  const handleSpareTimeSubmit = async (event) => {
    event.preventDefault();
    setSpareTimeSaving(true);

    try {
      if (editingSpareTimeId) {
        await updateAdminSpareTime(userId, editingSpareTimeId, spareTimeForm);
      } else {
        await createAdminSpareTime(userId, spareTimeForm);
      }

      const refreshed = await listAdminSpareTimes(userId);
      setSpareTimes(refreshed.items || []);
      setSpareTimeForm(createSpareTimeForm());
      setEditingSpareTimeId(null);
      toast.success('Окно доступности сохранено');
    } catch (err) {
      toast.error(err.message || 'Не удалось сохранить окно доступности');
    } finally {
      setSpareTimeSaving(false);
    }
  };

  const handleSpareTimeDelete = async (spareTimeId) => {
    if (!window.confirm('Удалить окно доступности?')) {
      return;
    }

    try {
      await deleteAdminSpareTime(userId, spareTimeId);
      const refreshed = await listAdminSpareTimes(userId);
      setSpareTimes(refreshed.items || []);
      if (editingSpareTimeId === spareTimeId) {
        setEditingSpareTimeId(null);
        setSpareTimeForm(createSpareTimeForm());
      }
      toast.success('Окно доступности удалено');
    } catch (err) {
      toast.error(err.message || 'Не удалось удалить окно доступности');
    }
  };

  const handleResourceSubmit = async (event) => {
    event.preventDefault();
    setResourceSaving(true);

    try {
      if (editingResourceId) {
        await activeResourceConfig.update(userId, editingResourceId, resourceForm);
      } else {
        await activeResourceConfig.create(userId, resourceForm);
      }

      await loadResourceItems();
      setEditingResourceId(null);
      setResourceForm(activeResourceConfig.createForm());
      toast.success(`${activeResourceConfig.label} сохранены`);
    } catch (err) {
      toast.error(err.message || `Не удалось сохранить раздел "${activeResourceConfig.label}"`);
    } finally {
      setResourceSaving(false);
    }
  };

  const handleResourceDelete = async (resourceId) => {
    if (!window.confirm(`Удалить запись из раздела "${activeResourceConfig.label}"?`)) {
      return;
    }

    try {
      await activeResourceConfig.remove(userId, resourceId);
      await loadResourceItems();
      if (editingResourceId === resourceId) {
        setEditingResourceId(null);
        setResourceForm(activeResourceConfig.createForm());
      }
      toast.success('Запись удалена');
    } catch (err) {
      toast.error(err.message || 'Не удалось удалить запись');
    }
  };

  if (loading) {
    return <div className="admin-screen admin-content-stack">Загрузка...</div>;
  }

  return (
    <div className="admin-screen admin-content-stack">
      <section className="management-card admin-panel-card">
        <div className="admin-section-header">
          <div>
            <span className="projects-panel-eyebrow">Администрирование пользователя</span>
            <h2>{authUser?.email || userId}</h2>
            <p>Карточка администратора для профиля, доступности и пользовательского инвентаря.</p>
          </div>
          <Link className="secondary-btn admin-inline-link" to="/admin/users">
            Ко всем пользователям
          </Link>
        </div>
      </section>

      {error ? <div className="management-card admin-panel-card error-text">{error}</div> : null}

      <section className="management-card admin-summary-grid">
        <div className="admin-summary-card">
          <span>OID</span>
          <strong>{authUser?.oid || userId}</strong>
        </div>
        <div className="admin-summary-card">
          <span>Активен</span>
          <strong>{authUser?.is_active ? 'Да' : 'Нет'}</strong>
        </div>
        <div className="admin-summary-card">
          <span>Суперпользователь</span>
          <strong>{authUser?.is_superuser ? 'Да' : 'Нет'}</strong>
        </div>
        <div className="admin-summary-card">
          <span>Есть в пользовательском сервисе</span>
          <strong>{userExists ? 'Да' : 'Нет данных'}</strong>
        </div>
      </section>

      <div className="admin-detail-grid">
        <section className="management-card">
          <div className="section-heading">
            <div>
              <h3>Описание пользователя</h3>
              <p>Поля `username` и `phone` из admin user API.</p>
            </div>
          </div>

          <form className="stacked-form" onSubmit={handleDescriptionSubmit}>
            <label className="field-block">
              <span>ФИО</span>
              <input
                value={descriptionForm.username}
                onChange={(event) =>
                  setDescriptionForm((prev) => ({ ...prev, username: event.target.value }))
                }
                required
              />
            </label>
            <label className="field-block">
              <span>Телефон</span>
              <input
                value={descriptionForm.phone}
                onChange={(event) =>
                  setDescriptionForm((prev) => ({ ...prev, phone: event.target.value }))
                }
                required
                minLength={10}
              />
            </label>

            <div className="inline-actions">
              <button type="submit" className="profile-save-btn compact" disabled={descriptionSaving}>
                {descriptionSaving ? 'Сохраняем...' : 'Сохранить описание'}
              </button>
            </div>
          </form>
        </section>

        <section className="management-card">
          <div className="section-heading">
            <div>
              <h3>Доступность пользователя</h3>
              <p>Управление окнами `spare-times` для выбранного пользователя.</p>
            </div>
          </div>

          <form className="stacked-form" onSubmit={handleSpareTimeSubmit}>
            <div className="grid-two-columns">
              <label className="field-block">
                <span>Начало</span>
                <input
                  type="datetime-local"
                  value={spareTimeForm.start_time}
                  onChange={(event) =>
                    setSpareTimeForm((prev) => ({ ...prev, start_time: event.target.value }))
                  }
                  required
                />
              </label>
              <label className="field-block">
                <span>Конец</span>
                <input
                  type="datetime-local"
                  value={spareTimeForm.end_time}
                  onChange={(event) =>
                    setSpareTimeForm((prev) => ({ ...prev, end_time: event.target.value }))
                  }
                  required
                />
              </label>
            </div>

            <div className="inline-actions">
              <button type="submit" className="profile-save-btn compact" disabled={spareTimeSaving}>
                {spareTimeSaving ? 'Сохраняем...' : editingSpareTimeId ? 'Обновить окно' : 'Добавить окно'}
              </button>
              <button
                type="button"
                className="secondary-btn"
                onClick={() => {
                  setEditingSpareTimeId(null);
                  setSpareTimeForm(createSpareTimeForm());
                }}
              >
                Сбросить
              </button>
            </div>
          </form>

          <div className="admin-entity-list">
            {spareTimes.map((item) => (
              <article key={item.oid} className="admin-entity-card">
                <div>
                  <strong>{new Date(item.start_time).toLocaleString()}</strong>
                  <p>{new Date(item.end_time).toLocaleString()}</p>
                  <small>Статус: {item.status}</small>
                </div>
                <div className="table-actions">
                  <button
                    type="button"
                    className="ghost-action-btn"
                    onClick={() => {
                      setEditingSpareTimeId(item.oid);
                      setSpareTimeForm({
                        start_time: item.start_time.slice(0, 16),
                        end_time: item.end_time.slice(0, 16),
                      });
                    }}
                  >
                    Изменить
                  </button>
                  <button
                    type="button"
                    className="ghost-action-btn danger"
                    onClick={() => handleSpareTimeDelete(item.oid)}
                  >
                    Удалить
                  </button>
                </div>
              </article>
            ))}
          </div>
        </section>
      </div>

      <section className="management-card">
        <div className="section-heading">
          <div>
            <h3>Инвентарь пользователя</h3>
            <p>CRUD по административным user endpoints для оборудования и реквизита.</p>
          </div>
        </div>

        <div className="projects-sidebar-nav admin-resource-tabs">
          {Object.entries(resourceConfigs).map(([key, config]) => (
            <button
              key={key}
              type="button"
              className={`projects-sidebar-button ${selectedResourceKey === key ? 'is-active' : ''}`}
              onClick={() => setSelectedResourceKey(key)}
            >
              <span>{config.label}</span>
            </button>
          ))}
        </div>

        <div className="admin-detail-grid admin-detail-grid-bottom">
          <form className="stacked-form management-card admin-nested-card" onSubmit={handleResourceSubmit}>
            <div className="section-heading">
              <div>
                <h3>{editingResourceId ? `Редактирование: ${activeResourceConfig.label}` : activeResourceConfig.label}</h3>
                <p>Форма создания и обновления записей.</p>
              </div>
            </div>

            <label className="field-block">
              <span>Название</span>
              <input
                value={resourceForm.title}
                onChange={(event) => setResourceForm((prev) => ({ ...prev, title: event.target.value }))}
                required
              />
            </label>

            <label className="field-block">
              <span>Описание</span>
              <textarea
                value={resourceForm.description}
                onChange={(event) =>
                  setResourceForm((prev) => ({ ...prev, description: event.target.value }))
                }
                rows={4}
                required
              />
            </label>

            <div className="grid-two-columns">
              <label className="field-block">
                <span>Тип</span>
                <input
                  value={resourceForm.type}
                  onChange={(event) => setResourceForm((prev) => ({ ...prev, type: event.target.value }))}
                  required
                />
              </label>

              {'size' in resourceForm ? (
                <label className="field-block">
                  <span>Размер</span>
                  <input
                    value={resourceForm.size}
                    onChange={(event) => setResourceForm((prev) => ({ ...prev, size: event.target.value }))}
                    required
                  />
                </label>
              ) : (
                <div />
              )}
            </div>

            <div className="inline-actions">
              <button type="submit" className="profile-save-btn compact" disabled={resourceSaving}>
                {resourceSaving ? 'Сохраняем...' : editingResourceId ? 'Сохранить запись' : 'Добавить запись'}
              </button>
              <button
                type="button"
                className="secondary-btn"
                onClick={() => {
                  setEditingResourceId(null);
                  setResourceForm(activeResourceConfig.createForm());
                }}
              >
                Сбросить
              </button>
            </div>
          </form>

          <div className="management-card admin-nested-card">
            <div className="section-heading">
              <div>
                <h3>Список: {activeResourceConfig.label}</h3>
                <p>{resourceLoading ? 'Загрузка...' : `Найдено записей: ${resourceItems.length}`}</p>
              </div>
            </div>

            <div className="admin-entity-list">
              {resourceItems.map((item) => (
                <article key={item.oid} className="admin-entity-card">
                  <div>
                    <strong>{item.title}</strong>
                    <p>{item.description}</p>
                    <small>
                      Тип: {item.type}
                      {'size' in item ? ` | Размер: ${item.size}` : ''}
                    </small>
                  </div>
                  <div className="table-actions">
                    <button
                      type="button"
                      className="ghost-action-btn"
                      onClick={() => {
                        setEditingResourceId(item.oid);
                        setResourceForm(
                          'size' in item
                            ? {
                                title: item.title || '',
                                description: item.description || '',
                                type: item.type || '',
                                size: item.size || '',
                              }
                            : {
                                title: item.title || '',
                                description: item.description || '',
                                type: item.type || '',
                              },
                        );
                      }}
                    >
                      Изменить
                    </button>
                    <button
                      type="button"
                      className="ghost-action-btn danger"
                      onClick={() => handleResourceDelete(item.oid)}
                    >
                      Удалить
                    </button>
                  </div>
                </article>
              ))}
            </div>
          </div>
        </div>
      </section>
    </div>
  );
};

export default AdminUserDetailsPage;
