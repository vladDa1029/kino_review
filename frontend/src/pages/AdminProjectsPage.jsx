import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { listAdminProjects } from '../services/api';

const AdminProjectsPage = () => {
  const navigate = useNavigate();
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [includeArchived, setIncludeArchived] = useState(false);

  useEffect(() => {
    let cancelled = false;

    const run = async () => {
      try {
        setLoading(true);
        setError('');
        const response = await listAdminProjects({ includeArchived });

        if (!cancelled) {
          setProjects(response.items || []);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err.message || 'Не удалось загрузить проекты');
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
  }, [includeArchived]);

  return (
    <div className="admin-screen admin-content-stack">
      <section className="management-card admin-panel-card">
        <div className="admin-section-header">
          <div>
            <span className="projects-panel-eyebrow">Project admin</span>
            <h2>Проекты</h2>
            <p>Глобальный просмотр проектов сервиса с доступом суперпользователя.</p>
          </div>
          <label className="user-admin-flag">
            <input
              type="checkbox"
              checked={includeArchived}
              onChange={(event) => setIncludeArchived(event.target.checked)}
            />
            <span>Показывать архивные</span>
          </label>
        </div>
      </section>

      <section className="management-card admin-panel-card">
        <div className="admin-section-header">
          <div>
            <h3>Список проектов</h3>
            <p>Найдено: {projects.length}</p>
          </div>
        </div>

        {error ? <div className="error-text">{error}</div> : null}
        {loading ? (
          <div>Загрузка...</div>
        ) : (
          <div className="table-shell">
            <table className="user-table">
              <thead>
                <tr>
                  <th>Название</th>
                  <th>Owner</th>
                  <th>Status</th>
                  <th>Created</th>
                  <th>Updated</th>
                  <th>Действия</th>
                </tr>
              </thead>
              <tbody>
                {projects.map((project) => (
                  <tr key={project.oid}>
                    <td data-label="Название">
                      <strong>{project.title}</strong>
                      <div className="table-subtext">{project.description || 'Без описания'}</div>
                    </td>
                    <td data-label="Owner">{project.owner_id}</td>
                    <td data-label="Status">{project.status}</td>
                    <td data-label="Created">{new Date(project.created_at).toLocaleString()}</td>
                    <td data-label="Updated">{new Date(project.updated_at).toLocaleString()}</td>
                    <td data-label="Действия">
                      <div className="table-actions">
                        <button
                          type="button"
                          className="ghost-action-btn"
                          onClick={() => navigate(`/admin/projects/${project.oid}`)}
                        >
                          Открыть
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
};

export default AdminProjectsPage;
