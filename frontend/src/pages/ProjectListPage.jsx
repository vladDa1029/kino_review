import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-toastify';

import {
  archiveProject,
  changeProjectMemberRole,
  createProject,
  inviteProjectMember,
  listProjectMembers,
  removeProjectMember,
  updateProject,
} from '../services/api';
import { useAuth } from '../context/useAuth';
import { useProjectContext } from '../context/useProjectContext';

const initialForm = {
  title: '',
  description: '',
};

const initialMemberForm = {
  userId: '',
  role: 'ACTOR',
};

const roleOptions = [
  { value: 'DIRECTOR', label: 'Режиссер' },
  { value: 'PROP_MASTER', label: 'Реквизитор' },
  { value: 'CAMERA', label: 'Камера' },
  { value: 'SOUND', label: 'Звук' },
  { value: 'LIGHT', label: 'Свет' },
  { value: 'ACTOR', label: 'Актер' },
];

const statusLabels = {
  0: 'Активен',
  1: 'Архивирован',
};

const memberStatusLabels = {
  0: 'Активен',
  1: 'Неактивен',
};

const formatDate = (value) => {
  if (!value) {
    return 'Нет даты';
  }

  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 'Нет даты' : date.toLocaleDateString('ru-RU');
};

const getProjectId = (project) => project.oid || project.id;

const getStatusLabel = (status) => statusLabels[status] || `Статус ${status}`;

const getRoleLabel = (role) => roleOptions.find((option) => option.value === role)?.label || role;

const getMemberStatusLabel = (status) => memberStatusLabels[status] || `Статус ${status}`;

const getCurrentUserId = (userData) =>
  userData?.user_id ||
  userData?.userId ||
  userData?.sub ||
  userData?.id ||
  userData?.oid ||
  userData?.uid ||
  userData?.actor_id ||
  userData?.subject ||
  '';

const isUuid = (value) =>
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value);

const ProjectListPage = () => {
  const navigate = useNavigate();
  const { userData } = useAuth();
  const {
    projects,
    activeProjectId,
    isProjectsLoading,
    refreshProjects,
    setActiveProjectId,
  } = useProjectContext();
  const [form, setForm] = useState(initialForm);
  const [editingId, setEditingId] = useState(null);
  const [includeArchived, setIncludeArchived] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [archivingId, setArchivingId] = useState(null);
  const [memberProjectId, setMemberProjectId] = useState('');
  const [members, setMembers] = useState([]);
  const [memberForm, setMemberForm] = useState(initialMemberForm);
  const [includeInactiveMembers, setIncludeInactiveMembers] = useState(false);
  const [isMembersLoading, setIsMembersLoading] = useState(false);
  const [isInvitingMember, setIsInvitingMember] = useState(false);
  const [updatingMemberId, setUpdatingMemberId] = useState(null);
  const [removingMemberId, setRemovingMemberId] = useState(null);

  const loadProjects = useCallback(async () => {
    await refreshProjects({ includeArchived });
  }, [includeArchived, refreshProjects]);

  useEffect(() => {
    loadProjects();
  }, [loadProjects]);

  useEffect(() => {
    if (memberProjectId && projects.some((project) => getProjectId(project) === memberProjectId)) {
      return;
    }

    setMemberProjectId(activeProjectId || (projects[0] ? getProjectId(projects[0]) : ''));
  }, [activeProjectId, memberProjectId, projects]);

  const loadMembers = useCallback(async () => {
    if (!memberProjectId) {
      setMembers([]);
      return;
    }

    setIsMembersLoading(true);

    try {
      const response = await listProjectMembers(memberProjectId, {
        includeInactive: includeInactiveMembers,
      });
      setMembers(Array.isArray(response?.items) ? response.items : []);
    } catch (error) {
      setMembers([]);
      toast.error(error?.message || 'Не удалось загрузить участников проекта');
    } finally {
      setIsMembersLoading(false);
    }
  }, [includeInactiveMembers, memberProjectId]);

  useEffect(() => {
    loadMembers();
  }, [loadMembers]);

  const counters = useMemo(
    () => ({
      total: projects.length,
      active: projects.filter((project) => project.status === 0).length,
      archived: projects.filter((project) => project.status !== 0).length,
    }),
    [projects],
  );

  const isEditing = Boolean(editingId);
  const currentUserId = getCurrentUserId(userData);
  const memberProject = useMemo(
    () => projects.find((project) => getProjectId(project) === memberProjectId) || null,
    [memberProjectId, projects],
  );
  const currentProjectMember = useMemo(
    () => members.find((member) => member.user_id === currentUserId) || null,
    [currentUserId, members],
  );
  const canManageMembers = Boolean(
    memberProject && currentUserId && (
      memberProject.owner_id === currentUserId ||
      currentProjectMember?.role === 'DIRECTOR'
    ),
  );
  const displayedMembers = useMemo(() => {
    if (!memberProject?.owner_id) {
      return members;
    }

    const hasOwnerInMembers = members.some((member) => member.user_id === memberProject.owner_id);
    if (hasOwnerInMembers) {
      return members;
    }

    return [
      {
        oid: `owner-${memberProject.owner_id}`,
        user_id: memberProject.owner_id,
        role: 'DIRECTOR',
        status: 0,
        invited_by: memberProject.owner_id,
        created_at: memberProject.created_at,
        isOwner: true,
      },
      ...members,
    ];
  }, [memberProject, members]);

  const handleChange = (event) => {
    const { name, value } = event.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleResetForm = () => {
    setForm(initialForm);
    setEditingId(null);
  };

  const handleEditProject = (project) => {
    setEditingId(getProjectId(project));
    setForm({
      title: project.title || '',
      description: project.description || '',
    });
  };

  const handleSubmit = async (event) => {
    event.preventDefault();

    const title = form.title.trim();
    const description = form.description.trim();

    if (!title) {
      toast.error('Укажите название проекта');
      return;
    }

    setSubmitting(true);

    try {
      if (isEditing) {
        await updateProject(editingId, { title, description });
        toast.success('Проект обновлен');
      } else {
        const createdProject = await createProject({ title, description });
        const createdProjectId = getProjectId(createdProject || {});
        if (createdProjectId) {
          setActiveProjectId(createdProjectId);
          setMemberProjectId(createdProjectId);
        }
        toast.success('Проект создан');
      }

      handleResetForm();
      await loadProjects();
    } catch (error) {
      toast.error(error?.message || 'Не удалось сохранить проект');
    } finally {
      setSubmitting(false);
    }
  };

  const handleArchiveProject = async (project) => {
    const projectId = getProjectId(project);

    if (!projectId || !window.confirm(`Архивировать проект "${project.title}"?`)) {
      return;
    }

    setArchivingId(projectId);

    try {
      await archiveProject(projectId);
      toast.success('Проект архивирован');

      if (editingId === projectId) {
        handleResetForm();
      }

      await loadProjects();
    } catch (error) {
      toast.error(error?.message || 'Не удалось архивировать проект');
    } finally {
      setArchivingId(null);
    }
  };

  const handleOpenProject = (project) => {
    const projectId = getProjectId(project);

    if (!projectId) {
      return;
    }

    setActiveProjectId(projectId);
    navigate('/projects');
  };

  const handleMemberFormChange = (event) => {
    const { name, value } = event.target;
    setMemberForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleInviteMember = async (event) => {
    event.preventDefault();

    const userId = memberForm.userId.trim();
    if (!memberProjectId || !userId) {
      toast.error('Выберите проект и укажите user_id участника');
      return;
    }

    if (!isUuid(userId)) {
      toast.error('user_id должен быть UUID в формате xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx');
      return;
    }

    if (!canManageMembers) {
      toast.error('У вас нет прав приглашать участников в этот проект');
      return;
    }

    setIsInvitingMember(true);

    try {
      await inviteProjectMember(memberProjectId, {
        user_id: userId,
        role: memberForm.role,
      });
      toast.success('Участник приглашен в проект');
      setMemberForm(initialMemberForm);
      await loadMembers();
    } catch (error) {
      toast.error(error?.message || 'Не удалось пригласить участника');
    } finally {
      setIsInvitingMember(false);
    }
  };

  const handleChangeMemberRole = async (targetUserId, role) => {
    if (!memberProjectId || !targetUserId) {
      return;
    }

    if (!canManageMembers) {
      toast.error('У вас нет прав менять роли в этом проекте');
      await loadMembers();
      return;
    }

    if (targetUserId === currentUserId) {
      toast.error('Нельзя менять собственную роль из этой панели');
      await loadMembers();
      return;
    }

    setUpdatingMemberId(targetUserId);

    try {
      await changeProjectMemberRole(memberProjectId, targetUserId, { role });
      toast.success('Роль участника обновлена');
      await loadMembers();
    } catch (error) {
      toast.error(error?.message || 'Не удалось изменить роль участника');
    } finally {
      setUpdatingMemberId(null);
    }
  };

  const handleRemoveMember = async (member) => {
    if (!memberProjectId || !member?.user_id || !window.confirm('Удалить участника из проекта?')) {
      return;
    }

    if (!canManageMembers) {
      toast.error('У вас нет прав удалять участников из этого проекта');
      return;
    }

    if (member.user_id === currentUserId) {
      toast.error('Нельзя удалить себя из проекта из этой панели');
      return;
    }

    setRemovingMemberId(member.user_id);

    try {
      await removeProjectMember(memberProjectId, member.user_id);
      toast.success('Участник удален из проекта');
      await loadMembers();
    } catch (error) {
      toast.error(error?.message || 'Не удалось удалить участника');
    } finally {
      setRemovingMemberId(null);
    }
  };

  return (
    <section className="project-list-page">
      <div className="dashboard-panel project-list-hero">
        <div>
          <span className="projects-panel-eyebrow">Проекты</span>
          <h1>Проектная панель</h1>
          <p>Создавайте проекты, храните описание и быстро возвращайтесь к рабочему списку.</p>
        </div>

        <div className="project-list-stats" aria-label="Сводка проектов">
          <div>
            <span>Всего</span>
            <strong>{counters.total}</strong>
          </div>
          <div>
            <span>Активные</span>
            <strong>{counters.active}</strong>
          </div>
          <div>
            <span>Архив</span>
            <strong>{counters.archived}</strong>
          </div>
        </div>
      </div>

      <div className="project-list-layout">
        <section className="dashboard-panel project-create-panel">
          <div className="section-heading">
            <h2>{isEditing ? 'Редактировать проект' : 'Новый проект'}</h2>
            <p>Заполните поля, которые принимает сервис проектов.</p>
          </div>

          <form className="stacked-form" onSubmit={handleSubmit}>
            <label className="field-block">
              <span>Название</span>
              <input
                name="title"
                value={form.title}
                onChange={handleChange}
                placeholder="Музыкальный клип"
                maxLength={255}
              />
            </label>

            <label className="field-block">
              <span>Описание</span>
              <textarea
                name="description"
                value={form.description}
                onChange={handleChange}
                placeholder="Коротко о проекте, команде или задаче"
                maxLength={2000}
                rows={5}
              />
            </label>

            <div className="project-form-actions">
              <button type="submit" className="profile-save-btn compact" disabled={submitting}>
                {submitting ? 'Сохраняем...' : isEditing ? 'Сохранить' : 'Создать проект'}
              </button>
              {isEditing && (
                <button
                  type="button"
                  className="ghost-action-btn"
                  onClick={handleResetForm}
                  disabled={submitting}
                >
                  Отмена
                </button>
              )}
            </div>
          </form>
        </section>

        <section className="project-cards">
          <div className="dashboard-panel project-list-toolbar">
            <label className="toggle-inline">
              <input
                type="checkbox"
                checked={includeArchived}
                onChange={(event) => setIncludeArchived(event.target.checked)}
              />
              <span>Показывать архивные</span>
            </label>
            <button type="button" className="ghost-action-btn" onClick={loadProjects} disabled={isProjectsLoading}>
              Обновить
            </button>
          </div>

          {isProjectsLoading && (
            <div className="dashboard-panel project-empty-state">
              <p>Загружаем проекты...</p>
            </div>
          )}

          {!isProjectsLoading && projects.length === 0 && (
            <div className="dashboard-panel project-empty-state">
              <p>Пока нет проектов. Создайте первый проект слева.</p>
            </div>
          )}

          {!isProjectsLoading &&
            projects.map((project) => {
              const projectId = getProjectId(project);
              const isArchiving = archivingId === projectId;
              const isActiveProject = activeProjectId === projectId;
              const isOwner = currentUserId && project.owner_id === currentUserId;

              return (
                <article
                  key={projectId}
                  className={`dashboard-panel project-card-item${isActiveProject ? ' is-active-project' : ''}`}
                >
                  <div className="project-card-main">
                    <div className="project-card-meta">
                      <span className="project-type-label">{getStatusLabel(project.status)}</span>
                      <span className="project-type-label">{isOwner ? 'Владелец' : 'Участник'}</span>
                      {isActiveProject ? <span className="project-type-label active">Открыт сейчас</span> : null}
                      <span>Создан: {formatDate(project.created_at)}</span>
                    </div>
                    <h2>{project.title}</h2>
                    <p className="project-card-description">
                      {project.description || 'Описание не указано'}
                    </p>
                    <p>Обновлен: {formatDate(project.updated_at)}</p>
                  </div>

                  <div className="project-card-actions">
                    <button
                      type="button"
                      className="profile-save-btn compact"
                      onClick={() => handleOpenProject(project)}
                    >
                      {isActiveProject ? 'Открыт' : 'Открыть'}
                    </button>
                    <button
                      type="button"
                      className="ghost-action-btn"
                      onClick={() => handleEditProject(project)}
                    >
                      Изменить
                    </button>
                    <button
                      type="button"
                      className="ghost-action-btn danger"
                      onClick={() => handleArchiveProject(project)}
                      disabled={isArchiving}
                    >
                      {isArchiving ? 'Архивируем...' : 'В архив'}
                    </button>
                  </div>
                </article>
              );
            })}
        </section>
      </div>

      <section className="dashboard-panel project-members-panel">
        <div className="section-heading project-members-heading">
          <div>
            <span className="projects-panel-eyebrow">Участники</span>
            <h2>{memberProject ? memberProject.title : 'Выберите проект'}</h2>
          </div>
          <p>
            Приглашайте пользователей по `user_id`, меняйте роль и убирайте участников из проекта.
          </p>
        </div>

        {memberProject && !canManageMembers ? (
          <p className="helper-note">Управлять участниками может создатель проекта или участник с ролью DIRECTOR.</p>
        ) : null}

        <div className="project-members-toolbar">
          <label className="field-block">
            <span>Проект</span>
            <select
              value={memberProjectId}
              onChange={(event) => setMemberProjectId(event.target.value)}
              disabled={projects.length === 0}
            >
              {projects.length === 0 ? (
                <option value="">Нет проектов</option>
              ) : (
                projects.map((project) => {
                  const projectId = getProjectId(project);
                  return (
                    <option key={projectId} value={projectId}>
                      {project.title}
                    </option>
                  );
                })
              )}
            </select>
          </label>

          <label className="toggle-inline">
            <input
              type="checkbox"
              checked={includeInactiveMembers}
              onChange={(event) => setIncludeInactiveMembers(event.target.checked)}
            />
            <span>Показывать неактивных</span>
          </label>

          <button
            type="button"
            className="ghost-action-btn"
            onClick={loadMembers}
            disabled={!memberProjectId || isMembersLoading}
          >
            Обновить
          </button>
        </div>

        <form className="project-member-invite-form" onSubmit={handleInviteMember}>
          <label className="field-block">
            <span>User ID</span>
            <input
              name="userId"
              value={memberForm.userId}
              onChange={handleMemberFormChange}
              disabled={!canManageMembers}
              placeholder="UUID пользователя"
            />
          </label>

          <label className="field-block">
            <span>Роль</span>
            <select
              name="role"
              value={memberForm.role}
              onChange={handleMemberFormChange}
              disabled={!canManageMembers}
            >
              {roleOptions.map((role) => (
                <option key={role.value} value={role.value}>
                  {role.label}
                </option>
              ))}
            </select>
          </label>

          <button
            type="submit"
            className="profile-save-btn compact"
            disabled={!memberProjectId || !canManageMembers || isInvitingMember}
          >
            {isInvitingMember ? 'Приглашаем...' : 'Пригласить'}
          </button>
        </form>

        <div className="project-members-list">
          {isMembersLoading ? <p className="helper-note">Загружаем участников...</p> : null}

          {!isMembersLoading && displayedMembers.length === 0 ? (
            <p className="helper-note">В этом проекте пока нет участников для отображения.</p>
          ) : null}

          {!isMembersLoading &&
            displayedMembers.map((member) => {
              const isCurrentUser = member.user_id === currentUserId;
              const isUpdating = updatingMemberId === member.user_id;
              const isRemoving = removingMemberId === member.user_id;

              return (
                <article key={member.oid || member.user_id} className="project-member-card">
                  <div>
                    <span className="project-type-label">{member.isOwner ? 'Создатель' : getMemberStatusLabel(member.status)}</span>
                    <h3>{member.user_id}</h3>
                    <p>
                      {isCurrentUser ? 'Это вы' : `Пригласил: ${member.invited_by || '-'}`} · Создан:
                      {' '}
                      {formatDate(member.created_at)}
                    </p>
                  </div>

                  <div className="project-member-actions">
                    <label className="field-block">
                      <span>Роль</span>
                      <select
                        value={member.role}
                        onChange={(event) => handleChangeMemberRole(member.user_id, event.target.value)}
                        disabled={!canManageMembers || member.isOwner || isCurrentUser || isUpdating}
                      >
                        {roleOptions.map((role) => (
                          <option key={role.value} value={role.value}>
                            {role.label}
                          </option>
                        ))}
                      </select>
                    </label>

                    <button
                      type="button"
                      className="ghost-action-btn danger"
                      onClick={() => handleRemoveMember(member)}
                      disabled={!canManageMembers || member.isOwner || isCurrentUser || isRemoving}
                      title={getRoleLabel(member.role)}
                    >
                      {isRemoving ? 'Удаляем...' : 'Удалить'}
                    </button>
                  </div>
                </article>
              );
            })}
        </div>
      </section>
    </section>
  );
};

export default ProjectListPage;
