import { useCallback, useEffect, useMemo, useState } from 'react';
import { toast } from 'react-toastify';

import {
  approveShift,
  approveResourceRequest,
  archiveShiftReport,
  cancelResourceRequest,
  cancelShift,
  cancelShiftParticipant,
  completeShift,
  createShift,
  createShiftResourceRequest,
  declineShiftParticipant,
  confirmShiftParticipant,
  generateShiftReport,
  getDocumentDownloadUrl,
  getProjectUserResources,
  getShiftReportDownloadUrl,
  inviteShiftParticipant,
  listProjectMembers,
  listProjectShifts,
  listShiftDocuments,
  listShiftParticipants,
  listShiftReports,
  listShiftResourceRequests,
  rejectResourceRequest,
  uploadShiftDocument,
} from '../services/api';
import { useAuth } from '../context/useAuth';
import { useProjectContext } from '../context/useProjectContext';
import { formatDateTime, toDateTimeLocalValue, toIsoDateTime } from '../utils/dateTime';

const roleOptions = [
  { value: 'DIRECTOR', label: 'Режиссер' },
  { value: 'PROP_MASTER', label: 'Реквизитор' },
  { value: 'CAMERA', label: 'Камера' },
  { value: 'SOUND', label: 'Звук' },
  { value: 'LIGHT', label: 'Свет' },
  { value: 'ACTOR', label: 'Актер' },
];

const memberStatusLabels = {
  0: 'Ожидает приглашения',
  10: 'Активен',
  20: 'Удален',
};

const participantStatusLabels = {
  0: 'Ожидает',
  10: 'Подтвержден',
  20: 'Зарезервирован',
  30: 'Отклонен',
  40: 'Отменен',
  50: 'Ошибка резерва',
};

const resourceRequestStatusLabels = {
  0: 'Ожидает владельца',
  10: 'Одобрен',
  15: 'Резервируется',
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

const SHIFT_STATUS_APPROVED = 20;
const SHIFT_STATUS_CANCELLED = 30;
const SHIFT_STATUS_COMPLETED = 40;
const PROJECT_MEMBER_STATUS_ACTIVE = 10;

const PARTICIPANT_STATUS_DECLINED = 30;
const PARTICIPANT_STATUS_CANCELLED = 40;

const RESOURCE_REQUEST_STATUS_PENDING_OWNER = 0;
const RESOURCE_REQUEST_STATUS_APPROVED_OWNER = 10;

const canCancelParticipantStatus = (status) =>
  ![PARTICIPANT_STATUS_DECLINED, PARTICIPANT_STATUS_CANCELLED].includes(Number(status));

const canCancelResourceRequestStatus = (status) =>
  [RESOURCE_REQUEST_STATUS_PENDING_OWNER, RESOURCE_REQUEST_STATUS_APPROVED_OWNER].includes(
    Number(status),
  );

const canCompleteShiftStatus = (status) => Number(status) === SHIFT_STATUS_APPROVED;

const canCancelShiftStatus = (status) =>
  ![SHIFT_STATUS_CANCELLED, SHIFT_STATUS_COMPLETED].includes(Number(status));

const canApproveShiftStatus = (status) =>
  ![SHIFT_STATUS_APPROVED, SHIFT_STATUS_CANCELLED, SHIFT_STATUS_COMPLETED].includes(Number(status));

// Generating a report is only meaningful once a shift has been approved.
const canGenerateReportForShiftStatus = (status) =>
  [SHIFT_STATUS_APPROVED, SHIFT_STATUS_COMPLETED].includes(Number(status));

const REPORT_GENERATION_STATUS_READY = 40;
const REPORT_GENERATION_STATUS_FAILED = 50;
const REPORT_GENERATION_STATUS_ARCHIVED = 60;
const REPORT_ACTUALITY_STALE = 20;

const reportGenerationStatusLabels = {
  10: 'В очереди',
  20: 'Сбор данных',
  30: 'Формирование',
  40: 'Готов',
  50: 'Ошибка',
  60: 'В архиве',
};

const REPORT_IN_PROGRESS_STATUSES = [10, 20, 30];

const getReportGenerationStatusLabel = (status) =>
  reportGenerationStatusLabels[Number(status)] || `Статус ${status}`;

const isReportInProgress = (status) => REPORT_IN_PROGRESS_STATUSES.includes(Number(status));
const isReportReady = (status) => Number(status) === REPORT_GENERATION_STATUS_READY;
const canArchiveReportStatus = (status) =>
  !isReportInProgress(status) && Number(status) !== REPORT_GENERATION_STATUS_ARCHIVED;

// Roles allowed to create resource requests (mirrors the backend rule: any
// active crew member except a plain actor).
const RESOURCE_REQUEST_ROLES = ['DIRECTOR', 'PROP_MASTER', 'CAMERA', 'SOUND', 'LIGHT'];

const documentTypeOptions = [
  { value: 'PLAN', label: 'План' },
  { value: 'SCENARIO', label: 'Сценарий' },
];

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

const initialDocumentForm = {
  shiftId: '',
  file: null,
  docType: 'PLAN',
  title: '',
  description: '',
};

const initialResourceRequestForm = {
  shiftId: '',
  ownerUserId: '',
  resourceId: '',
  resourceType: '',
  timeFrom: '',
  timeTo: '',
};

const getProjectId = (project) => project?.oid || project?.id || '';

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

const getRoleLabel = (role) => roleOptions.find((option) => option.value === role)?.label || role;
const getMemberStatusLabel = (status) => memberStatusLabels[Number(status)] || `Статус ${status}`;
const getParticipantStatusLabel = (status) => participantStatusLabels[Number(status)] || `Статус ${status}`;
const getResourceRequestStatusLabel = (status) => resourceRequestStatusLabels[Number(status)] || `Статус ${status}`;
const getShiftStatusLabel = (status) => shiftStatusLabels[Number(status)] || `Статус ${status}`;
const getDocumentTypeLabel = (docType) => {
  const normalized = String(docType ?? '').toUpperCase();
  const labels = { PLAN: 'План', SCENARIO: 'Сценарий', REPORT: 'Отчет' };
  return labels[normalized] || (docType ?? 'Документ');
};
const formatShortId = (value = '') => {
  const id = String(value);
  return id.length > 13 ? `${id.slice(0, 8)}...${id.slice(-4)}` : id;
};

const getShiftTimeRange = (shift) => ({
  timeFrom: toDateTimeLocalValue(shift?.start_time),
  timeTo: toDateTimeLocalValue(shift?.end_time),
});

// datetime-local strings ("YYYY-MM-DDTHH:mm") sort lexically in chronological
// order, so a plain string comparison verifies a sub-interval sits inside the
// shift window without timezone conversions.
const isWithinDateTimeBounds = (from, to, bounds) =>
  !bounds?.timeFrom || !bounds?.timeTo || (from >= bounds.timeFrom && to <= bounds.timeTo);

const extractItems = (response) => {
  if (Array.isArray(response)) {
    return response;
  }
  return Array.isArray(response?.items) ? response.items : [];
};

const ShiftPlanningPage = () => {
  const { userData } = useAuth();
  const { projects, activeProjectId, refreshProjects } = useProjectContext();
  const [memberProjectId, setMemberProjectId] = useState('');
  const [members, setMembers] = useState([]);
  const [isMembersLoading, setIsMembersLoading] = useState(false);
  const [shiftForm, setShiftForm] = useState(initialShiftForm);
  const [participantForm, setParticipantForm] = useState(initialParticipantForm);
  const [documentForm, setDocumentForm] = useState(initialDocumentForm);
  const [resourceRequestForm, setResourceRequestForm] = useState(initialResourceRequestForm);
  const [projectShifts, setProjectShifts] = useState({});
  const [shiftParticipants, setShiftParticipants] = useState({});
  const [shiftDocuments, setShiftDocuments] = useState({});
  const [shiftResourceRequests, setShiftResourceRequests] = useState({});
  const [isShiftsLoading, setIsShiftsLoading] = useState(false);
  const [isParticipantsLoading, setIsParticipantsLoading] = useState(false);
  const [isDocumentsLoading, setIsDocumentsLoading] = useState(false);
  const [isResourceRequestsLoading, setIsResourceRequestsLoading] = useState(false);
  const [isCreatingShift, setIsCreatingShift] = useState(false);
  const [approvingShiftId, setApprovingShiftId] = useState(null);
  const [shiftActionId, setShiftActionId] = useState(null);
  const [isInvitingParticipant, setIsInvitingParticipant] = useState(false);
  const [participantActionId, setParticipantActionId] = useState(null);
  const [isUploadingDocument, setIsUploadingDocument] = useState(false);
  const [loadingDocumentId, setLoadingDocumentId] = useState(null);
  const [documentInputKey, setDocumentInputKey] = useState(0);
  const [ownerResources, setOwnerResources] = useState([]);
  const [isOwnerResourcesLoading, setIsOwnerResourcesLoading] = useState(false);
  const [isSubmittingResourceRequest, setIsSubmittingResourceRequest] = useState(false);
  const [resourceRequestActionId, setResourceRequestActionId] = useState(null);
  const [rejectReasonsById, setRejectReasonsById] = useState({});
  const [shiftReports, setShiftReports] = useState({});
  const [reportShiftId, setReportShiftId] = useState('');
  const [isReportsLoading, setIsReportsLoading] = useState(false);
  const [isGeneratingReport, setIsGeneratingReport] = useState(false);
  const [reportActionId, setReportActionId] = useState(null);

  const currentUserId = getCurrentUserId(userData);

  useEffect(() => {
    refreshProjects();
  }, [refreshProjects]);

  useEffect(() => {
    if (memberProjectId && projects.some((project) => getProjectId(project) === memberProjectId)) {
      return;
    }

    setMemberProjectId(activeProjectId || (projects[0] ? getProjectId(projects[0]) : ''));
  }, [activeProjectId, memberProjectId, projects]);

  const memberProject = useMemo(
    () => projects.find((project) => getProjectId(project) === memberProjectId) || null,
    [memberProjectId, projects],
  );

  const loadMembers = useCallback(async () => {
    if (!memberProjectId) {
      setMembers([]);
      return;
    }

    setIsMembersLoading(true);

    try {
      const response = await listProjectMembers(memberProjectId, {
        includeInactive: false,
      });
      setMembers(Array.isArray(response?.items) ? response.items : []);
    } catch (error) {
      setMembers([]);
      toast.error(error?.message || 'Не удалось загрузить участников проекта');
    } finally {
      setIsMembersLoading(false);
    }
  }, [memberProjectId]);

  useEffect(() => {
    loadMembers();
  }, [loadMembers]);

  const loadProjectShifts = useCallback(async (projectId) => {
    if (!projectId) {
      return;
    }

    setIsShiftsLoading(true);

    try {
      const response = await listProjectShifts(projectId);
      const items = extractItems(response);
      setProjectShifts((prev) => ({ ...prev, [projectId]: items }));
    } catch (error) {
      toast.error(error?.message || 'Не удалось загрузить смены проекта');
    } finally {
      setIsShiftsLoading(false);
    }
  }, []);

  const loadShiftParticipants = useCallback(async (shiftId) => {
    if (!shiftId) {
      return;
    }

    setIsParticipantsLoading(true);

    try {
      const response = await listShiftParticipants(shiftId);
      const items = extractItems(response);
      setShiftParticipants((prev) => ({ ...prev, [shiftId]: items }));
    } catch (error) {
      toast.error(error?.message || 'Не удалось загрузить участников смены');
    } finally {
      setIsParticipantsLoading(false);
    }
  }, []);

  const loadShiftDocuments = useCallback(async (shiftId) => {
    if (!shiftId) {
      return;
    }

    setIsDocumentsLoading(true);

    try {
      const response = await listShiftDocuments(shiftId);
      const items = extractItems(response);
      setShiftDocuments((prev) => ({ ...prev, [shiftId]: items }));
    } catch (error) {
      toast.error(error?.message || 'Не удалось загрузить документы смены');
    } finally {
      setIsDocumentsLoading(false);
    }
  }, []);

  const loadShiftResourceRequests = useCallback(async (shiftId) => {
    if (!shiftId) {
      return;
    }

    setIsResourceRequestsLoading(true);

    try {
      const response = await listShiftResourceRequests(shiftId);
      const items = extractItems(response);
      setShiftResourceRequests((prev) => ({ ...prev, [shiftId]: items }));
    } catch (error) {
      toast.error(error?.message || 'Не удалось загрузить запросы на ресурсы');
    } finally {
      setIsResourceRequestsLoading(false);
    }
  }, []);

  // Load shifts from the backend whenever the selected project changes so that
  // shift data stays durable across browsers, devices and incognito sessions.
  useEffect(() => {
    loadProjectShifts(memberProjectId);
  }, [memberProjectId, loadProjectShifts]);

  const currentProjectMember = useMemo(
    () => members.find((member) => member.user_id === currentUserId) || null,
    [currentUserId, members],
  );

  const isProjectOwner = Boolean(
    memberProject && currentUserId && memberProject.owner_id === currentUserId,
  );

  // Effective role of the current user in this project (the owner always acts
  // as a director). Used to render only the controls the role can actually use.
  const currentUserRole = isProjectOwner ? 'DIRECTOR' : currentProjectMember?.role || null;

  const canManageMembers = Boolean(
    memberProject && currentUserId && (isProjectOwner || currentUserRole === 'DIRECTOR'),
  );

  // Crew members (everyone except a plain actor) may create resource requests.
  const canRequestResources = Boolean(
    currentUserRole && RESOURCE_REQUEST_ROLES.includes(currentUserRole),
  );

  // Reports are restricted to directors on the backend; only fetch them when the
  // current user is allowed to manage the project to avoid noisy 403 toasts.
  // Declared after `canManageMembers` so the dependency is initialised in time.
  const loadShiftReports = useCallback(
    async (shiftId) => {
      if (!shiftId || !canManageMembers) {
        return;
      }

      setIsReportsLoading(true);

      try {
        const response = await listShiftReports(shiftId);
        const items = extractItems(response);
        setShiftReports((prev) => ({ ...prev, [shiftId]: items }));
      } catch (error) {
        toast.error(error?.message || 'Не удалось загрузить отчёты смены');
      } finally {
        setIsReportsLoading(false);
      }
    },
    [canManageMembers],
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

  const availableParticipantMembers = useMemo(
    () => displayedMembers.filter((member) => Boolean(member.user_id)),
    [displayedMembers],
  );

  const selectedProjectShifts = useMemo(
    () => projectShifts[memberProjectId] || [],
    [memberProjectId, projectShifts],
  );

  const selectedShiftParticipants = useMemo(
    () => shiftParticipants[participantForm.shiftId] || [],
    [participantForm.shiftId, shiftParticipants],
  );
  const selectedShiftDocuments = useMemo(
    () => shiftDocuments[documentForm.shiftId] || [],
    [documentForm.shiftId, shiftDocuments],
  );
  const selectedShiftResourceRequests = useMemo(
    () => shiftResourceRequests[resourceRequestForm.shiftId] || [],
    [resourceRequestForm.shiftId, shiftResourceRequests],
  );
  const selectedShiftReports = useMemo(
    () => shiftReports[reportShiftId] || [],
    [reportShiftId, shiftReports],
  );

  // datetime-local bounds (min/max) of the shift a sub-interval is being picked
  // for, so participant/resource windows stay inside the shift but may be shorter.
  const participantShiftBounds = useMemo(
    () => getShiftTimeRange(selectedProjectShifts.find((shift) => shift.oid === participantForm.shiftId)),
    [participantForm.shiftId, selectedProjectShifts],
  );
  const resourceShiftBounds = useMemo(
    () => getShiftTimeRange(selectedProjectShifts.find((shift) => shift.oid === resourceRequestForm.shiftId)),
    [resourceRequestForm.shiftId, selectedProjectShifts],
  );
  const reportShift = useMemo(
    () => selectedProjectShifts.find((shift) => shift.oid === reportShiftId) || null,
    [reportShiftId, selectedProjectShifts],
  );
  const shiftStats = useMemo(
    () => ({
      shifts: selectedProjectShifts.length,
      confirmed: selectedProjectShifts.filter((shift) => Number(shift.status) === SHIFT_STATUS_APPROVED).length,
      participants: Object.values(shiftParticipants)
        .flat()
        .filter((participant) => selectedProjectShifts.some((shift) => shift.oid === participant.shift_id)).length,
      requests: Object.values(shiftResourceRequests)
        .flat()
        .filter((request) => selectedProjectShifts.some((shift) => shift.oid === request.shift_id)).length,
    }),
    [selectedProjectShifts, shiftParticipants, shiftResourceRequests],
  );

  useEffect(() => {
    setParticipantForm((prev) => {
      const nextShiftId = selectedProjectShifts.some((shift) => shift.oid === prev.shiftId)
        ? prev.shiftId
        : selectedProjectShifts[0]?.oid || '';
      const selectedShift = selectedProjectShifts.find((shift) => shift.oid === nextShiftId);
      const shiftRange = getShiftTimeRange(selectedShift);

      if (
        nextShiftId === prev.shiftId &&
        shiftRange.timeFrom === prev.timeFrom &&
        shiftRange.timeTo === prev.timeTo
      ) {
        return prev;
      }

      return { ...prev, shiftId: nextShiftId, ...shiftRange };
    });
  }, [selectedProjectShifts]);

  useEffect(() => {
    setDocumentForm((prev) => {
      const nextShiftId = selectedProjectShifts.some((shift) => shift.oid === prev.shiftId)
        ? prev.shiftId
        : selectedProjectShifts[0]?.oid || '';

      if (nextShiftId === prev.shiftId) {
        return prev;
      }

      return { ...prev, shiftId: nextShiftId };
    });
  }, [selectedProjectShifts]);

  useEffect(() => {
    setResourceRequestForm((prev) => {
      const nextShiftId = selectedProjectShifts.some((shift) => shift.oid === prev.shiftId)
        ? prev.shiftId
        : selectedProjectShifts[0]?.oid || '';
      const selectedShift = selectedProjectShifts.find((shift) => shift.oid === nextShiftId);
      const shiftRange = getShiftTimeRange(selectedShift);

      if (
        nextShiftId === prev.shiftId &&
        shiftRange.timeFrom === prev.timeFrom &&
        shiftRange.timeTo === prev.timeTo
      ) {
        return prev;
      }

      return { ...prev, shiftId: nextShiftId, ...shiftRange };
    });
  }, [selectedProjectShifts]);

  // Load shift composition from the backend whenever the selected shift changes.
  // This keeps participants, documents and resource requests durable across
  // page refreshes, new browser sessions and devices.
  useEffect(() => {
    loadShiftParticipants(participantForm.shiftId);
  }, [participantForm.shiftId, loadShiftParticipants]);

  useEffect(() => {
    loadShiftDocuments(documentForm.shiftId);
  }, [documentForm.shiftId, loadShiftDocuments]);

  useEffect(() => {
    loadShiftResourceRequests(resourceRequestForm.shiftId);
  }, [resourceRequestForm.shiftId, loadShiftResourceRequests]);

  // Keep the report panel pointed at a valid shift of the current project.
  useEffect(() => {
    setReportShiftId((prev) => {
      if (selectedProjectShifts.some((shift) => shift.oid === prev)) {
        return prev;
      }
      return selectedProjectShifts[0]?.oid || '';
    });
  }, [selectedProjectShifts]);

  useEffect(() => {
    loadShiftReports(reportShiftId);
  }, [reportShiftId, loadShiftReports]);

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

  useEffect(() => {
    if (!memberProjectId || !resourceRequestForm.ownerUserId) {
      setOwnerResources([]);
      return;
    }

    let isMounted = true;
    setIsOwnerResourcesLoading(true);

    getProjectUserResources(memberProjectId, resourceRequestForm.ownerUserId)
      .then((response) => {
        if (!isMounted) {
          return;
        }

        setOwnerResources(Array.isArray(response?.resources) ? response.resources : []);
      })
      .catch(() => {
        if (!isMounted) {
          return;
        }

        setOwnerResources([]);
        toast.error('Не удалось загрузить ресурсы выбранного участника');
      })
      .finally(() => {
        if (isMounted) {
          setIsOwnerResourcesLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [memberProjectId, resourceRequestForm.ownerUserId]);

  const handleShiftFormChange = (event) => {
    const { name, value } = event.target;
    setShiftForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleParticipantFormChange = (event) => {
    const { name, value } = event.target;
    setParticipantForm((prev) => {
      if (name === 'shiftId') {
        const selectedShift = selectedProjectShifts.find((shift) => shift.oid === value);
        return { ...prev, shiftId: value, ...getShiftTimeRange(selectedShift) };
      }

      if (name === 'userId') {
        const selectedMember = displayedMembers.find((member) => member.user_id === value);
        return { ...prev, userId: value, role: selectedMember?.role || prev.role };
      }

      return { ...prev, [name]: value };
    });
  };

  const handleDocumentFormChange = (event) => {
    const { name, value, files } = event.target;
    setDocumentForm((prev) => ({
      ...prev,
      [name]: name === 'file' ? files?.[0] || null : value,
    }));
  };

  const handleResourceRequestFormChange = (event) => {
    const { name, value } = event.target;
    setResourceRequestForm((prev) => {
      if (name === 'shiftId') {
        const selectedShift = selectedProjectShifts.find((shift) => shift.oid === value);
        return { ...prev, shiftId: value, ...getShiftTimeRange(selectedShift) };
      }

      if (name === 'ownerUserId') {
        return {
          ...prev,
          ownerUserId: value,
          resourceId: '',
          resourceType: '',
        };
      }

      if (name === 'resourceId') {
        const nextResource = ownerResources.find((resource) => resource.resource_id === value);
        return {
          ...prev,
          resourceId: value,
          resourceType: nextResource?.resource_kind || nextResource?.resource_type || '',
        };
      }

      return { ...prev, [name]: value };
    });
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
        ...getShiftTimeRange(createdShift),
      }));
      setDocumentForm((prev) => ({
        ...prev,
        shiftId: createdShift.oid,
      }));
      setResourceRequestForm((prev) => ({
        ...prev,
        shiftId: createdShift.oid,
        ...getShiftTimeRange(createdShift),
      }));
      setShiftForm(initialShiftForm);
      toast.success('Смена создана');
    } catch (error) {
      toast.error(error?.message || 'Не удалось создать смену');
    } finally {
      setIsCreatingShift(false);
    }
  };

  const handleSelectShift = (shiftId) => {
    const selectedShift = selectedProjectShifts.find((shift) => shift.oid === shiftId);
    const shiftRange = getShiftTimeRange(selectedShift);
    setParticipantForm((prev) => ({ ...prev, shiftId, ...shiftRange }));
    setDocumentForm((prev) => ({ ...prev, shiftId }));
    setResourceRequestForm((prev) => ({ ...prev, shiftId, ...shiftRange }));
    setReportShiftId(shiftId);
  };

  const updateShiftInState = (shiftId, nextShift) => {
    setProjectShifts((prev) => ({
      ...prev,
      [memberProjectId]: (prev[memberProjectId] || []).map((shift) =>
        shift.oid === shiftId ? nextShift : shift,
      ),
    }));
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
      updateShiftInState(shiftId, updatedShift);
      toast.success('Смена подтверждена');
    } catch (error) {
      toast.error(error?.message || 'Не удалось подтвердить смену');
    } finally {
      setApprovingShiftId(null);
    }
  };

  const handleCompleteShift = async (shiftId) => {
    if (!shiftId) {
      return;
    }

    if (!canManageMembers) {
      toast.error('У вас нет прав завершать смены в этом проекте');
      return;
    }

    setShiftActionId(shiftId);

    try {
      const updatedShift = await completeShift(shiftId);
      updateShiftInState(shiftId, updatedShift);
      toast.success('Смена завершена');
    } catch (error) {
      toast.error(error?.message || 'Не удалось завершить смену');
    } finally {
      setShiftActionId(null);
    }
  };

  const handleCancelShift = async (shiftId) => {
    if (!shiftId) {
      return;
    }

    if (!canManageMembers) {
      toast.error('У вас нет прав отменять смены в этом проекте');
      return;
    }

    setShiftActionId(shiftId);

    try {
      const updatedShift = await cancelShift(shiftId);
      updateShiftInState(shiftId, updatedShift);
      toast.success('Смена отменена');
      // Cancelling a shift cancels its participants and resource requests on the
      // server, so refresh them from the backend to reflect the new statuses.
      await Promise.all([
        loadShiftParticipants(shiftId),
        loadShiftResourceRequests(shiftId),
      ]);
    } catch (error) {
      toast.error(error?.message || 'Не удалось отменить смену');
    } finally {
      setShiftActionId(null);
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

    if (!isWithinDateTimeBounds(participantForm.timeFrom, participantForm.timeTo, participantShiftBounds)) {
      toast.error('Время участия должно быть в пределах времени смены');
      return;
    }

    const selectedMember = displayedMembers.find((member) => member.user_id === userId);

    setIsInvitingParticipant(true);

    try {
      await inviteShiftParticipant(participantForm.shiftId, {
        user_id: userId,
        role: selectedMember?.role || participantForm.role,
        time_from: timeFrom,
        time_to: timeTo,
      });

      setParticipantForm((prev) => ({
        ...initialParticipantForm,
        shiftId: prev.shiftId,
        timeFrom: prev.timeFrom,
        timeTo: prev.timeTo,
      }));
      // Reload from the server so the participant list reflects the source of truth.
      await loadShiftParticipants(participantForm.shiftId);
      toast.success('Участник приглашен в смену');
    } catch (error) {
      toast.error(error?.message || 'Не удалось пригласить участника в смену');
    } finally {
      setIsInvitingParticipant(false);
    }
  };

  const handleUploadDocument = async (event) => {
    event.preventDefault();

    if (!documentForm.shiftId || !documentForm.file || !documentForm.title.trim()) {
      toast.error('Выберите смену, файл и заполните название документа');
      return;
    }

    if (!canManageMembers) {
      toast.error('У вас нет прав загружать документы для этой смены');
      return;
    }

    setIsUploadingDocument(true);

    try {
      await uploadShiftDocument(documentForm.shiftId, {
        file: documentForm.file,
        doc_type: documentForm.docType,
        title: documentForm.title.trim(),
        description: documentForm.description.trim(),
      });

      setDocumentForm((prev) => ({
        ...initialDocumentForm,
        shiftId: prev.shiftId,
        docType: prev.docType,
      }));
      setDocumentInputKey((prev) => prev + 1);
      await loadShiftDocuments(documentForm.shiftId);
      toast.success('Документ загружен');
    } catch (error) {
      toast.error(error?.message || 'Не удалось загрузить документ');
    } finally {
      setIsUploadingDocument(false);
    }
  };

  const handleOpenDocument = async (documentId) => {
    if (!documentId) {
      return;
    }

    setLoadingDocumentId(documentId);

    try {
      const response = await getDocumentDownloadUrl(documentId);
      if (!response?.download_url) {
        toast.error('Ссылка на скачивание не получена');
        return;
      }

      window.open(response.download_url, '_blank', 'noopener,noreferrer');
    } catch (error) {
      toast.error(error?.message || 'Не удалось получить ссылку на документ');
    } finally {
      setLoadingDocumentId(null);
    }
  };

  const handleCreateResourceRequest = async (event) => {
    event.preventDefault();

    const timeFrom = toIsoDateTime(resourceRequestForm.timeFrom);
    const timeTo = toIsoDateTime(resourceRequestForm.timeTo);

    if (
      !resourceRequestForm.shiftId ||
      !resourceRequestForm.ownerUserId ||
      !resourceRequestForm.resourceId ||
      !resourceRequestForm.resourceType ||
      !timeFrom ||
      !timeTo
    ) {
      toast.error('Выберите смену, владельца ресурса, ресурс и укажите время');
      return;
    }

    if (new Date(timeFrom) >= new Date(timeTo)) {
      toast.error('Время окончания запроса должно быть позже времени начала');
      return;
    }

    if (!isWithinDateTimeBounds(resourceRequestForm.timeFrom, resourceRequestForm.timeTo, resourceShiftBounds)) {
      toast.error('Время запроса должно быть в пределах времени смены');
      return;
    }

    setIsSubmittingResourceRequest(true);

    try {
      await createShiftResourceRequest(resourceRequestForm.shiftId, {
        resource_type: resourceRequestForm.resourceType,
        resource_id: resourceRequestForm.resourceId,
        resource_owner_user_id: resourceRequestForm.ownerUserId,
        time_from: timeFrom,
        time_to: timeTo,
      });

      setResourceRequestForm((prev) => ({
        ...initialResourceRequestForm,
        shiftId: prev.shiftId,
        ownerUserId: prev.ownerUserId,
      }));
      await loadShiftResourceRequests(resourceRequestForm.shiftId);
      toast.success('Запрос на ресурс создан');
    } catch (error) {
      toast.error(error?.message || 'Не удалось создать запрос на ресурс');
    } finally {
      setIsSubmittingResourceRequest(false);
    }
  };

  const handleApproveShiftResourceRequest = async (shiftId, requestId) => {
    if (!requestId) {
      return;
    }

    setResourceRequestActionId(requestId);

    try {
      await approveResourceRequest(requestId);
      toast.success('Запрос на ресурс подтвержден — ожидайте письмо для подтверждения брони');
      await loadShiftResourceRequests(shiftId);
    } catch (error) {
      toast.error(error?.message || 'Не удалось подтвердить запрос на ресурс');
    } finally {
      setResourceRequestActionId(null);
    }
  };

  const handleRejectShiftResourceRequest = async (shiftId, requestId) => {
    const reason = (rejectReasonsById[requestId] || '').trim();

    if (!requestId) {
      return;
    }

    if (!reason) {
      toast.error('Укажите причину отклонения');
      return;
    }

    setResourceRequestActionId(requestId);

    try {
      await rejectResourceRequest(requestId, { reason });
      setRejectReasonsById((prev) => ({ ...prev, [requestId]: '' }));
      toast.success('Запрос на ресурс отклонен');
      await loadShiftResourceRequests(shiftId);
    } catch (error) {
      toast.error(error?.message || 'Не удалось отклонить запрос на ресурс');
    } finally {
      setResourceRequestActionId(null);
    }
  };

  const handleCancelShiftResourceRequest = async (shiftId, requestId) => {
    if (!requestId) {
      return;
    }

    setResourceRequestActionId(requestId);

    try {
      await cancelResourceRequest(requestId);
      toast.success('Запрос на ресурс отменен');
      await loadShiftResourceRequests(shiftId);
    } catch (error) {
      toast.error(error?.message || 'Не удалось отменить запрос на ресурс');
    } finally {
      setResourceRequestActionId(null);
    }
  };

  const handleConfirmParticipant = async (shiftId, participantId) => {
    if (!participantId) {
      return;
    }

    setParticipantActionId(participantId);

    try {
      await confirmShiftParticipant(participantId);
      toast.success('Участие подтверждено');
      await loadShiftParticipants(shiftId);
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
      await declineShiftParticipant(participantId);
      toast.success('Участие отклонено');
      await loadShiftParticipants(shiftId);
    } catch (error) {
      toast.error(error?.message || 'Не удалось отклонить участие');
    } finally {
      setParticipantActionId(null);
    }
  };

  const handleCancelParticipant = async (shiftId, participantId) => {
    if (!participantId) {
      return;
    }

    if (!canManageMembers) {
      toast.error('У вас нет прав отменять участников смены');
      return;
    }

    setParticipantActionId(participantId);

    try {
      await cancelShiftParticipant(participantId);
      toast.success('Участник отменен');
      await loadShiftParticipants(shiftId);
    } catch (error) {
      toast.error(error?.message || 'Не удалось отменить участника');
    } finally {
      setParticipantActionId(null);
    }
  };

  const handleGenerateReport = async () => {
    if (!reportShiftId || !canManageMembers) {
      return;
    }

    setIsGeneratingReport(true);

    try {
      await generateShiftReport(reportShiftId);
      toast.success('Отчёт поставлен в очередь на формирование');
      await loadShiftReports(reportShiftId);
    } catch (error) {
      toast.error(error?.message || 'Не удалось запустить формирование отчёта');
    } finally {
      setIsGeneratingReport(false);
    }
  };

  const handleDownloadReport = async (reportId) => {
    if (!reportId) {
      return;
    }

    setReportActionId(reportId);

    try {
      const response = await getShiftReportDownloadUrl(reportId);
      if (!response?.download_url) {
        toast.error('Ссылка на скачивание не получена');
        return;
      }

      window.open(response.download_url, '_blank', 'noopener,noreferrer');
    } catch (error) {
      toast.error(error?.message || 'Не удалось получить ссылку на отчёт');
    } finally {
      setReportActionId(null);
    }
  };

  const handleArchiveReport = async (reportId) => {
    if (!reportId || !canManageMembers) {
      return;
    }

    setReportActionId(reportId);

    try {
      await archiveShiftReport(reportId);
      toast.success('Отчёт перемещён в архив');
      await loadShiftReports(reportShiftId);
    } catch (error) {
      toast.error(error?.message || 'Не удалось архивировать отчёт');
    } finally {
      setReportActionId(null);
    }
  };

  return (
    <section className="project-list-page shift-planning-page">
      <div className="dashboard-panel project-list-hero shift-planning-hero">
        <div>
          <span className="projects-panel-eyebrow">Смены</span>
          <h1>{memberProject ? `Планирование для "${memberProject.title}"` : 'Планирование смен'}</h1>
          <p>Создайте смену, затем пригласите участников с ролью и временным окном работы.</p>
        </div>
        <div className="shift-hero-stats" aria-label="Сводка по сменам">
          <article>
            <span>Смен</span>
            <strong>{shiftStats.shifts}</strong>
          </article>
          <article>
            <span>Подтверждено</span>
            <strong>{shiftStats.confirmed}</strong>
          </article>
          <article>
            <span>Участников</span>
            <strong>{shiftStats.participants}</strong>
          </article>
          <article>
            <span>Заявок</span>
            <strong>{shiftStats.requests}</strong>
          </article>
        </div>
      </div>

      <section className="dashboard-panel shift-planning-toolbar">
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

        <button
          type="button"
          className="ghost-action-btn"
          onClick={loadMembers}
          disabled={!memberProjectId || isMembersLoading}
        >
          {isMembersLoading ? 'Обновляем...' : 'Обновить участников'}
        </button>
      </section>

      {!memberProject ? (
        <section className="dashboard-panel project-empty-state">
          <p>Сначала выберите проект на странице проектов или в списке выше.</p>
        </section>
      ) : (
        <div className="shift-planning-layout">
          <section className="dashboard-panel shift-planning-card">
            <div className="section-heading">
              <div>
                <span className="projects-panel-eyebrow">Новая смена</span>
                <h2>Запланировать смену</h2>
              </div>
              <p>Смена сохраняется для текущего проекта и остается доступной в меню планирования.</p>
            </div>

            {canManageMembers ? (
            <form className="shift-planning-form" onSubmit={handleCreateShift}>
              <label className="field-block">
                <span>Название смены</span>
                <input
                  name="title"
                  value={shiftForm.title}
                  onChange={handleShiftFormChange}
                  placeholder="Смена первого съемочного дня"
                  disabled={!canManageMembers || isCreatingShift}
                />
              </label>

              <label className="field-block">
                <span>Описание</span>
                <input
                  name="description"
                  value={shiftForm.description}
                  onChange={handleShiftFormChange}
                  placeholder="Коротко о задачах смены"
                  disabled={!canManageMembers || isCreatingShift}
                />
              </label>

              <label className="field-block">
                <span>Начало</span>
                <input
                  name="startTime"
                  type="datetime-local"
                  value={shiftForm.startTime}
                  onChange={handleShiftFormChange}
                  disabled={!canManageMembers || isCreatingShift}
                />
              </label>

              <label className="field-block">
                <span>Окончание</span>
                <input
                  name="endTime"
                  type="datetime-local"
                  value={shiftForm.endTime}
                  onChange={handleShiftFormChange}
                  disabled={!canManageMembers || isCreatingShift}
                />
              </label>

              <button
                type="submit"
                className="profile-save-btn compact shift-planning-submit"
                disabled={!canManageMembers || isCreatingShift}
              >
                {isCreatingShift ? 'Создаем...' : 'Создать смену'}
              </button>
            </form>
            ) : null}

            <div className="project-shifts-list">
              {isShiftsLoading ? (
                <p className="helper-note">Загружаем смены...</p>
              ) : selectedProjectShifts.length === 0 ? (
                <p className="helper-note">Смены появятся здесь после создания.</p>
              ) : (
                selectedProjectShifts.map((shift) => {
                  const isSelectedShift = participantForm.shiftId === shift.oid;
                  const isApproving = approvingShiftId === shift.oid;
                  const isShiftBusy = shiftActionId === shift.oid;

                  return (
                    <article
                      key={shift.oid}
                      className={`project-shift-card${isSelectedShift ? ' is-active-project' : ''}`}
                    >
                      <div>
                        <div className="project-card-meta">
                          <span className="project-type-label">{getShiftStatusLabel(shift.status)}</span>
                          <span>Создана: {formatDateTime(shift.created_at || shift.start_time)}</span>
                        </div>
                        <h3>{shift.title}</h3>
                        <p>{shift.description || 'Описание не указано'}</p>
                        <p>{formatDateTime(shift.start_time)} - {formatDateTime(shift.end_time)}</p>
                      </div>

                      <div className="project-shift-actions">
                        <button
                          type="button"
                          className="ghost-action-btn"
                          onClick={() => handleSelectShift(shift.oid)}
                        >
                          {isSelectedShift ? 'Выбрана' : 'Выбрать'}
                        </button>
                        {canManageMembers && canApproveShiftStatus(shift.status) ? (
                          <button
                            type="button"
                            className="profile-save-btn compact"
                            onClick={() => handleApproveShift(shift.oid)}
                            disabled={isApproving}
                          >
                            {isApproving ? 'Подтверждаем...' : 'Подтвердить смену'}
                          </button>
                        ) : null}
                        {canManageMembers && canCompleteShiftStatus(shift.status) ? (
                          <button
                            type="button"
                            className="profile-save-btn compact"
                            onClick={() => handleCompleteShift(shift.oid)}
                            disabled={isShiftBusy}
                          >
                            {isShiftBusy ? 'Сохраняем...' : 'Завершить смену'}
                          </button>
                        ) : null}
                        {canManageMembers && canCancelShiftStatus(shift.status) ? (
                          <button
                            type="button"
                            className="ghost-action-btn danger"
                            onClick={() => handleCancelShift(shift.oid)}
                            disabled={isShiftBusy}
                          >
                            {isShiftBusy ? '...' : 'Отменить смену'}
                          </button>
                        ) : null}
                      </div>
                    </article>
                  );
                })
              )}
            </div>
          </section>

          <section className="dashboard-panel shift-planning-card">
            <div className="section-heading">
              <div>
                <span className="projects-panel-eyebrow">Участники смены</span>
                <h2>Пригласить в смену</h2>
              </div>
              <p>Приглашения отправляются по выбранной смене и видны ниже в списке.</p>
            </div>

            {canManageMembers ? (
            <form className="shift-planning-participant-form" onSubmit={handleInviteParticipant}>
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
                      {formatShortId(member.user_id)} - {member.isOwner ? 'Создатель' : getRoleLabel(member.role)}
                    </option>
                  ))}
                </select>
              </label>

              <label className="field-block">
                <span>Роль</span>
                <select
                  name="role"
                  value={participantForm.role}
                  onChange={handleParticipantFormChange}
                  disabled={!canManageMembers}
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
                  min={participantShiftBounds.timeFrom}
                  max={participantShiftBounds.timeTo}
                />
              </label>

              <label className="field-block">
                <span>До</span>
                <input
                  name="timeTo"
                  type="datetime-local"
                  value={participantForm.timeTo}
                  onChange={handleParticipantFormChange}
                  min={participantShiftBounds.timeFrom}
                  max={participantShiftBounds.timeTo}
                />
              </label>

              {participantShiftBounds.timeFrom ? (
                <p className="helper-note shift-planning-window-hint">
                  Окно участия можно сузить, но оно должно оставаться в пределах смены:
                  {' '}{formatDateTime(participantShiftBounds.timeFrom)} — {formatDateTime(participantShiftBounds.timeTo)}
                </p>
              ) : null}

              <button
                type="submit"
                className="profile-save-btn compact shift-planning-submit"
                disabled={!participantForm.shiftId || isInvitingParticipant}
              >
                {isInvitingParticipant ? 'Приглашаем...' : 'Пригласить в смену'}
              </button>
            </form>
            ) : null}

            <div className="project-participants-list">
              {!participantForm.shiftId ? (
                <p className="helper-note">Выберите смену, чтобы увидеть приглашенных участников.</p>
              ) : isParticipantsLoading ? (
                <p className="helper-note">Загружаем участников...</p>
              ) : selectedShiftParticipants.length === 0 ? (
                <p className="helper-note">Для этой смены пока нет приглашенных участников.</p>
              ) : (
                selectedShiftParticipants.map((participant) => {
                  const isProcessing = participantActionId === participant.oid;
                  const participantMember = displayedMembers.find((member) => member.user_id === participant.user_id);
                  const isParticipantSelf = currentUserId === participant.user_id;
                  const canCancelParticipant =
                    canManageMembers && canCancelParticipantStatus(participant.status);

                  return (
                    <article key={participant.oid} className="project-member-card">
                      <div>
                        <span className="project-type-label">{getParticipantStatusLabel(participant.status)}</span>
                        <h3 title={participant.user_id}>{formatShortId(participant.user_id)}</h3>
                        <p>
                          {participantMember?.isOwner ? 'Создатель проекта' : getMemberStatusLabel(participantMember?.status)}
                          {' '}· {getRoleLabel(participant.role)}
                        </p>
                        <p>{formatDateTime(participant.time_from)} - {formatDateTime(participant.time_to)}</p>
                      </div>

                      {isParticipantSelf || canCancelParticipant ? (
                      <div className="project-member-actions">
                        {isParticipantSelf ? (
                          <>
                            <button
                              type="button"
                              className="ghost-action-btn"
                              onClick={() => handleConfirmParticipant(participant.shift_id, participant.oid)}
                              disabled={isProcessing}
                            >
                              {isProcessing ? '...' : 'Подтвердить'}
                            </button>
                            <button
                              type="button"
                              className="ghost-action-btn danger"
                              onClick={() => handleDeclineParticipant(participant.shift_id, participant.oid)}
                              disabled={isProcessing}
                            >
                              {isProcessing ? '...' : 'Отклонить'}
                            </button>
                          </>
                        ) : null}
                        {canCancelParticipant ? (
                          <button
                            type="button"
                            className="ghost-action-btn danger"
                            onClick={() => handleCancelParticipant(participant.shift_id, participant.oid)}
                            disabled={isProcessing}
                          >
                            {isProcessing ? '...' : 'Отменить'}
                          </button>
                        ) : null}
                      </div>
                      ) : null}
                    </article>
                  );
                })
              )}
            </div>
          </section>

          <section className="dashboard-panel shift-planning-card">
            <div className="section-heading">
              <div>
                <span className="projects-panel-eyebrow">Документы</span>
                <h2>Документы смены</h2>
              </div>
              <p>Загрузите план или сценарий для выбранной смены и получите временную ссылку на скачивание.</p>
            </div>

            {canManageMembers ? (
            <form className="shift-planning-document-form" onSubmit={handleUploadDocument}>
              <label className="field-block">
                <span>Смена</span>
                <select
                  name="shiftId"
                  value={documentForm.shiftId}
                  onChange={handleDocumentFormChange}
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
                <span>Тип документа</span>
                <select
                  name="docType"
                  value={documentForm.docType}
                  onChange={handleDocumentFormChange}
                  disabled={!canManageMembers}
                >
                  {documentTypeOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>

              <label className="field-block">
                <span>Название</span>
                <input
                  name="title"
                  value={documentForm.title}
                  onChange={handleDocumentFormChange}
                  placeholder="План первого съемочного дня"
                  disabled={!canManageMembers || isUploadingDocument}
                />
              </label>

              <label className="field-block">
                <span>Описание</span>
                <input
                  name="description"
                  value={documentForm.description}
                  onChange={handleDocumentFormChange}
                  placeholder="Необязательно"
                  disabled={!canManageMembers || isUploadingDocument}
                />
              </label>

              <label className="field-block">
                <span>Файл</span>
                <input
                  key={documentInputKey}
                  name="file"
                  type="file"
                  onChange={handleDocumentFormChange}
                  disabled={!canManageMembers || isUploadingDocument}
                />
              </label>

              <button
                type="submit"
                className="profile-save-btn compact shift-planning-submit"
                disabled={!documentForm.shiftId || !canManageMembers || isUploadingDocument}
              >
                {isUploadingDocument ? 'Загружаем...' : 'Загрузить документ'}
              </button>
            </form>
            ) : null}

            <div className="project-documents-list">
              {!documentForm.shiftId ? (
                <p className="helper-note">Выберите смену, чтобы увидеть документы.</p>
              ) : isDocumentsLoading ? (
                <p className="helper-note">Загружаем документы...</p>
              ) : selectedShiftDocuments.length === 0 ? (
                <p className="helper-note">Для этой смены пока нет документов.</p>
              ) : (
                selectedShiftDocuments.map((document) => (
                  <article key={document.oid} className="project-member-card">
                    <div>
                      <span className="project-type-label">{getDocumentTypeLabel(document.doc_type)}</span>
                      <h3>{document.title}</h3>
                      <p>{document.description || 'Описание не указано'}</p>
                      <p>{document.filename || document.storage_key || 'Файл без имени'} · {formatDateTime(document.created_at)}</p>
                    </div>

                    <div className="project-member-actions">
                      <button
                        type="button"
                        className="ghost-action-btn"
                        onClick={() => handleOpenDocument(document.oid)}
                        disabled={loadingDocumentId === document.oid}
                      >
                        {loadingDocumentId === document.oid ? 'Получаем...' : 'Открыть ссылку'}
                      </button>
                    </div>
                  </article>
                ))
              )}
            </div>
          </section>

          <section className="dashboard-panel shift-planning-card">
            <div className="section-heading">
              <div>
                <span className="projects-panel-eyebrow">Ресурсы</span>
                <h2>Запросы на ресурсы</h2>
              </div>
              <p>Создайте запрос на ресурс для смены, затем владелец ресурса сможет его подтвердить или отклонить.</p>
            </div>

            {canRequestResources ? (
            <form className="shift-planning-resource-form" onSubmit={handleCreateResourceRequest}>
              <label className="field-block">
                <span>Смена</span>
                <select
                  name="shiftId"
                  value={resourceRequestForm.shiftId}
                  onChange={handleResourceRequestFormChange}
                  disabled={selectedProjectShifts.length === 0}
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
                <span>Владелец ресурса</span>
                <select
                  name="ownerUserId"
                  value={resourceRequestForm.ownerUserId}
                  onChange={handleResourceRequestFormChange}
                  disabled={availableParticipantMembers.length === 0}
                >
                  <option value="">Выберите владельца</option>
                  {availableParticipantMembers.map((member) => (
                    <option key={member.user_id} value={member.user_id}>
                      {formatShortId(member.user_id)} - {member.isOwner ? 'Создатель' : getRoleLabel(member.role)}
                    </option>
                  ))}
                </select>
              </label>

              <label className="field-block">
                <span>Ресурс</span>
                <select
                  name="resourceId"
                  value={resourceRequestForm.resourceId}
                  onChange={handleResourceRequestFormChange}
                  disabled={!resourceRequestForm.ownerUserId || isOwnerResourcesLoading}
                >
                  <option value="">
                    {isOwnerResourcesLoading ? 'Загружаем ресурсы...' : 'Выберите ресурс'}
                  </option>
                  {ownerResources.map((resource) => (
                    <option key={resource.resource_id} value={resource.resource_id}>
                      {(resource.title || resource.resource_id)} - {(resource.resource_kind || resource.resource_type || 'Ресурс')}
                    </option>
                  ))}
                </select>
              </label>

              <label className="field-block">
                <span>С</span>
                <input
                  name="timeFrom"
                  type="datetime-local"
                  value={resourceRequestForm.timeFrom}
                  onChange={handleResourceRequestFormChange}
                  min={resourceShiftBounds.timeFrom}
                  max={resourceShiftBounds.timeTo}
                />
              </label>

              <label className="field-block">
                <span>До</span>
                <input
                  name="timeTo"
                  type="datetime-local"
                  value={resourceRequestForm.timeTo}
                  onChange={handleResourceRequestFormChange}
                  min={resourceShiftBounds.timeFrom}
                  max={resourceShiftBounds.timeTo}
                />
              </label>

              {resourceShiftBounds.timeFrom ? (
                <p className="helper-note shift-planning-window-hint">
                  Время можно сузить, но оно должно оставаться в пределах смены:
                  {' '}{formatDateTime(resourceShiftBounds.timeFrom)} — {formatDateTime(resourceShiftBounds.timeTo)}
                </p>
              ) : null}

              <button
                type="submit"
                className="profile-save-btn compact shift-planning-submit"
                disabled={!resourceRequestForm.shiftId || isSubmittingResourceRequest}
              >
                {isSubmittingResourceRequest ? 'Создаем...' : 'Создать запрос'}
              </button>
            </form>
            ) : null}

            <div className="project-resource-requests-list">
              {!resourceRequestForm.shiftId ? (
                <p className="helper-note">Выберите смену, чтобы увидеть запросы на ресурсы.</p>
              ) : isResourceRequestsLoading ? (
                <p className="helper-note">Загружаем запросы на ресурсы...</p>
              ) : selectedShiftResourceRequests.length === 0 ? (
                <p className="helper-note">Для этой смены пока нет запросов на ресурсы.</p>
              ) : (
                selectedShiftResourceRequests.map((request) => {
                  const isProcessing = resourceRequestActionId === request.oid;
                  const canDecide = currentUserId && request.resource_owner_user_id === currentUserId;
                  const isRequester =
                    currentUserId && request.requested_by_user_id === currentUserId;
                  const canCancelRequest =
                    (isRequester || canManageMembers) &&
                    canCancelResourceRequestStatus(request.status);

                  return (
                    <article key={request.oid} className="project-member-card shift-resource-request-card">
                      <div className="shift-resource-request-copy">
                        <span className="project-type-label">{request.resource_type || 'Ресурс'}</span>
                        <span className="project-type-label">{getResourceRequestStatusLabel(request.status)}</span>
                        <h3 title={request.resource_id}>{formatShortId(request.resource_id)}</h3>
                        <p title={request.resource_owner_user_id}>Владелец: {formatShortId(request.resource_owner_user_id)}</p>
                        <p>{formatDateTime(request.time_from)} - {formatDateTime(request.time_to)}</p>
                        {request.rejection_reason ? <p>Причина отказа: {request.rejection_reason}</p> : null}
                        {request.reserve_failure_reason ? <p>Ошибка резерва: {request.reserve_failure_reason}</p> : null}
                      </div>

                      {Number(request.status) === 0 && canDecide && (
                        <div className="project-member-actions shift-resource-actions">
                          <label className="field-block shift-resource-reason">
                            <span>Причина отказа</span>
                            <input
                              value={rejectReasonsById[request.oid] || ''}
                              onChange={(event) =>
                                setRejectReasonsById((prev) => ({ ...prev, [request.oid]: event.target.value }))
                              }
                              placeholder="Укажите причину"
                              disabled={!canDecide || isProcessing}
                            />
                          </label>

                          <button
                            type="button"
                            className="ghost-action-btn"
                            onClick={() => handleApproveShiftResourceRequest(request.shift_id, request.oid)}
                            disabled={!canDecide || isProcessing}
                          >
                            {isProcessing ? '...' : 'Подтвердить'}
                          </button>
                          <button
                            type="button"
                            className="ghost-action-btn danger"
                            onClick={() => handleRejectShiftResourceRequest(request.shift_id, request.oid)}
                            disabled={!canDecide || isProcessing}
                          >
                            {isProcessing ? '...' : 'Отклонить'}
                          </button>
                        </div>
                      )}

                      {canCancelRequest && (
                        <div className="project-member-actions shift-resource-actions">
                          <button
                            type="button"
                            className="ghost-action-btn danger"
                            onClick={() => handleCancelShiftResourceRequest(request.shift_id, request.oid)}
                            disabled={isProcessing}
                          >
                            {isProcessing ? '...' : 'Отменить запрос'}
                          </button>
                        </div>
                      )}
                    </article>
                  );
                })
              )}
            </div>
          </section>

          {canManageMembers ? (
          <section className="dashboard-panel shift-planning-card">
            <div className="section-heading">
              <div>
                <span className="projects-panel-eyebrow">Отчётность</span>
                <h2>Отчёты по смене</h2>
              </div>
              <p>Сформируйте XLSX-отчёт по смене, скачайте готовую версию или отправьте устаревшую в архив.</p>
            </div>

            <form className="shift-planning-report-form" onSubmit={(event) => event.preventDefault()}>
              <label className="field-block">
                <span>Смена</span>
                <select
                  value={reportShiftId}
                  onChange={(event) => setReportShiftId(event.target.value)}
                  disabled={selectedProjectShifts.length === 0}
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

              <div className="shift-planning-report-actions">
                <button
                  type="button"
                  className="profile-save-btn compact shift-planning-submit"
                  onClick={handleGenerateReport}
                  disabled={
                    !reportShiftId ||
                    isGeneratingReport ||
                    !canGenerateReportForShiftStatus(reportShift?.status)
                  }
                >
                  {isGeneratingReport ? 'Формируем...' : 'Сформировать отчёт'}
                </button>
                <button
                  type="button"
                  className="ghost-action-btn"
                  onClick={() => loadShiftReports(reportShiftId)}
                  disabled={!reportShiftId || isReportsLoading}
                >
                  {isReportsLoading ? 'Обновляем...' : 'Обновить'}
                </button>
              </div>

              {reportShiftId && !canGenerateReportForShiftStatus(reportShift?.status) ? (
                <p className="helper-note shift-planning-window-hint">
                  Отчёт можно сформировать только после подтверждения смены.
                </p>
              ) : null}
            </form>

            <div className="project-reports-list">
              {!reportShiftId ? (
                <p className="helper-note">Выберите смену, чтобы увидеть отчёты.</p>
              ) : isReportsLoading ? (
                <p className="helper-note">Загружаем отчёты...</p>
              ) : selectedShiftReports.length === 0 ? (
                <p className="helper-note">Для этой смены ещё нет отчётов.</p>
              ) : (
                selectedShiftReports.map((report) => {
                  const isProcessing = reportActionId === report.oid;
                  const isStale = Number(report.actuality_status) === REPORT_ACTUALITY_STALE;
                  const isFailed = Number(report.generation_status) === REPORT_GENERATION_STATUS_FAILED;

                  return (
                    <article key={report.oid} className="project-member-card">
                      <div>
                        <div className="project-card-meta">
                          <span className="project-type-label">Версия {report.version}</span>
                          <span className="project-type-label">{getReportGenerationStatusLabel(report.generation_status)}</span>
                          <span className="project-type-label">{isStale ? 'Устарел' : 'Актуален'}</span>
                        </div>
                        <h3>{report.file_name || `Отчёт смены v${report.version}`}</h3>
                        <p>{formatDateTime(report.generated_at || report.created_at)}</p>
                        {isFailed && report.error_message ? <p>Ошибка: {report.error_message}</p> : null}
                        {isStale && report.stale_reason ? <p>Причина устаревания: {report.stale_reason}</p> : null}
                      </div>

                      <div className="project-member-actions">
                        {isReportReady(report.generation_status) ? (
                          <button
                            type="button"
                            className="ghost-action-btn"
                            onClick={() => handleDownloadReport(report.oid)}
                            disabled={isProcessing}
                          >
                            {isProcessing ? '...' : 'Скачать'}
                          </button>
                        ) : null}
                        {canArchiveReportStatus(report.generation_status) ? (
                          <button
                            type="button"
                            className="ghost-action-btn danger"
                            onClick={() => handleArchiveReport(report.oid)}
                            disabled={isProcessing}
                          >
                            {isProcessing ? '...' : 'В архив'}
                          </button>
                        ) : null}
                      </div>
                    </article>
                  );
                })
              )}
            </div>
          </section>
          ) : null}
        </div>
      )}
    </section>
  );
};

export default ShiftPlanningPage;
