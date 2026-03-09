import { useCallback, useEffect, useState } from 'react';
import { NavLink } from 'react-router-dom';
import { toast } from 'react-toastify';
import {
  createMicrofon,
  deleteMicrofon,
  listMicrofons,
  updateMicrofon,
} from '../services/api';

const initialForm = {
  title: '',
  description: '',
  type: '',
};

const Projects = () => {
  const [form, setForm] = useState(initialForm);
  const [editingId, setEditingId] = useState(null);
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [pagination, setPagination] = useState({
    page: 1,
    pageSize: 10,
    totalPages: 1,
    totalCount: 0,
  });

  const fetchMicrofons = useCallback(async () => {
    try {
      setLoading(true);
      const data = await listMicrofons({
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
      toast.error(error.message || 'Не удалось загрузить рабочую зону');
    } finally {
      setLoading(false);
    }
  }, [pagination.page, pagination.pageSize]);

  useEffect(() => {
    fetchMicrofons();
  }, [fetchMicrofons]);

  const handleChange = (event) => {
    const { name, value } = event.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const resetForm = () => {
    setForm(initialForm);
    setEditingId(null);
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
        await updateMicrofon(editingId, payload);
        toast.success('Запись обновлена');
      } else {
        await createMicrofon(payload);
        toast.success('Запись добавлена');
      }

      resetForm();
      await fetchMicrofons();
    } catch (error) {
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

  const handleDelete = async (microfonId) => {
    const confirmed = window.confirm('Удалить запись?');
    if (!confirmed) {
      return;
    }

    try {
      await deleteMicrofon(microfonId);
      toast.success('Запись удалена');

      if (items.length === 1 && pagination.page > 1) {
        setPagination((prev) => ({ ...prev, page: prev.page - 1 }));
      } else {
        await fetchMicrofons();
      }
    } catch (error) {
      toast.error(error.message || 'Не удалось удалить запись');
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
        <p>Управление вашим списком оборудования.</p>

        <form className="microfon-form" onSubmit={handleSubmit}>
          <label htmlFor="microfon-title">Название</label>
          <input
            id="microfon-title"
            name="title"
            value={form.title}
            onChange={handleChange}
            className="profile-input"
            placeholder="Sony A7S III"
            required
          />

          <label htmlFor="microfon-description">Описание</label>
          <textarea
            id="microfon-description"
            name="description"
            value={form.description}
            onChange={handleChange}
            className="profile-textarea"
            placeholder="Например: полнокадровая беззеркальная камера"
            rows={3}
            required
          />

          <label htmlFor="microfon-type">Тип</label>
          <input
            id="microfon-type"
            name="type"
            value={form.type}
            onChange={handleChange}
            className="profile-input"
            placeholder="Например: mirrorless"
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
                          >
                            Удалить
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
