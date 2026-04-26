import { useCallback, useEffect, useMemo, useState } from 'react';
import { toast } from 'react-toastify';

import {
  approveShift,
  approveResourceRequest,
  createShift,
  createShiftResourceRequest,
  declineShiftParticipant,
  confirmShiftParticipant,
  getDocumentDownloadUrl,
  getProjectUserResources,
  inviteShiftParticipant,
  listProjectMembers,
  rejectResourceRequest,
  uploadShiftDocument,
} from '../services/api';
import { useAuth } from '../context/useAuth';
import { useProjectContext } from '../context/useProjectContext';
import { formatDateTime, toIsoDateTime } from '../utils/dateTime';

const STORAGE_KEYS = {
  shifts: 'kinoflow.projectShifts',
  participants: 'kinoflow.shiftParticipants',
  documents: 'kinoflow.shiftDocuments',
  resourceRequests: 'kinoflow.shiftResourceRequests',
};

const roleOptions = [
  { value: 'DIRECTOR', label: 'Режиссер' },
  { value: 'PROP_MASTER', label: 'Реквизитор' },
  { value: 'CAMERA', label: 'Камера' },
  { value: 'SOUND', label: 'Звук' },
  { value: 'LIGHT', label: 'Свет' },
  { value: 'ACTOR', label: 'Актер' },
];

const memberStatusLabels = {
  0: 'Активен',
  1: 'Неактивен',
};

const participantStatusLabels = {
  0: 'Ожидает',
  1: 'Подтвержден',
  2: 'Отклонен',
};

const shiftStatusLabels = {
  0: 'Черновик',
  1: 'Подтверждена',
};

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
const getMemberStatusLabel = (status) => memberStatusLabels[status] || `Статус ${status}`;
const getParticipantStatusLabel = (status) => participantStatusLabels[status] || `Статус ${status}`;
const getShiftStatusLabel = (status) => shiftStatusLabels[status] || `Статус ${status}`;

const readStorage = (key) => {
  try {
    const rawValue = localStorage.getItem(key);
    return rawValue ? JSON.parse(rawValue) : {};
  } catch {
    return {};
  }
};

const writeStorage = (key, value) => {
  localStorage.setItem(key, JSON.stringify(value));
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
  const [projectShifts, setProjectShifts] = useState(() => readStorage(STORAGE_KEYS.shifts));
  const [shiftParticipants, setShiftParticipants] = useState(() => readStorage(STORAGE_KEYS.participants));
  const [shiftDocuments, setShiftDocuments] = useState(() => readStorage(STORAGE_KEYS.documents));
  const [shiftResourceRequests, setShiftResourceRequests] = useState(() => readStorage(STORAGE_KEYS.resourceRequests));
  const [isCreatingShift, setIsCreatingShift] = useState(false);
  const [approvingShiftId, setApprovingShiftId] = useState(null);
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

  const currentUserId = getCurrentUserId(userData);

  useEffect(() => {
    refreshProjects();
  }, [refreshProjects]);

  useEffect(() => {
    writeStorage(STORAGE_KEYS.shifts, projectShifts);
  }, [projectShifts]);

  useEffect(() => {
    writeStorage(STORAGE_KEYS.participants, shiftParticipants);
  }, [shiftParticipants]);

  useEffect(() => {
    writeStorage(STORAGE_KEYS.documents, shiftDocuments);
  }, [shiftDocuments]);

  useEffect(() => {
    writeStorage(STORAGE_KEYS.resourceRequests, shiftResourceRequests);
  }, [shiftResourceRequests]);

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

  useEffect(() => {
    setParticipantForm((prev) => {
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

      if (nextShiftId === prev.shiftId) {
        return prev;
      }

      return { ...prev, shiftId: nextShiftId };
    });
  }, [selectedProjectShifts]);

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
    setParticipantForm((prev) => ({ ...prev, [name]: value }));
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

  const handleSelectShift = (shiftId) => {
    setParticipantForm((prev) => ({ ...prev, shiftId }));
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
      const uploadedDocument = await uploadShiftDocument(documentForm.shiftId, {
        file: documentForm.file,
        doc_type: documentForm.docType,
        title: documentForm.title.trim(),
        description: documentForm.description.trim(),
      });

      setShiftDocuments((prev) => ({
        ...prev,
        [documentForm.shiftId]: [uploadedDocument, ...(prev[documentForm.shiftId] || [])],
      }));
      setDocumentForm((prev) => ({
        ...initialDocumentForm,
        shiftId: prev.shiftId,
        docType: prev.docType,
      }));
      setDocumentInputKey((prev) => prev + 1);
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

    setIsSubmittingResourceRequest(true);

    try {
      const request = await createShiftResourceRequest(resourceRequestForm.shiftId, {
        resource_type: resourceRequestForm.resourceType,
        resource_id: resourceRequestForm.resourceId,
        resource_owner_user_id: resourceRequestForm.ownerUserId,
        time_from: timeFrom,
        time_to: timeTo,
      });

      setShiftResourceRequests((prev) => ({
        ...prev,
        [resourceRequestForm.shiftId]: [request, ...(prev[resourceRequestForm.shiftId] || [])],
      }));
      setResourceRequestForm((prev) => ({
        ...initialResourceRequestForm,
        shiftId: prev.shiftId,
        ownerUserId: prev.ownerUserId,
      }));
      toast.success('Запрос на ресурс создан');
    } catch (error) {
      toast.error(error?.message || 'Не удалось создать запрос на ресурс');
    } finally {
      setIsSubmittingResourceRequest(false);
    }
  };

  const updateResourceRequestInState = (shiftId, requestId, nextRequest) => {
    setShiftResourceRequests((prev) => ({
      ...prev,
      [shiftId]: (prev[shiftId] || []).map((request) =>
        request.oid === requestId ? nextRequest : request,
      ),
    }));
  };

  const handleApproveShiftResourceRequest = async (shiftId, requestId) => {
    if (!requestId) {
      return;
    }

    setResourceRequestActionId(requestId);

    try {
      const updatedRequest = await approveResourceRequest(requestId);
      updateResourceRequestInState(shiftId, requestId, updatedRequest);
      toast.success('Запрос на ресурс подтвержден');
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
      const updatedRequest = await rejectResourceRequest(requestId, { reason });
      updateResourceRequestInState(shiftId, requestId, updatedRequest);
      setRejectReasonsById((prev) => ({ ...prev, [requestId]: '' }));
      toast.success('Запрос на ресурс отклонен');
    } catch (error) {
      toast.error(error?.message || 'Не удалось отклонить запрос на ресурс');
    } finally {
      setResourceRequestActionId(null);
    }
  };

  const handleConfirmParticipant = async (shiftId, participantId) => {
    if (!participantId) {
      return;
    }

    if (!canManageMembers) {
      toast.error('У вас нет прав подтверждать участие в этой смене');
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

    if (!canManageMembers) {
      toast.error('У вас нет прав отклонять участие в этой смене');
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

  return (
    <section className="project-list-page shift-planning-page">
      <div className="dashboard-panel project-list-hero">
        <div>
          <span className="projects-panel-eyebrow">Смены</span>
          <h1>{memberProject ? `Планирование для "${memberProject.title}"` : 'Планирование смен'}</h1>
          <p>Создайте смену, затем пригласите участников с ролью и временным окном работы.</p>
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

            {!canManageMembers ? (
              <p className="helper-note">Создавать и подтверждать смены может создатель проекта или участник с ролью DIRECTOR.</p>
            ) : null}

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

            <div className="project-shifts-list">
              {selectedProjectShifts.length === 0 ? (
                <p className="helper-note">Смены появятся здесь после создания.</p>
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
          </section>

          <section className="dashboard-panel shift-planning-card">
            <div className="section-heading">
              <div>
                <span className="projects-panel-eyebrow">Участники смены</span>
                <h2>Пригласить в смену</h2>
              </div>
              <p>Приглашения отправляются по выбранной смене и видны ниже в списке.</p>
            </div>

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
                      {member.user_id} - {member.isOwner ? 'Создатель' : getRoleLabel(member.role)}
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
                  disabled={!canManageMembers}
                />
              </label>

              <label className="field-block">
                <span>До</span>
                <input
                  name="timeTo"
                  type="datetime-local"
                  value={participantForm.timeTo}
                  onChange={handleParticipantFormChange}
                  disabled={!canManageMembers}
                />
              </label>

              <button
                type="submit"
                className="profile-save-btn compact shift-planning-submit"
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
                  const participantMember = displayedMembers.find((member) => member.user_id === participant.user_id);

                  return (
                    <article key={participant.oid} className="project-member-card">
                      <div>
                        <span className="project-type-label">{getParticipantStatusLabel(participant.status)}</span>
                        <h3>{participant.user_id}</h3>
                        <p>
                          {participantMember?.isOwner ? 'Создатель проекта' : getMemberStatusLabel(participantMember?.status)}
                          {' '}· {getRoleLabel(participant.role)}
                        </p>
                        <p>{formatDateTime(participant.time_from)} - {formatDateTime(participant.time_to)}</p>
                      </div>

                      <div className="project-member-actions">
                        <button
                          type="button"
                          className="ghost-action-btn"
                          onClick={() => handleConfirmParticipant(participant.shift_id, participant.oid)}
                          disabled={!canManageMembers || isProcessing}
                        >
                          {isProcessing ? '...' : 'Подтвердить'}
                        </button>
                        <button
                          type="button"
                          className="ghost-action-btn danger"
                          onClick={() => handleDeclineParticipant(participant.shift_id, participant.oid)}
                          disabled={!canManageMembers || isProcessing}
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

          <section className="dashboard-panel shift-planning-card">
            <div className="section-heading">
              <div>
                <span className="projects-panel-eyebrow">Документы</span>
                <h2>Документы смены</h2>
              </div>
              <p>Загрузите план или сценарий для выбранной смены и получите временную ссылку на скачивание.</p>
            </div>

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

            <div className="project-documents-list">
              {!documentForm.shiftId ? (
                <p className="helper-note">Выберите смену, чтобы увидеть документы.</p>
              ) : selectedShiftDocuments.length === 0 ? (
                <p className="helper-note">Для этой смены пока нет документов.</p>
              ) : (
                selectedShiftDocuments.map((document) => (
                  <article key={document.oid} className="project-member-card">
                    <div>
                      <span className="project-type-label">{document.doc_type}</span>
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
                      {member.user_id} - {member.isOwner ? 'Создатель' : getRoleLabel(member.role)}
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
                />
              </label>

              <label className="field-block">
                <span>До</span>
                <input
                  name="timeTo"
                  type="datetime-local"
                  value={resourceRequestForm.timeTo}
                  onChange={handleResourceRequestFormChange}
                />
              </label>

              <button
                type="submit"
                className="profile-save-btn compact shift-planning-submit"
                disabled={!resourceRequestForm.shiftId || isSubmittingResourceRequest}
              >
                {isSubmittingResourceRequest ? 'Создаем...' : 'Создать запрос'}
              </button>
            </form>

            <div className="project-resource-requests-list">
              {!resourceRequestForm.shiftId ? (
                <p className="helper-note">Выберите смену, чтобы увидеть запросы на ресурсы.</p>
              ) : selectedShiftResourceRequests.length === 0 ? (
                <p className="helper-note">Для этой смены пока нет запросов на ресурсы.</p>
              ) : (
                selectedShiftResourceRequests.map((request) => {
                  const isProcessing = resourceRequestActionId === request.oid;
                  const canDecide = currentUserId && request.resource_owner_user_id === currentUserId;

                  return (
                    <article key={request.oid} className="project-member-card">
                      <div>
                        <span className="project-type-label">{request.resource_type || 'Ресурс'}</span>
                        <h3>{request.resource_id}</h3>
                        <p>Владелец: {request.resource_owner_user_id}</p>
                        <p>{formatDateTime(request.time_from)} - {formatDateTime(request.time_to)}</p>
                        {request.rejection_reason ? <p>Причина отказа: {request.rejection_reason}</p> : null}
                        {request.reserve_failure_reason ? <p>Ошибка резерва: {request.reserve_failure_reason}</p> : null}
                      </div>

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
                    </article>
                  );
                })
              )}
            </div>
          </section>
        </div>
      )}
    </section>
  );
};

export default ShiftPlanningPage;
