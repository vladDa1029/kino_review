import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-toastify';

import {
  archiveProject,
  changeProjectMemberRole,
  approveShift,
  createProject,
  createShift,
  declineShiftParticipant,
  confirmShiftParticipant,
  inviteProjectMember,
  inviteShiftParticipant,
  listProjectMembers,
  removeProjectMember,
  updateProject,
} from '../services/api';
import { useAuth } from '../context/useAuth';
import { useProjectContext } from '../context/useProjectContext';
import { formatDateTime, toIsoDateTime } from '../utils/dateTime';

const initialForm = {
  title: '',
  description: '',
};

const initialMemberForm = {
  inviteMode: 'userId',
  userId: '',
  email: '',
  role: 'ACTOR',
};

const initialShiftForm = {
  title: '',
  description: '',
  startTime: '',
  endTime: '',
};

const initialParticipantForm = {
  shiftId: '',
  userId: '',
  role: 'ACTOR',
  timeFrom: '',
  timeTo: '',
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
  10: 'Активен',
  20: 'Архивирован',
};

const PROJECT_STATUS_ACTIVE = 10;
const PROJECT_STATUS_ARCHIVED = 20;

const memberStatusLabels = {
  0: 'Ожидает приглашения',
  10: 'Активен',
  20: 'Удален',
};

const PROJECT_MEMBER_STATUS_ACTIVE = 10;

const participantStatusLabels = {
  0: 'Ожидает',
  10: 'Подтвержден',
  20: 'Зарезервирован',
  30: 'Отклонен',
  40: 'Отменен',
  50: 'Ошибка резерва',
};

const shiftStatusLabels = {
  0: 'Черновик',
  10: 'На подтверждении',
  20: 'Подтверждена',
  30: 'Отменена',
  40: 'Завершена',
};

const formatDate = (value) => {
  if (!value) {
    return 'Нет даты';
  }

  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 'Нет даты' : date.toLocaleDateString('ru-RU');
};

const getProjectId = (project) => project.oid || project.id;

const getStatusLabel = (status) => statusLabels[Number(status)] || `Статус ${status}`;
const isProjectActive = (project) => Number(project?.status) === PROJECT_STATUS_ACTIVE;
const isProjectArchived = (project) => Number(project?.status) === PROJECT_STATUS_ARCHIVED;

const getRoleLabel = (role) => roleOptions.find((option) => option.value === role)?.label || role;

const getMemberStatusLabel = (status) => memberStatusLabels[Number(status)] || `Статус ${status}`;
const getParticipantStatusLabel = (status) => participantStatusLabels[Number(status)] || `Статус ${status}`;
const getShiftStatusLabel = (status) => shiftStatusLabels[Number(status)] || `Статус ${status}`;

const PlusIcon = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true">
    <path d="M12 5v14" />
    <path d="M5 12h14" />
  </svg>
);

const EditIcon = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true">
    <path d="M4 20l4.5-1 9-9a2 2 0 0 0-4-4l-9 9L4 20Z" />
    <path d="M13 7l4 4" />
  </svg>
);

const ArchiveIcon = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true">
    <path d="M4 7h16v4H4z" />
    <path d="M6 11h12v8H6z" />
    <path d="M10 15h4" />
  </svg>
);

const RefreshIcon = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true">
    <path d="M20 12a8 8 0 1 1-2.3-5.7" />
    <path d="M20 4v6h-6" />
  </svg>
);

const FolderIcon = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true">
    <path d="M3 7h6l2 2h10v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7Z" />
    <path d="M3 7a2 2 0 0 1 2-2h5l2 2" />
  </svg>
);

const FilmIcon = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true">
    <rect x="4" y="5" width="16" height="14" rx="2" />
    <path d="M8.5 9l6 3-6 3z" />
    <path d="M8 5v14" />
    <path d="M16 5v14" />
  </svg>
);

const BoxArchiveIcon = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true">
    <path d="M4 7h16v4H4z" />
    <path d="M6 11h12v8H6z" />
    <path d="M10 15h4" />
  </svg>
);

const UsersIcon = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true">
    <path d="M8 11a3 3 0 1 1 0-6 3 3 0 0 1 0 6Z" />
    <path d="M16 10a2.5 2.5 0 1 1 0-5 2.5 2.5 0 0 1 0 5Z" />
    <path d="M3.5 19a4.5 4.5 0 0 1 9 0" />
    <path d="M13 19a4 4 0 0 1 7 0" />
  </svg>
);

const TrashIcon = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true">
    <path d="M4 7h16" />
    <path d="M10 11v6" />
    <path d="M14 11v6" />
    <path d="M6 7l1 12h10l1-12" />
    <path d="M9 7V4h6v3" />
  </svg>
);

const CalendarSmallIcon = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true">
    <path d="M7 3v3" />
    <path d="M17 3v3" />
    <path d="M4 9h16" />
    <rect x="4" y="5" width="16" height="15" rx="2" />
  </svg>
);

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

const isEmail = (value) =>
  /^[^\s@]+@[^\s@]+\.[^\s@]+$/i.test(value);

const formatShortId = (value = '') => {
  const id = String(value);
  return id.length > 13 ? `${id.slice(0, 8)}...${id.slice(-4)}` : id;
};

const getMemberInitials = (member) => {
  const source = member.displayName || member.user_id || '';
  const parts = source.trim().split(/\s+/).filter(Boolean);

  if (parts.length >= 2) {
    return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
  }

  return source.slice(0, 2).toUpperCase() || 'U';
};

const ProjectListPage = () => {
  const navigate = useNavigate();
  const { userData } = useAuth();
  const {
    projects,
    newProjectIds,
    activeProjectId,
    isProjectsLoading,
    markProjectSeen,
    refreshProjects,
    setActiveProjectId,
  } = useProjectContext();
  const [form, setForm] = useState(initialForm);
  const [editingId, setEditingId] = useState(null);
  const [includeArchived, setIncludeArchived] = useState(false);
  const [projectView, setProjectView] = useState('active');
  const projectSort = 'updated';
  const [submitting, setSubmitting] = useState(false);
  const [archivingId, setArchivingId] = useState(null);
  const [memberProjectId, setMemberProjectId] = useState('');
  const [members, setMembers] = useState([]);
  const [memberForm, setMemberForm] = useState(initialMemberForm);
  const [includeInactiveMembers, setIncludeInactiveMembers] = useState(false);
  const [isMembersLoading, setIsMembersLoading] = useState(false);
  const [isInvitingMember, setIsInvitingMember] = useState(false);
  const [memberInviteError, setMemberInviteError] = useState('');
  const [updatingMemberId, setUpdatingMemberId] = useState(null);
  const [removingMemberId, setRemovingMemberId] = useState(null);
  const [shiftForm, setShiftForm] = useState(initialShiftForm);
  const [projectShifts, setProjectShifts] = useState({});
  const [participantForm, setParticipantForm] = useState(initialParticipantForm);
  const [shiftParticipants, setShiftParticipants] = useState({});
  const [isCreatingShift, setIsCreatingShift] = useState(false);
  const [approvingShiftId, setApprovingShiftId] = useState(null);
  const [isInvitingParticipant, setIsInvitingParticipant] = useState(false);
  const [participantActionId, setParticipantActionId] = useState(null);

  const loadProjects = useCallback(async () => {
    await refreshProjects({ includeArchived });
  }, [includeArchived, refreshProjects]);

  useEffect(() => {
    loadProjects();
  }, [loadProjects]);

  useEffect(() => {
    setIncludeArchived(projectView !== 'active');
  }, [projectView]);

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

  useEffect(() => {
    setParticipantForm((prev) => {
      const availableShiftIds = new Set((projectShifts[memberProjectId] || []).map((shift) => shift.oid));
      const nextShiftId = availableShiftIds.has(prev.shiftId)
        ? prev.shiftId
        : (projectShifts[memberProjectId] || [])[0]?.oid || '';

      if (prev.shiftId === nextShiftId) {
        return prev;
      }

      return { ...prev, shiftId: nextShiftId };
    });
  }, [memberProjectId, projectShifts]);

  const counters = useMemo(
    () => ({
      total: projects.length,
      active: projects.filter(isProjectActive).length,
      archived: projects.filter(isProjectArchived).length,
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
        status: PROJECT_MEMBER_STATUS_ACTIVE,
        invited_by: memberProject.owner_id,
        created_at: memberProject.created_at,
        isOwner: true,
      },
      ...members,
    ];
  }, [memberProject, members]);
  const selectedProjectShifts = useMemo(
    () => projectShifts[memberProjectId] || [],
    [memberProjectId, projectShifts],
  );
  const selectedShiftParticipants = useMemo(
    () => shiftParticipants[participantForm.shiftId] || [],
    [participantForm.shiftId, shiftParticipants],
  );
  const availableParticipantMembers = useMemo(
    () => displayedMembers.filter((member) => !member.isOwner || member.user_id),
    [displayedMembers],
  );
  const visibleMembers = useMemo(
    () =>
      displayedMembers.map((member) => {
        return {
          ...member,
          displayName: member.user_id,
          displayEmail: '',
          isPendingAcceptance: !member.isOwner && Number(member.status) !== PROJECT_MEMBER_STATUS_ACTIVE,
        };
      }),
    [displayedMembers],
  );
  const filteredProjects = useMemo(() => {
    const nextProjects = projects.filter((project) => {
      const matchesView =
        projectView === 'all'
          ? true
          : projectView === 'archived'
            ? isProjectArchived(project)
            : isProjectActive(project);

      if (!matchesView) {
        return false;
      }

      return true;
    });

    nextProjects.sort((left, right) => {
      if (projectSort === 'title') {
        return String(left.title || '').localeCompare(String(right.title || ''), 'ru');
      }

      if (projectSort === 'created') {
        return new Date(right.created_at || 0) - new Date(left.created_at || 0);
      }

      return new Date(right.updated_at || 0) - new Date(left.updated_at || 0);
    });

    return nextProjects;
  }, [projectSort, projectView, projects]);
  const featuredProject = filteredProjects[0] || null;
  const secondaryProjects = filteredProjects.slice(1);

  useEffect(() => {
    if (!participantForm.userId) {
      return;
    }

    const selectedMember = displayedMembers.find((member) => member.user_id === participantForm.userId);
    if (!selectedMember || selectedMember.role === participantForm.role) {
      return;
    }

    setParticipantForm((prev) => ({ ...prev, role: selectedMember.role }));
  }, [displayedMembers, participantForm.role, participantForm.userId]);

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

    if (isProjectArchived(project)) {
      toast.info('Проект уже находится в архиве');
      return;
    }

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

    markProjectSeen(projectId);
    setActiveProjectId(projectId);
    navigate('/projects');
  };

  const handleMemberFormChange = (event) => {
    const { name, value } = event.target;
    setMemberInviteError('');
    setMemberForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleShiftFormChange = (event) => {
    const { name, value } = event.target;
    setShiftForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleParticipantFormChange = (event) => {
    const { name, value } = event.target;
    setParticipantForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleSelectShiftForParticipants = (shiftId) => {
    setParticipantForm((prev) => ({
      ...prev,
      shiftId,
      timeFrom: prev.timeFrom || '',
      timeTo: prev.timeTo || '',
    }));
  };

  const handleCreateShift = async (event) => {
    event.preventDefault();

    const title = shiftForm.title.trim();
    const startTime = toIsoDateTime(shiftForm.startTime);
    const endTime = toIsoDateTime(shiftForm.endTime);

    if (!memberProjectId) {
      toast.error('Сначала выберите проект');
      return;
    }

    if (!canManageMembers) {
      toast.error('У вас нет прав создавать смены в этом проекте');
      return;
    }

    if (!title || !startTime || !endTime) {
      toast.error('Заполните название смены, дату начала и дату окончания');
      return;
    }

    if (new Date(startTime) >= new Date(endTime)) {
      toast.error('Время окончания смены должно быть позже времени начала');
      return;
    }

    setIsCreatingShift(true);

    try {
      const createdShift = await createShift(memberProjectId, {
        title,
        description: shiftForm.description.trim(),
        start_time: startTime,
        end_time: endTime,
      });

      setProjectShifts((prev) => ({
        ...prev,
        [memberProjectId]: [createdShift, ...(prev[memberProjectId] || [])],
      }));
      setParticipantForm((prev) => ({
        ...prev,
        shiftId: createdShift.oid,
        timeFrom: shiftForm.startTime,
        timeTo: shiftForm.endTime,
      }));
      setShiftForm(initialShiftForm);
      toast.success('Смена создана');
    } catch (error) {
      toast.error(error?.message || 'Не удалось создать смену');
    } finally {
      setIsCreatingShift(false);
    }
  };

  const handleApproveShift = async (shiftId) => {
    if (!shiftId) {
      return;
    }

    if (!canManageMembers) {
      toast.error('У вас нет прав подтверждать смены в этом проекте');
      return;
    }

    setApprovingShiftId(shiftId);

    try {
      const updatedShift = await approveShift(shiftId);
      setProjectShifts((prev) => ({
        ...prev,
        [memberProjectId]: (prev[memberProjectId] || []).map((shift) =>
          shift.oid === shiftId ? updatedShift : shift,
        ),
      }));
      toast.success('Смена подтверждена');
    } catch (error) {
      toast.error(error?.message || 'Не удалось подтвердить смену');
    } finally {
      setApprovingShiftId(null);
    }
  };

  const handleInviteMember = async (event) => {
    event.preventDefault();

    const inviteMode = memberForm.inviteMode;
    const userId = memberForm.userId.trim();
    const email = memberForm.email.trim().toLowerCase();
    const inviteValue = inviteMode === 'email' ? email : userId;
    const projectStillExists = projects.some((project) => getProjectId(project) === memberProjectId);
    setMemberInviteError('');

    if (!memberProjectId || !inviteValue) {
      const message = inviteMode === 'email'
        ? 'Выберите проект и укажите email для приглашения'
        : 'Выберите проект и укажите ID пользователя для приглашения';
      setMemberInviteError(message);
      toast.error(message);
      return;
    }

    if (!projectStillExists) {
      const message = 'Выбранный проект больше недоступен. Обновите список проектов и попробуйте снова.';
      setMemberInviteError(message);
      toast.error(message);
      await loadProjects();
      return;
    }

    if (inviteMode === 'email') {
      if (!isEmail(email)) {
        const message = 'Введите корректный email для приглашения';
        setMemberInviteError(message);
        toast.error(message);
        return;
      }
    } else if (!isUuid(userId)) {
      const message = 'user_id должен быть UUID в формате xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx';
      setMemberInviteError(message);
      toast.error(message);
      return;
    }

    if (!canManageMembers) {
      const message = 'У вас нет прав приглашать участников в этот проект';
      setMemberInviteError(message);
      toast.error(message);
      return;
    }

    if (inviteMode === 'email') {
      if (visibleMembers.some((member) => member.displayEmail && member.displayEmail.toLowerCase() === email)) {
        const message = 'Пользователь с этим email уже есть в проекте';
        setMemberInviteError(message);
        toast.error(message);
        return;
      }
    } else if (displayedMembers.some((member) => member.user_id === userId)) {
      const message = 'Этот пользователь уже добавлен в проект';
      setMemberInviteError(message);
      toast.error(message);
      return;
    }

    setIsInvitingMember(true);

    try {
      await inviteProjectMember(memberProjectId, {
        role: memberForm.role,
        ...(inviteMode === 'email' ? { email } : { user_id: userId }),
      });
      if (inviteMode === 'email') {
        setIncludeInactiveMembers(true);
      }
      const response = await listProjectMembers(memberProjectId, {
        includeInactive: inviteMode === 'email' ? true : includeInactiveMembers,
      });
      setMembers(Array.isArray(response?.items) ? response.items : []);
      toast.success(
        inviteMode === 'email'
          ? 'Приглашение отправлено на email. Пользователь должен принять его по ссылке в письме.'
          : 'Пользователь сразу добавлен в проект.',
      );
      setMemberForm(initialMemberForm);
      setMemberInviteError('');
    } catch (error) {
      if (error?.status === 404) {
        const message = 'Проект не найден или больше недоступен для приглашения участников. Обновите список проектов.';
        setMemberInviteError(message);
        toast.error(message);
        await loadProjects();
        return;
      }

      const message = error?.message || 'Не удалось пригласить участника';
      setMemberInviteError(message);
      toast.error(message);
    } finally {
      setIsInvitingMember(false);
    }
  };
  const handleInviteParticipant = async (event) => {
    event.preventDefault();

    const userId = participantForm.userId.trim();
    const timeFrom = toIsoDateTime(participantForm.timeFrom);
    const timeTo = toIsoDateTime(participantForm.timeTo);

    if (!participantForm.shiftId || !userId || !timeFrom || !timeTo) {
      toast.error('Выберите смену, участника и укажите время участия');
      return;
    }

    if (!canManageMembers) {
      toast.error('У вас нет прав приглашать участников в смену');
      return;
    }

    if (new Date(timeFrom) >= new Date(timeTo)) {
      toast.error('Время окончания участия должно быть позже времени начала');
      return;
    }

    setIsInvitingParticipant(true);

    try {
      const participant = await inviteShiftParticipant(participantForm.shiftId, {
        user_id: userId,
        role: participantForm.role,
        time_from: timeFrom,
        time_to: timeTo,
      });

      setShiftParticipants((prev) => ({
        ...prev,
        [participantForm.shiftId]: [participant, ...(prev[participantForm.shiftId] || [])],
      }));
      setParticipantForm((prev) => ({
        ...initialParticipantForm,
        shiftId: prev.shiftId,
        timeFrom: prev.timeFrom,
        timeTo: prev.timeTo,
      }));
      toast.success('Участник приглашен в смену');
    } catch (error) {
      toast.error(error?.message || 'Не удалось пригласить участника в смену');
    } finally {
      setIsInvitingParticipant(false);
    }
  };

  const updateParticipantInState = (shiftId, participantId, nextParticipant) => {
    setShiftParticipants((prev) => ({
      ...prev,
      [shiftId]: (prev[shiftId] || []).map((participant) =>
        participant.oid === participantId ? nextParticipant : participant,
      ),
    }));
  };

  const handleConfirmParticipant = async (shiftId, participantId) => {
    if (!participantId) {
      return;
    }

    setParticipantActionId(participantId);

    try {
      const updatedParticipant = await confirmShiftParticipant(participantId);
      updateParticipantInState(shiftId, participantId, updatedParticipant);
      toast.success('Участие подтверждено');
    } catch (error) {
      toast.error(error?.message || 'Не удалось подтвердить участие');
    } finally {
      setParticipantActionId(null);
    }
  };

  const handleDeclineParticipant = async (shiftId, participantId) => {
    if (!participantId) {
      return;
    }

    setParticipantActionId(participantId);

    try {
      const updatedParticipant = await declineShiftParticipant(participantId);
      updateParticipantInState(shiftId, participantId, updatedParticipant);
      toast.success('Участие отклонено');
    } catch (error) {
      toast.error(error?.message || 'Не удалось отклонить участие');
    } finally {
      setParticipantActionId(null);
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
            <span className="project-stat-icon"><FolderIcon /></span>
            <div className="project-stat-copy">
              <span>Всего</span>
              <strong>{counters.total}</strong>
              <small>проект</small>
            </div>
          </div>
          <div>
            <span className="project-stat-icon"><FilmIcon /></span>
            <div className="project-stat-copy">
              <span>Активные</span>
              <strong>{counters.active}</strong>
              <small>проект</small>
            </div>
          </div>
          <div>
            <span className="project-stat-icon"><BoxArchiveIcon /></span>
            <div className="project-stat-copy">
              <span>Архив</span>
              <strong>{counters.archived}</strong>
              <small>проект</small>
            </div>
          </div>
        </div>
      </div>

      <div className="dashboard-panel project-list-commandbar">
        <div className="project-view-switcher" role="tablist" aria-label="Фильтр проектов">
          {[
            { key: 'all', label: 'Все' },
            { key: 'active', label: 'Активные' },
            { key: 'archived', label: 'Архив' },
          ].map((option) => (
            <button
              key={option.key}
              type="button"
              className={`project-view-tab ${projectView === option.key ? 'is-active' : ''}`}
              onClick={() => setProjectView(option.key)}
            >
              {option.label}
            </button>
          ))}
        </div>

        <button
          type="button"
          className="project-toolbar-create-btn"
          onClick={() => {
            handleResetForm();
            document.getElementById('project-create-form')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
          }}
        >
          <PlusIcon />
          <span>Новый проект</span>
        </button>
      </div>

      {newProjectIds.length > 0 ? (
        <p className="helper-note">У вас есть новое приглашение в проект. Оно отмечено в списке ниже.</p>
      ) : null}

      <div className="project-list-layout">
        <section className="dashboard-panel project-create-panel">
          <div className="section-heading">
            <h2>{isEditing ? 'Редактировать проект' : 'Новый проект'}</h2>
            <p>Заполните поля, которые принимает сервис проектов.</p>
          </div>

          <form id="project-create-form" className="stacked-form" onSubmit={handleSubmit}>
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
          <div className="dashboard-panel project-list-toolbar project-list-toolbar-rich">
            <div className="project-list-toolbar-title">
              <FilmIcon />
              <div>
                <h2>Список проектов</h2>
              </div>
            </div>
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

          {!isProjectsLoading && featuredProject && (
            <article
              key={getProjectId(featuredProject)}
              className={`dashboard-panel project-card-item project-card-featured${activeProjectId === getProjectId(featuredProject) ? ' is-active-project' : ''}`}
            >
              <div className="project-card-thumb project-card-thumb-featured" aria-hidden="true" />
              <div className="project-card-main">
                <div className="project-card-meta">
                  <span className="project-type-label">{getStatusLabel(featuredProject.status)}</span>
                  <span className="project-type-label">
                    {currentUserId && featuredProject.owner_id === currentUserId ? 'Владелец' : 'Участник'}
                  </span>
                  {newProjectIds.includes(getProjectId(featuredProject)) ? (
                    <span className="project-type-label invitation">Новое приглашение</span>
                  ) : null}
                  {activeProjectId === getProjectId(featuredProject) ? (
                    <span className="project-type-label active">Открыт сейчас</span>
                  ) : null}
                  <span>Создан: {formatDate(featuredProject.created_at)}</span>
                </div>
                <h2>{featuredProject.title}</h2>
                <p className="project-card-description">
                  {featuredProject.description || 'Описание не указано'}
                </p>
                <p>Обновлен: {formatDate(featuredProject.updated_at)}</p>
              </div>

              <div className="project-card-actions">
                <button
                  type="button"
                  className="profile-save-btn compact"
                  onClick={() => handleOpenProject(featuredProject)}
                >
                  {activeProjectId === getProjectId(featuredProject) ? 'Открыт' : 'Открыть'}
                </button>
                {!isProjectArchived(featuredProject) ? (
                  <>
                    <button
                      type="button"
                      className="ghost-action-btn project-inline-action"
                      onClick={() => handleEditProject(featuredProject)}
                    >
                      <EditIcon />
                      <span>Изменить</span>
                    </button>
                    <button
                      type="button"
                      className="ghost-action-btn danger project-inline-action"
                      onClick={() => handleArchiveProject(featuredProject)}
                      disabled={archivingId === getProjectId(featuredProject)}
                    >
                      <ArchiveIcon />
                      <span>{archivingId === getProjectId(featuredProject) ? 'Архивируем...' : 'В архив'}</span>
                    </button>
                  </>
                ) : null}
              </div>
            </article>
          )}

          {!isProjectsLoading &&
            secondaryProjects.map((project) => {
              const projectId = getProjectId(project);
              const isArchiving = archivingId === projectId;
              const isActiveProject = activeProjectId === projectId;
              const isOwner = currentUserId && project.owner_id === currentUserId;
              const isArchived = isProjectArchived(project);

              return (
                <article
                  key={projectId}
                  className={`dashboard-panel project-card-item project-card-compact${isActiveProject ? ' is-active-project' : ''}`}
                >
                  <div className="project-card-thumb project-card-thumb-compact" aria-hidden="true" />
                  <div className="project-card-main">
                    <div className="project-card-meta">
                      <span className="project-type-label">{getStatusLabel(project.status)}</span>
                      <span className="project-type-label">{isOwner ? 'Владелец' : 'Участник'}</span>
                      {newProjectIds.includes(projectId) ? (
                        <span className="project-type-label invitation">Новое приглашение</span>
                      ) : null}
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
                    {!isArchived ? (
                      <>
                        <button
                          type="button"
                          className="ghost-action-btn project-inline-action"
                          onClick={() => handleEditProject(project)}
                        >
                          <EditIcon />
                          <span>Изменить</span>
                        </button>
                        <button
                          type="button"
                          className="ghost-action-btn danger project-inline-action"
                          onClick={() => handleArchiveProject(project)}
                          disabled={isArchiving}
                        >
                          <ArchiveIcon />
                          <span>{isArchiving ? 'Архивируем...' : 'В архив'}</span>
                        </button>
                      </>
                    ) : null}
                  </div>
                </article>
              );
            })}
        </section>
      </div>

      {false ? (
      <section className="dashboard-panel project-shifts-panel">
        <div className="section-heading project-members-heading">
          <div>
            <span className="projects-panel-eyebrow">Смены</span>
            <h2>{memberProject ? `Смены проекта "${memberProject.title}"` : 'Выберите проект'}</h2>
          </div>
          <p>Создайте смену, затем пригласите участников с ролью и временным окном работы.</p>
        </div>

        <form className="project-shift-form" onSubmit={handleCreateShift}>
          <label className="field-block">
            <span>Название смены</span>
            <input
              name="title"
              value={shiftForm.title}
              onChange={handleShiftFormChange}
              placeholder="Смена первого съемочного дня"
              disabled={!memberProjectId || isCreatingShift}
              
            />
          </label>

          <label className="field-block">
            <span>Описание</span>
            <input
              name="description"
              value={shiftForm.description}
              onChange={handleShiftFormChange}
              placeholder="Коротко о задачах смены"
              disabled={!memberProjectId || isCreatingShift}
            />
          </label>

          <label className="field-block">
            <span>Начало</span>
            <input
              name="startTime"
              type="datetime-local"
              value={shiftForm.startTime}
              onChange={handleShiftFormChange}
              disabled={!memberProjectId || isCreatingShift}
            />
          </label>

          <label className="field-block">
            <span>Окончание</span>
            <input
              name="endTime"
              type="datetime-local"
              value={shiftForm.endTime}
              onChange={handleShiftFormChange}
              disabled={!memberProjectId || isCreatingShift}
            />
          </label>

          <button
            type="submit"
            className="profile-save-btn compact"
            disabled={!memberProjectId || !canManageMembers || isCreatingShift}
          >
            {isCreatingShift ? 'Создаем...' : 'Создать смену'}
          </button>
        </form>

        <div className="project-shifts-list">
          {selectedProjectShifts.length === 0 ? (
            <p className="helper-note">Смены появятся здесь после создания на этой странице.</p>
          ) : (
            selectedProjectShifts.map((shift) => {
              const isSelectedShift = participantForm.shiftId === shift.oid;
              const isApproving = approvingShiftId === shift.oid;
              return (
                <article
                  key={shift.oid}
                  className={`project-shift-card${isSelectedShift ? ' is-active-project' : ''}`}
                >
                  <div>
                    <div className="project-card-meta">
                      <span className="project-type-label">{getShiftStatusLabel(shift.status)}</span>
                      <span>Создана: {formatDate(shift.created_at)}</span>
                    </div>
                    <h3>{shift.title}</h3>
                    <p>{shift.description || 'Описание не указано'}</p>
                    <p>{formatDateTime(shift.start_time)} - {formatDateTime(shift.end_time)}</p>
                  </div>

                  <div className="project-shift-actions">
                    <button
                      type="button"
                      className="ghost-action-btn"
                      onClick={() => handleSelectShiftForParticipants(shift.oid)}
                    >
                      {isSelectedShift ? 'Выбрана' : 'Выбрать'}
                    </button>
                    <button
                      type="button"
                      className="profile-save-btn compact"
                      onClick={() => handleApproveShift(shift.oid)}
                      disabled={!canManageMembers || isApproving}
                    >
                      {isApproving ? 'Подтверждаем...' : 'Подтвердить смену'}
                    </button>
                  </div>
                </article>
              );
            })
          )}
        </div>

        <form className="project-participant-form" onSubmit={handleInviteParticipant}>
          <label className="field-block">
            <span>Смена</span>
            <select
              name="shiftId"
              value={participantForm.shiftId}
              onChange={handleParticipantFormChange}
              disabled={selectedProjectShifts.length === 0 || !canManageMembers}
            >
              {selectedProjectShifts.length === 0 ? (
                <option value="">Нет смен</option>
              ) : (
                selectedProjectShifts.map((shift) => (
                  <option key={shift.oid} value={shift.oid}>
                    {shift.title}
                  </option>
                ))
              )}
            </select>
          </label>

          <label className="field-block">
            <span>Участник</span>
            <select
              name="userId"
              value={participantForm.userId}
              onChange={handleParticipantFormChange}
              disabled={availableParticipantMembers.length === 0 || !canManageMembers}
            >
              <option value="">Выберите участника проекта</option>
              {availableParticipantMembers.map((member) => (
                <option key={member.user_id} value={member.user_id}>
                  {member.user_id} - {getRoleLabel(member.role)}
                </option>
              ))}
            </select>
          </label>

          <label className="field-block">
            <span>Роль в смене</span>
            <select
              name="role"
              value={participantForm.role}
              onChange={handleParticipantFormChange}
            >
              {roleOptions.map((role) => (
                <option key={role.value} value={role.value}>
                  {role.label}
                </option>
              ))}
            </select>
          </label>

          <label className="field-block">
            <span>С</span>
            <input
              name="timeFrom"
              type="datetime-local"
              value={participantForm.timeFrom}
              onChange={handleParticipantFormChange}
            />
          </label>

          <label className="field-block">
            <span>До</span>
            <input
              name="timeTo"
              type="datetime-local"
              value={participantForm.timeTo}
              onChange={handleParticipantFormChange}
            />
          </label>

          <button
            type="submit"
            className="profile-save-btn compact"
            disabled={!participantForm.shiftId || !canManageMembers || isInvitingParticipant}
          >
            {isInvitingParticipant ? 'Приглашаем...' : 'Пригласить в смену'}
          </button>
        </form>

        <div className="project-participants-list">
          {!participantForm.shiftId ? (
            <p className="helper-note">Выберите смену, чтобы увидеть приглашенных участников.</p>
          ) : selectedShiftParticipants.length === 0 ? (
            <p className="helper-note">Для этой смены пока нет приглашенных участников.</p>
          ) : (
            selectedShiftParticipants.map((participant) => {
              const isProcessing = participantActionId === participant.oid;
              return (
                <article key={participant.oid} className="project-member-card">
                  <div>
                    <span className="project-type-label">{getParticipantStatusLabel(participant.status)}</span>
                    <h3>{participant.user_id}</h3>
                    <p>{getRoleLabel(participant.role)}</p>
                    <p>{formatDateTime(participant.time_from)} - {formatDateTime(participant.time_to)}</p>
                  </div>

                  <div className="project-member-actions">
                    <button
                      type="button"
                      className="ghost-action-btn"
                      onClick={() => handleConfirmParticipant(participant.shift_id, participant.oid)}
                      disabled={!currentUserId || currentUserId !== participant.user_id || isProcessing}
                    >
                      {isProcessing ? '...' : 'Подтвердить'}
                    </button>
                    <button
                      type="button"
                      className="ghost-action-btn danger"
                      onClick={() => handleDeclineParticipant(participant.shift_id, participant.oid)}
                      disabled={!currentUserId || currentUserId !== participant.user_id || isProcessing}
                    >
                      {isProcessing ? '...' : 'Отклонить'}
                    </button>
                  </div>
                </article>
              );
            })
          )}
        </div>
      </section>
      ) : null}

      <section className="dashboard-panel project-members-panel">
        <div className="section-heading project-members-heading">
          <div>
            <span className="projects-panel-eyebrow">Участники</span>
            <h2>Участники</h2>
          </div>
          <p>
            Приглашайте пользователей по ID, назначайте роли и управляйте доступом.
          </p>
        </div>

        <div className="project-members-toolbar project-members-toolbar-refined">
          <div className="project-members-toolbar-icon" aria-hidden="true">
            <UsersIcon />
          </div>
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

          <div className="project-members-toolbar-side">
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
              <RefreshIcon />
              <span>Обновить</span>
            </button>
          </div>
        </div>

        {canManageMembers && memberInviteError ? <p className="helper-note">{memberInviteError}</p> : null}

        {canManageMembers ? (
        <>
        <form className="project-member-invite-form project-member-invite-form-refined" onSubmit={handleInviteMember}>
          <label className="field-block">
            <span>Пригласить по</span>
            <select
              name="inviteMode"
              value={memberForm.inviteMode}
              onChange={handleMemberFormChange}
              disabled={!canManageMembers}
            >
              <option value="userId">ID user</option>
              <option value="email">Email</option>
            </select>
          </label>

          <label className="field-block">
            <span>{memberForm.inviteMode === 'email' ? 'Email' : 'ID user'}</span>
            <input
              name={memberForm.inviteMode === 'email' ? 'email' : 'userId'}
              type={memberForm.inviteMode === 'email' ? 'email' : 'text'}
              value={memberForm.inviteMode === 'email' ? memberForm.email : memberForm.userId}
              onChange={handleMemberFormChange}
              disabled={!canManageMembers}
              placeholder={memberForm.inviteMode === 'email' ? 'Введите email пользователя' : 'Введите ID пользователя'}
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

        <p className="helper-note">
          {memberForm.inviteMode === 'email'
            ? 'После отправки приглашения участник получит письмо со ссылкой и сможет принять приглашение только после входа в систему.'
            : 'При приглашении по ID user пользователь добавляется в проект сразу, без ожидания ответа.'}
        </p>
        </>
        ) : null}

        <div className="project-members-table-shell">
          {isMembersLoading ? <p className="helper-note">Загружаем участников...</p> : null}

          {!isMembersLoading && visibleMembers.length === 0 ? (
            <p className="helper-note">В этом проекте пока нет участников для отображения.</p>
          ) : null}

          {!isMembersLoading && visibleMembers.length > 0 ? (
            <div className="project-members-table">
              <div className="project-members-table-head">
                <span>Пользователь</span>
                <span>Email</span>
                <span>Роль</span>
                <span>Добавлен</span>
                <span>Действия</span>
              </div>

              {visibleMembers.map((member) => {
                const isCurrentUser = member.user_id === currentUserId;
                const isUpdating = updatingMemberId === member.user_id;
                const isRemoving = removingMemberId === member.user_id;
                const shortUserId = formatShortId(member.user_id);

                return (
                  <div key={member.oid || member.user_id} className="project-members-table-row">
                    <div className="project-members-user-cell">
                      <div className="project-member-avatar" aria-hidden="true">
                        {getMemberInitials(member)}
                      </div>
                      <div className="project-member-copy">
                        <h3 title={member.user_id}>
                          {member.displayName && member.displayName !== member.user_id ? member.displayName : shortUserId}
                          {isCurrentUser ? <span className="project-member-self-badge">Это вы</span> : null}
                        </h3>
                        <p>{member.isOwner ? 'Создатель проекта' : 'Участник проекта'}</p>
                      </div>
                    </div>

                    <div className="project-members-status-cell">
                      <span>{member.displayEmail || 'Почта не указана'}</span>
                      {member.isPendingAcceptance ? (
                        <small className="project-members-pending-note">Ожидает принятия приглашения</small>
                      ) : null}
                    </div>

                    <div className="project-members-role-cell">
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
                    </div>

                    <div className="project-members-date-cell">
                      <CalendarSmallIcon />
                      <span>{formatDate(member.created_at)}</span>
                    </div>

                    <div className="project-members-actions-cell">
                      {member.isOwner || isCurrentUser ? (
                        <span className="project-members-action-placeholder">—</span>
                      ) : (
                        <button
                          type="button"
                          className="project-member-delete-btn"
                          onClick={() => handleRemoveMember(member)}
                          disabled={!canManageMembers || isRemoving}
                          title={getRoleLabel(member.role)}
                        >
                          <TrashIcon />
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          ) : null}
        </div>
      </section>
    </section>
  );
};

export default ProjectListPage;
