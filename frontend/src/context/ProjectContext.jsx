import { useCallback, useEffect, useMemo, useState } from 'react';
import { toast } from 'react-toastify';

import { listProjects } from '../services/api';
import { getAccessToken } from '../services/tokenStorage';
import { useAuth } from './useAuth';
import { ProjectContext } from './projectContextInstance';

const ACTIVE_PROJECT_STORAGE_KEY = 'kinoflow.activeProjectId';

const getProjectId = (project) => project?.oid || project?.id || '';

export const ProjectProvider = ({ children }) => {
  const { token } = useAuth();
  const [projects, setProjects] = useState([]);
  const [activeProjectId, setActiveProjectIdState] = useState(() =>
    localStorage.getItem(ACTIVE_PROJECT_STORAGE_KEY) || '',
  );
  const [isProjectsLoading, setIsProjectsLoading] = useState(false);

  const refreshProjects = useCallback(async ({ includeArchived = false } = {}) => {
    if (!getAccessToken()) {
      setProjects([]);
      setActiveProjectIdState('');
      localStorage.removeItem(ACTIVE_PROJECT_STORAGE_KEY);
      return [];
    }

    setIsProjectsLoading(true);

    try {
      const response = await listProjects({ includeArchived });
      const nextProjects = Array.isArray(response?.items) ? response.items : [];
      setProjects(nextProjects);
      return nextProjects;
    } catch (error) {
      setProjects([]);
      toast.error(error?.message || 'Не удалось загрузить проекты');
      return [];
    } finally {
      setIsProjectsLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshProjects();
  }, [refreshProjects]);

  useEffect(() => {
    if (!token || projects.length === 0) {
      if (!token) {
        setActiveProjectIdState('');
      }
      return;
    }

    const hasActiveProject = projects.some((project) => getProjectId(project) === activeProjectId);
    if (activeProjectId && !hasActiveProject) {
      setActiveProjectIdState('');
      localStorage.removeItem(ACTIVE_PROJECT_STORAGE_KEY);
    }
  }, [activeProjectId, projects, token]);

  const setActiveProjectId = useCallback((projectId) => {
    setActiveProjectIdState(projectId);

    if (projectId) {
      localStorage.setItem(ACTIVE_PROJECT_STORAGE_KEY, projectId);
    } else {
      localStorage.removeItem(ACTIVE_PROJECT_STORAGE_KEY);
    }
  }, []);

  const activeProject = useMemo(
    () => projects.find((project) => getProjectId(project) === activeProjectId) || null,
    [activeProjectId, projects],
  );

  const value = useMemo(
    () => ({
      projects,
      activeProject,
      activeProjectId,
      isProjectsLoading,
      refreshProjects,
      setActiveProjectId,
    }),
    [
      activeProject,
      activeProjectId,
      isProjectsLoading,
      projects,
      refreshProjects,
      setActiveProjectId,
    ],
  );

  return <ProjectContext.Provider value={value}>{children}</ProjectContext.Provider>;
};
