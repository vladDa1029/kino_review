import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/useAuth';
import { getUsers } from '../services/api';

const UserList = () => {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [pagination, setPagination] = useState({
    page: 1,
    pageSize: 5,
    totalPages: 1,
    totalCount: 0,
  });

  const { token } = useAuth();

  const fetchUsers = useCallback(async () => {
    try {
      setLoading(true);
      const response = await getUsers(pagination.page, pagination.pageSize);

      setUsers(response.users);
      setPagination((prev) => ({
        ...prev,
        totalPages: response.pages,
        totalCount: response.total_count,
      }));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [pagination.page, pagination.pageSize]);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  const handlePageChange = (newPage) => {
    if (newPage >= 1 && newPage <= pagination.totalPages) {
      setPagination((prev) => ({ ...prev, page: newPage }));
    }
  };

  if (!token) {
    return <div>Для просмотра списка пользователей необходимо войти в систему</div>;
  }

  if (error) {
    return <div>Ошибка: {error}</div>;
  }

  return (
    <div className="user-list-container">
      <h2>Список пользователей</h2>
      {loading ? (
        <div>Загрузка...</div>
      ) : (
        <>
          <table className="user-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Email</th>
                <th>Имя</th>
                <th>Телефон</th>
                <th>Активен</th>
                <th>Суперпользователь</th>
                <th>Подтверждён</th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <tr key={user.oid}>
                  <td>{user.oid}</td>
                  <td>{user.email}</td>
                  <td>{user.username ?? user.description?.username ?? '-'}</td>
                  <td>{user.phone ?? user.description?.phone ?? '-'}</td>
                  <td>{user.is_active ? 'Да' : 'Нет'}</td>
                  <td>{user.is_superuser ? 'Да' : 'Нет'}</td>
                  <td>{user.is_verified ? 'Да' : 'Нет'}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <div className="pagination">
            <button
              onClick={() => handlePageChange(pagination.page - 1)}
              disabled={pagination.page === 1}
            >
              Назад
            </button>

            <span>
              Страница {pagination.page} из {pagination.totalPages}
            </span>

            <button
              onClick={() => handlePageChange(pagination.page + 1)}
              disabled={pagination.page === pagination.totalPages}
            >
              Вперёд
            </button>
          </div>
        </>
      )}
    </div>
  );
};

export default UserList;

