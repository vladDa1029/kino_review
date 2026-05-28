import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { getAdminProject, getAdminProjectMember, listAdminProjectMembers } from '../services/api';

const projectStatusLabels = {
  10: 'Активен',
  20: 'Архивирован',
};

const memberStatusLabels = {
  0: 'Ожидает приглашения',
  10: 'Активен',
  20: 'Удалён',
};

const getProjectStatusLabel = (status) => projectStatusLabels[Number(status)] || `Статус ${status}`;
const getMemberStatusLabel = (status) => memberStatusLabels[Number(status)] || `Статус ${status}`;

const AdminProjectDetailsPage = () => {
  const { projectId } = useParams();
  const [project, setProject] = useState(null);
  const [members, setMembers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [includeInactive, setIncludeInactive] = useState(false);
  const [memberLookupId, setMemberLookupId] = useState('');
  const [memberLookupLoading, setMemberLookupLoading] = useState(false);
  const [memberLookupError, setMemberLookupError] = useState('');
  const [selectedMember, setSelectedMember] = useState(null);

  useEffect(() => {
    let cancelled = false;

    const run = async () => {
      try {
        setLoading(true);
        setError('');

        const [projectResponse, membersResponse] = await Promise.all([
          getAdminProject(projectId),
          listAdminProjectMembers(projectId, { includeInactive }),
        ]);

        if (!cancelled) {
          setProject(projectResponse);
          setMembers(membersResponse.items || []);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err.message || 'Не удалось загрузить проект');
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
  }, [includeInactive, projectId]);

  const handleMemberLookup = async (event) => {
    event.preventDefault();

    if (!memberLookupId.trim()) {
      setMemberLookupError('Укажите user_id участника');
      setSelectedMember(null);
      return;
    }

    try {
      setMemberLookupLoading(true);
      setMemberLookupError('');
      const response = await getAdminProjectMember(projectId, memberLookupId.trim(), {
        includeInactive,
      });
      setSelectedMember(response);
    } catch (err) {
      setSelectedMember(null);
      setMemberLookupError(err.message || 'Не удалось получить участника проекта');
    } finally {
      setMemberLookupLoading(false);
    }
  };

  return (
    <div className="admin-screen admin-content-stack">
      <section className="management-card admin-panel-card">
        <div className="admin-section-header">
          <div>
            <span className="projects-panel-eyebrow">Администрирование проекта</span>
            <h2>{project?.title || 'Проект'}</h2>
            <p>{project?.description || 'Описание проекта отсутствует.'}</p>
          </div>
          <div className="inline-actions">
            <Link className="secondary-btn admin-inline-link" to="/admin/projects">
              Ко всем проектам
            </Link>
            <label className="user-admin-flag">
              <input
                type="checkbox"
                checked={includeInactive}
                onChange={(event) => setIncludeInactive(event.target.checked)}
              />
              <span>Неактивные участники</span>
            </label>
          </div>
        </div>
      </section>

      {error ? <div className="management-card admin-panel-card error-text">{error}</div> : null}

      {loading ? (
        <section className="management-card admin-panel-card">Загрузка...</section>
      ) : (
        <>
          <section className="admin-summary-grid">
            <div className="admin-summary-card">
              <span>OID</span>
              <strong>{project?.oid}</strong>
            </div>
            <div className="admin-summary-card">
              <span>Владелец</span>
              <strong>{project?.owner_id}</strong>
            </div>
            <div className="admin-summary-card">
              <span>Статус</span>
              <strong>{getProjectStatusLabel(project?.status)}</strong>
            </div>
            <div className="admin-summary-card">
              <span>Обновлён</span>
              <strong>{project?.updated_at ? new Date(project.updated_at).toLocaleString() : '-'}</strong>
            </div>
          </section>

          <section className="management-card admin-panel-card">
            <div className="admin-section-header">
              <div>
                <h3>Участники проекта</h3>
                <p>Найдено: {members.length}</p>
              </div>
            </div>

            <div className="table-shell admin-table-shell">
              <table className="user-table">
                <thead>
                  <tr>
                    <th>User ID</th>
                    <th>Роль</th>
                    <th>Статус</th>
                    <th>Пригласил</th>
                    <th>Создан</th>
                    <th>Обновлён</th>
                  </tr>
                </thead>
                <tbody>
                  {members.map((member) => (
                    <tr key={member.oid}>
                      <td data-label="User ID">{member.user_id}</td>
                      <td data-label="Роль">{member.role}</td>
                      <td data-label="Статус">{getMemberStatusLabel(member.status)}</td>
                      <td data-label="Пригласил">{member.invited_by}</td>
                      <td data-label="Создан">{new Date(member.created_at).toLocaleString()}</td>
                      <td data-label="Обновлён">{new Date(member.updated_at).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className="management-card admin-panel-card">
            <div className="section-heading">
              <div>
                <h3>Поиск участника по user_id</h3>
                <p>Использует endpoint `GET /project/admin/projects/{'{project_id}'}/members/{'{target_user_id}'}`.</p>
              </div>
            </div>

            <form className="stacked-form" onSubmit={handleMemberLookup}>
              <label className="field-block">
                <span>User ID</span>
                <input
                  value={memberLookupId}
                  onChange={(event) => setMemberLookupId(event.target.value)}
                  placeholder="UUID пользователя"
                  required
                />
              </label>

              <div className="inline-actions">
                <button type="submit" className="profile-save-btn compact" disabled={memberLookupLoading}>
                  {memberLookupLoading ? 'Ищем...' : 'Найти участника'}
                </button>
              </div>
            </form>

            {memberLookupError ? <div className="error-text">{memberLookupError}</div> : null}

            {selectedMember ? (
              <div className="admin-summary-grid">
                <div className="admin-summary-card">
                  <span>User ID</span>
                  <strong>{selectedMember.user_id}</strong>
                </div>
                <div className="admin-summary-card">
                  <span>Роль</span>
                  <strong>{selectedMember.role}</strong>
                </div>
                <div className="admin-summary-card">
                  <span>Статус</span>
                  <strong>{getMemberStatusLabel(selectedMember.status)}</strong>
                </div>
                <div className="admin-summary-card">
                  <span>Пригласил</span>
                  <strong>{selectedMember.invited_by}</strong>
                </div>
              </div>
            ) : null}
          </section>
        </>
      )}
    </div>
  );
};

export default AdminProjectDetailsPage;
