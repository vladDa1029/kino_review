import { useCallback, useEffect, useMemo, useState } from 'react';
import { toast } from 'react-toastify';

import {
  approveShift,
  createShift,
  declineShiftParticipant,
  confirmShiftParticipant,
  inviteShiftParticipant,
  listProjectMembers,
} from '../services/api';
import { useAuth } from '../context/useAuth';
import { useProjectContext } from '../context/useProjectContext';
import { formatDateTime, toIsoDateTime } from '../utils/dateTime';

const STORAGE_KEYS = {
  shifts: 'kinoflow.projectShifts',
  participants: 'kinoflow.shiftParticipants',
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
  const [projectShifts, setProjectShifts] = useState(() => readStorage(STORAGE_KEYS.shifts));
  const [shiftParticipants, setShiftParticipants] = useState(() => readStorage(STORAGE_KEYS.participants));
  const [isCreatingShift, setIsCreatingShift] = useState(false);
  const [approvingShiftId, setApprovingShiftId] = useState(null);
  const [isInvitingParticipant, setIsInvitingParticipant] = useState(false);
  const [participantActionId, setParticipantActionId] = useState(null);

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
    if (!participantForm.userId) {
      return;
    }

    const selectedMember = displayedMembers.find((member) => member.user_id === participantForm.userId);
    if (!selectedMember || selectedMember.role === participantForm.role) {
      return;
    }

    setParticipantForm((prev) => ({ ...prev, role: selectedMember.role }));
  }, [displayedMembers, participantForm.role, participantForm.userId]);

  const handleShiftFormChange = (event) => {
    const { name, value } = event.target;
    setShiftForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleParticipantFormChange = (event) => {
    const { name, value } = event.target;
    setParticipantForm((prev) => ({ ...prev, [name]: value }));
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
        </div>
      )}
    </section>
  );
};

export default ShiftPlanningPage;
