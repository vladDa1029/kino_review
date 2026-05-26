import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { toast } from 'react-toastify';

import { listProjects } from '../services/api';
import { getAccessToken } from '../services/tokenStorage';
import { useAuth } from './useAuth';
import { ProjectContext } from './projectContextInstance';

const ACTIVE_PROJECT_STORAGE_KEY = 'kinoflow.activeProjectId';
const SEEN_PROJECT_IDS_STORAGE_KEY = 'kinoflow.seenProjectIds';

const getProjectId = (project) => project?.oid || project?.id || '';

export const ProjectProvider = ({ children }) => {
  const { token } = useAuth();
  const [projects, setProjects] = useState([]);
  const [newProjectIds, setNewProjectIds] = useState([]);
  const [activeProjectId, setActiveProjectIdState] = useState(() =>
    localStorage.getItem(ACTIVE_PROJECT_STORAGE_KEY) || '',
  );
  const [isProjectsLoading, setIsProjectsLoading] = useState(false);
  const includeArchivedRef = useRef(false);

  const refreshProjects = useCallback(async ({ includeArchived } = {}) => {
    const shouldIncludeArchived = includeArchived ?? includeArchivedRef.current;
    includeArchivedRef.current = shouldIncludeArchived;

    if (!getAccessToken()) {
      setProjects([]);
      setNewProjectIds([]);
      setActiveProjectIdState('');
      localStorage.removeItem(ACTIVE_PROJECT_STORAGE_KEY);
      localStorage.removeItem(SEEN_PROJECT_IDS_STORAGE_KEY);
      return [];
    }

    setIsProjectsLoading(true);

    try {
      const response = await listProjects({ includeArchived: shouldIncludeArchived });
      const nextProjects = Array.isArray(response?.items) ? response.items : [];
      const nextProjectIds = nextProjects.map(getProjectId).filter(Boolean);
      const storedSeenIds = (() => {
        try {
          return JSON.parse(localStorage.getItem(SEEN_PROJECT_IDS_STORAGE_KEY) || '[]');
        } catch {
          return [];
        }
      })();
      const seenIdSet = new Set(Array.isArray(storedSeenIds) ? storedSeenIds : []);
      const newlyVisibleIds = nextProjectIds.filter((projectId) => !seenIdSet.has(projectId));
      setProjects(nextProjects);
      setNewProjectIds((prev) => Array.from(new Set([...prev, ...newlyVisibleIds])));
      localStorage.setItem(SEEN_PROJECT_IDS_STORAGE_KEY, JSON.stringify(nextProjectIds));
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
    if (!token) {
      setProjects([]);
      setNewProjectIds([]);
      setActiveProjectIdState('');
      localStorage.removeItem(ACTIVE_PROJECT_STORAGE_KEY);
      localStorage.removeItem(SEEN_PROJECT_IDS_STORAGE_KEY);
      return;
    }

    refreshProjects();
  }, [refreshProjects, token]);

  useEffect(() => {
    if (!token) {
      return undefined;
    }

    const refreshVisibleProjects = () => {
      if (document.visibilityState === 'visible') {
        refreshProjects();
      }
    };

    const intervalId = window.setInterval(() => {
      if (document.visibilityState === 'visible') {
        refreshProjects();
      }
    }, 30000);

    window.addEventListener('focus', refreshVisibleProjects);
    document.addEventListener('visibilitychange', refreshVisibleProjects);

    return () => {
      window.clearInterval(intervalId);
      window.removeEventListener('focus', refreshVisibleProjects);
      document.removeEventListener('visibilitychange', refreshVisibleProjects);
    };
  }, [refreshProjects, token]);

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
    setNewProjectIds((prev) => prev.filter((item) => item !== projectId));

    if (projectId) {
      localStorage.setItem(ACTIVE_PROJECT_STORAGE_KEY, projectId);
    } else {
      localStorage.removeItem(ACTIVE_PROJECT_STORAGE_KEY);
    }
  }, []);

  const markProjectSeen = useCallback((projectId) => {
    if (!projectId) {
      return;
    }

    setNewProjectIds((prev) => prev.filter((item) => item !== projectId));
  }, []);

  const activeProject = useMemo(
    () => projects.find((project) => getProjectId(project) === activeProjectId) || null,
    [activeProjectId, projects],
  );

  const value = useMemo(
    () => ({
      projects,
      newProjectIds,
      activeProject,
      activeProjectId,
      isProjectsLoading,
      refreshProjects,
      markProjectSeen,
      setActiveProjectId,
    }),
    [
      newProjectIds,
      activeProject,
      activeProjectId,
      isProjectsLoading,
      markProjectSeen,
      projects,
      refreshProjects,
      setActiveProjectId,
    ],
  );

  return <ProjectContext.Provider value={value}>{children}</ProjectContext.Provider>;
};
