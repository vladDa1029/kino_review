import { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-toastify';
import {
  createAdminUser,
  deleteAdminUser,
  getUsers,
  updateAdminUser,
} from '../services/api';

const createInitialForm = () => ({
  email: '',
  password: '',
  is_active: true,
  is_superuser: false,
  is_verified: false,
});

const createInitialFilters = () => ({
  search: '',
  sortBy: 'create_at',
  sortDir: 'desc',
});

const UserList = () => {
  const navigate = useNavigate();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [removingUserId, setRemovingUserId] = useState(null);
  const [error, setError] = useState(null);
  const [editingUserId, setEditingUserId] = useState(null);
  const [form, setForm] = useState(createInitialForm);
  const [filters, setFilters] = useState(createInitialFilters);
  const [pagination, setPagination] = useState({
    page: 1,
    pageSize: 10,
    totalPages: 1,
    totalCount: 0,
  });

  const fetchUsers = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await getUsers(pagination.page, pagination.pageSize, {
        search: filters.search.trim() || undefined,
        sortBy: filters.sortBy || undefined,
        sortDir: filters.sortDir || undefined,
      });

      setUsers(response.users || []);
      setPagination((prev) => ({
        ...prev,
        totalPages: response.pages || 1,
        totalCount: response.total_count || 0,
      }));
    } catch (err) {
      setError(err.message || 'Не удалось загрузить пользователей');
    } finally {
      setLoading(false);
    }
  }, [filters.search, filters.sortBy, filters.sortDir, pagination.page, pagination.pageSize]);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  const handlePageChange = (nextPage) => {
    if (nextPage < 1 || nextPage > pagination.totalPages) {
      return;
    }

    setPagination((prev) => ({ ...prev, page: nextPage }));
  };

  const handleFilterChange = (event) => {
    const { name, value } = event.target;
    setFilters((prev) => ({
      ...prev,
      [name]: value,
    }));
    setPagination((prev) => ({ ...prev, page: 1 }));
  };

  const handleInputChange = (event) => {
    const { name, value, type, checked } = event.target;
    setForm((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }));
  };

  const resetForm = () => {
    setForm(createInitialForm());
    setEditingUserId(null);
  };

  const handleSubmit = async (event) => {
    event.preventDefault();

    if (!form.email.trim()) {
      toast.error('Укажите email пользователя');
      return;
    }

    if (!editingUserId && !form.password.trim()) {
      toast.error('Для нового пользователя нужен пароль');
      return;
    }

    setSubmitting(true);

    try {
      if (editingUserId) {
        const payload = {
          email: form.email.trim(),
          is_active: form.is_active,
          is_superuser: form.is_superuser,
          is_verified: form.is_verified,
        };

        if (form.password.trim()) {
          payload.password = form.password.trim();
        }

        await updateAdminUser(editingUserId, payload);
        toast.success('Пользователь обновлен');
      } else {
        await createAdminUser({
          email: form.email.trim(),
          password: form.password.trim(),
          is_active: form.is_active,
          is_superuser: form.is_superuser,
          is_verified: form.is_verified,
        });
        toast.success('Пользователь создан');
      }

      resetForm();
      await fetchUsers();
    } catch (err) {
      toast.error(err.message || 'Не удалось сохранить пользователя');
    } finally {
      setSubmitting(false);
    }
  };

  const handleEdit = (user) => {
    setEditingUserId(user.oid);
    setForm({
      email: user.email || '',
      password: '',
      is_active: Boolean(user.is_active),
      is_superuser: Boolean(user.is_superuser),
      is_verified: Boolean(user.is_verified),
    });
  };

  const handleDelete = async (user) => {
    if (!window.confirm(`Удалить пользователя ${user.email}?`)) {
      return;
    }

    setRemovingUserId(user.oid);

    try {
      await deleteAdminUser(user.oid);
      toast.success('Пользователь удален');

      if (editingUserId === user.oid) {
        resetForm();
      }

      await fetchUsers();
    } catch (err) {
      toast.error(err.message || 'Не удалось удалить пользователя');
    } finally {
      setRemovingUserId(null);
    }
  };

  return (
    <div className="admin-screen admin-content-stack">
      <section className="management-card admin-panel-card">
        <div className="admin-section-header">
          <div>
            <span className="projects-panel-eyebrow">Admin</span>
            <h2>Пользователи</h2>
            <p>Управление учетными записями через административные методы сервиса авторизации.</p>
          </div>
        </div>

        <div className="grid-two-columns admin-toolbar-grid">
          <label className="field-block">
            <span>Поиск по email</span>
            <input
              type="search"
              name="search"
              value={filters.search}
              onChange={handleFilterChange}
              placeholder="user@example.com"
            />
          </label>

          <div className="grid-two-columns admin-toolbar-grid-tight">
            <label className="field-block">
              <span>Сортировка</span>
              <select name="sortBy" value={filters.sortBy} onChange={handleFilterChange}>
                <option value="create_at">Дата создания</option>
                <option value="is_active">Активность</option>
                <option value="is_superuser">Суперпользователь</option>
                <option value="is_verified">Подтверждение</option>
              </select>
            </label>

            <label className="field-block">
              <span>Направление</span>
              <select name="sortDir" value={filters.sortDir} onChange={handleFilterChange}>
                <option value="desc">Сначала новые</option>
                <option value="asc">Сначала старые</option>
              </select>
            </label>
          </div>
        </div>
      </section>

      <section className="management-card admin-panel-card user-admin-form-card">
        <div className="admin-section-header">
          <div>
            <h3>{editingUserId ? 'Редактирование пользователя' : 'Новый пользователь'}</h3>
            <p>Пароль должен быть длиной от 4 до 24 символов.</p>
          </div>
        </div>

        <form className="stacked-form" onSubmit={handleSubmit}>
          <div className="grid-two-columns">
            <label className="field-block">
              <span>Email</span>
              <input type="email" name="email" value={form.email} onChange={handleInputChange} required />
            </label>

            <label className="field-block">
              <span>{editingUserId ? 'Новый пароль' : 'Пароль'}</span>
              <input
                type="password"
                name="password"
                value={form.password}
                onChange={handleInputChange}
                minLength={4}
                maxLength={24}
                placeholder={editingUserId ? 'Оставьте пустым, чтобы не менять' : 'От 4 до 24 символов'}
              />
            </label>
          </div>

          <div className="user-admin-flags">
            <label className="user-admin-flag">
              <input type="checkbox" name="is_active" checked={form.is_active} onChange={handleInputChange} />
              <span>Активен</span>
            </label>
            <label className="user-admin-flag">
              <input
                type="checkbox"
                name="is_superuser"
                checked={form.is_superuser}
                onChange={handleInputChange}
              />
              <span>Суперпользователь</span>
            </label>
            <label className="user-admin-flag">
              <input
                type="checkbox"
                name="is_verified"
                checked={form.is_verified}
                onChange={handleInputChange}
              />
              <span>Подтвержден</span>
            </label>
          </div>

          <div className="inline-actions">
            <button type="submit" className="profile-save-btn compact" disabled={submitting}>
              {submitting ? 'Сохраняем...' : editingUserId ? 'Сохранить' : 'Создать пользователя'}
            </button>
            <button type="button" className="secondary-btn" onClick={resetForm} disabled={submitting}>
              Сбросить
            </button>
          </div>
        </form>
      </section>

      <section className="management-card admin-panel-card">
        <div className="admin-section-header">
          <div>
            <h3>Список пользователей</h3>
            <p>Всего найдено: {pagination.totalCount}</p>
          </div>
        </div>

        {error ? <div className="error-text">{error}</div> : null}

        {loading ? (
          <div>Загрузка...</div>
        ) : (
          <>
            <div className="table-shell">
              <table className="user-table">
                <thead>
                  <tr>
                    <th>Email</th>
                    <th>Активен</th>
                    <th>Superuser</th>
                    <th>Verified</th>
                    <th>OID</th>
                    <th>Действия</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((user) => {
                    const isRemoving = removingUserId === user.oid;

                    return (
                      <tr key={user.oid}>
                        <td data-label="Email">{user.email}</td>
                        <td data-label="Активен">{user.is_active ? 'Да' : 'Нет'}</td>
                        <td data-label="Superuser">{user.is_superuser ? 'Да' : 'Нет'}</td>
                        <td data-label="Verified">{user.is_verified ? 'Да' : 'Нет'}</td>
                        <td data-label="OID">{user.oid}</td>
                        <td data-label="Действия">
                          <div className="table-actions">
                            <button
                              type="button"
                              className="ghost-action-btn"
                              onClick={() => navigate(`/admin/users/${user.oid}`)}
                            >
                              Открыть
                            </button>
                            <button type="button" className="ghost-action-btn" onClick={() => handleEdit(user)}>
                              Изменить
                            </button>
                            <button
                              type="button"
                              className="ghost-action-btn danger"
                              onClick={() => handleDelete(user)}
                              disabled={isRemoving}
                            >
                              {isRemoving ? 'Удаляем...' : 'Удалить'}
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            <div className="pagination">
              <button onClick={() => handlePageChange(pagination.page - 1)} disabled={pagination.page === 1}>
                Назад
              </button>
              <span>
                Страница {pagination.page} из {pagination.totalPages}
              </span>
              <button
                onClick={() => handlePageChange(pagination.page + 1)}
                disabled={pagination.page === pagination.totalPages}
              >
                Вперед
              </button>
            </div>
          </>
        )}
      </section>
    </div>
  );
};

export default UserList;
