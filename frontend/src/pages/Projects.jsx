import { useCallback, useEffect, useMemo, useState } from 'react';
import { NavLink } from 'react-router-dom';
import { toast } from 'react-toastify';
import { ApiError } from '../services/httpClient';
import {
  createCamera,
  createCameraTripod,
  createLight,
  createMicrofon,
  deleteCamera,
  deleteCameraTripod,
  deleteLight,
  deleteMicrofon,
  listCameras,
  listCameraTripods,
  listLights,
  listMicrofons,
  updateCamera,
  updateCameraTripod,
  updateLight,
  updateMicrofon,
} from '../services/api';

const initialForm = {
  title: '',
  description: '',
  type: '',
};

const resourceMeta = {
  microfons: {
    label: 'Микрофоны',
    one: 'микрофон',
    create: createMicrofon,
    list: listMicrofons,
    update: updateMicrofon,
    remove: deleteMicrofon,
    titlePlaceholder: 'Rode NT1',
    descriptionPlaceholder: 'Например: студийный конденсаторный микрофон',
    typePlaceholder: 'Например: condenser',
  },
  cameras: {
    label: 'Камеры',
    one: 'камера',
    create: createCamera,
    list: listCameras,
    update: updateCamera,
    remove: deleteCamera,
    titlePlaceholder: 'Sony A7S III',
    descriptionPlaceholder: 'Например: полнокадровая беззеркальная камера',
    typePlaceholder: 'Например: mirrorless',
  },
  'camera-tripods': {
    label: 'Штативы для камер',
    one: 'штатив',
    create: createCameraTripod,
    list: listCameraTripods,
    update: updateCameraTripod,
    remove: deleteCameraTripod,
    titlePlaceholder: 'Manfrotto 190X',
    descriptionPlaceholder: 'Например: алюминиевый штатив для видео и фото',
    typePlaceholder: 'Например: fluid-head',
  },
  lights: {
    label: 'Свет',
    one: 'свет',
    create: createLight,
    list: listLights,
    update: updateLight,
    remove: deleteLight,
    titlePlaceholder: 'Aputure 120d',
    descriptionPlaceholder: 'Например: светодиодный источник постоянного света',
    typePlaceholder: 'Например: led',
  },
};

const Projects = () => {
  const [activeResource, setActiveResource] = useState('microfons');
  const [form, setForm] = useState(initialForm);
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

  const currentResource = useMemo(() => resourceMeta[activeResource], [activeResource]);

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

  useEffect(() => {
    fetchItems();
  }, [fetchItems]);

  const handleChange = (event) => {
    const { name, value } = event.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const resetForm = () => {
    setForm(initialForm);
    setEditingId(null);
  };

  const switchResource = (nextResource) => {
    if (nextResource === activeResource) {
      return;
    }
    setActiveResource(nextResource);
    resetForm();
    setPagination((prev) => ({ ...prev, page: 1, totalPages: 1, totalCount: 0 }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setSubmitting(true);

    const payload = {
      title: form.title.trim(),
      description: form.description.trim(),
      type: form.type.trim(),
    };

    try {
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
    setForm({
      title: item.title || '',
      description: item.description || '',
      type: item.type || '',
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
        toast.info('Запись уже удалена на сервере');
        return;
      }
      toast.error(error.message || 'Не удалось удалить запись');
    } finally {
      setDeletingId(null);
    }
  };

  const handlePageChange = (newPage) => {
    if (newPage >= 1 && newPage <= pagination.totalPages) {
      setPagination((prev) => ({ ...prev, page: newPage }));
    }
  };

  return (
    <section className="projects-wrapper">
      <div className="projects-page">
        <div className="page-switcher">
          <NavLink
            to="/profile"
            className={({ isActive }) => `switcher-btn ${isActive ? 'active' : ''}`}
          >
            Профиль
          </NavLink>
          <NavLink
            to="/projects"
            className={({ isActive }) => `switcher-btn ${isActive ? 'active' : ''}`}
          >
            Рабочая зона
          </NavLink>
        </div>

        <h1>Рабочая зона</h1>

        <div className="equipment-switcher" role="tablist" aria-label="Тип оборудования">
          <button
            type="button"
            className={`switcher-btn ${activeResource === 'microfons' ? 'active' : ''}`}
            onClick={() => switchResource('microfons')}
          >
            Микрофоны
          </button>
          <button
            type="button"
            className={`switcher-btn ${activeResource === 'cameras' ? 'active' : ''}`}
            onClick={() => switchResource('cameras')}
          >
            Камеры
          </button>
          <button
            type="button"
            className={`switcher-btn ${activeResource === 'camera-tripods' ? 'active' : ''}`}
            onClick={() => switchResource('camera-tripods')}
          >
            Штативы
          </button>
          <button
            type="button"
            className={`switcher-btn ${activeResource === 'lights' ? 'active' : ''}`}
            onClick={() => switchResource('lights')}
          >
            Свет
          </button>
        </div>

        <p>Текущий раздел: {currentResource.label}</p>

        <form className="microfon-form" onSubmit={handleSubmit}>
          <label htmlFor="equipment-title">Название {currentResource.one}</label>
          <input
            id="equipment-title"
            name="title"
            value={form.title}
            onChange={handleChange}
            className="profile-input"
            placeholder={currentResource.titlePlaceholder}
            required
          />

          <label htmlFor="equipment-description">Описание {currentResource.one}</label>
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

          <label htmlFor="equipment-type">Тип {currentResource.one}</label>
          <input
            id="equipment-type"
            name="type"
            value={form.type}
            onChange={handleChange}
            className="profile-input"
            placeholder={currentResource.typePlaceholder}
            required
          />

          <div className="microfon-actions">
            <button type="submit" className="profile-save-btn" disabled={submitting}>
              {submitting ? 'Сохранение...' : editingId ? 'Обновить' : 'Добавить'}
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
            <table className="user-table microfon-table">
              <thead>
                <tr>
                  <th>Название</th>
                  <th>Описание</th>
                  <th>Тип</th>
                  <th>Создано</th>
                  <th>Действия</th>
                </tr>
              </thead>
              <tbody>
                {items.length === 0 ? (
                  <tr>
                    <td colSpan={5}>Список пока пуст</td>
                  </tr>
                ) : (
                  items.map((item) => (
                    <tr key={item.oid}>
                      <td>{item.title}</td>
                      <td>{item.description}</td>
                      <td>{item.type}</td>
                      <td>{item.create_at ? new Date(item.create_at).toLocaleString('ru-RU') : '-'}</td>
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
      </div>
    </section>
  );
};

export default Projects;
