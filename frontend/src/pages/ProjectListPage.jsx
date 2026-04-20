import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-toastify';

import {
  archiveProject,
  createProject,
  updateProject,
} from '../services/api';
import { useAuth } from '../context/useAuth';
import { useProjectContext } from '../context/useProjectContext';

const initialForm = {
  title: '',
  description: '',
};

const statusLabels = {
  0: 'Активен',
  1: 'Архивирован',
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

const getCurrentUserId = (userData) =>
  userData?.user_id || userData?.sub || userData?.id || userData?.oid || '';

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

  const loadProjects = useCallback(async () => {
    await refreshProjects({ includeArchived });
  }, [includeArchived, refreshProjects]);

  useEffect(() => {
    loadProjects();
  }, [loadProjects]);

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
        await createProject({ title, description });
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
    </section>
  );
};

export default ProjectListPage;
