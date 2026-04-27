import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-toastify';
import { API_BASE_URL } from '../constants';
import { ApiError } from '../services/httpClient';
import {
  addCameraFreeTime,
  addCameraTripodFreeTime,
  addLightFreeTime,
  addLightTripodFreeTime,
  addMicrofonFreeTime,
  addRequisiteFreeTime,
  addRequisiteImage,
  addSoundFreeTime,
  createCamera,
  createCameraTripod,
  createLight,
  createLightTripod,
  createMicrofon,
  createRequisite,
  createSound,
  deleteCamera,
  deleteCameraTripod,
  deleteLight,
  deleteLightTripod,
  deleteMicrofon,
  deleteRequisite,
  deleteSound,
  getRequisiteImage,
  getProjectUserResources,
  listCameraFreeTimes,
  listCameras,
  listCameraTripodFreeTimes,
  listCameraTripods,
  listLightFreeTimes,
  listLights,
  listLightTripodFreeTimes,
  listLightTripods,
  listMicrofonFreeTimes,
  listMicrofons,
  listRequisiteFreeTimes,
  listRequisiteImages,
  listRequisites,
  listSoundFreeTimes,
  listSounds,
  removeRequisiteImage,
  reserveAvailability,
  updateCamera,
  updateCameraTripod,
  updateLight,
  updateLightTripod,
  updateMicrofon,
  updateRequisite,
  updateSound,
} from '../services/api';
import { useAuth } from '../context/useAuth';
import { useProjectContext } from '../context/useProjectContext';
import { formatDateTime, toIsoDateTime } from '../utils/dateTime';

const resourceOrder = ['microfons', 'cameras', 'camera-tripods', 'lights', 'light-tripods', 'sounds', 'requisites'];
const RESOURCE_PAGE_SIZE = 100;
const resourceKindAliases = {
  microfons: ['microfons', 'microfon', 'microphones', 'microphone'],
  cameras: ['cameras', 'camera'],
  'camera-tripods': ['camera-tripods', 'camera-tripod', 'camera_tripods', 'camera_tripod'],
  lights: ['lights', 'light'],
  'light-tripods': ['light-tripods', 'light-tripod', 'light_tripods', 'light_tripod'],
  sounds: ['sounds', 'sound'],
  requisites: ['requisites', 'requisite', 'props', 'prop'],
};

const createInitialResourceForm = () => ({ title: '', description: '', type: '', size: '' });
const createInitialWindowForm = () => ({ startTime: '', endTime: '' });
const createDefaultTimeWindowForm = () => ({ startTime: '09:00', endTime: '18:00' });
const createInitialImageForm = () => ({ file: null, title: '', description: '' });

const tableColumns = {
  equipment: [
    { key: 'title', label: 'Название' },
    { key: 'description', label: 'Описание' },
    { key: 'type', label: 'Тип' },
    { key: 'create_at', label: 'Создано', render: (item) => formatDateTime(item.create_at) },
  ],
  requisites: [
    { key: 'title', label: 'Название' },
    { key: 'description', label: 'Описание' },
    { key: 'type', label: 'Тип' },
    { key: 'size', label: 'Размер' },
    { key: 'create_at', label: 'Создано', render: (item) => formatDateTime(item.create_at) },
  ],
};

const resourceMeta = {
  microfons: {
    label: 'Микрофоны',
    one: 'микрофон',
    create: createMicrofon,
    list: listMicrofons,
    update: updateMicrofon,
    remove: deleteMicrofon,
    addFreeTime: addMicrofonFreeTime,
    listFreeTimes: listMicrofonFreeTimes,
    columns: tableColumns.equipment,
    placeholders: { title: 'Rode NTG5', description: 'Пушка для съемок на площадке', type: 'shotgun' },
    buildPayload: (form) => ({ title: form.title.trim(), description: form.description.trim(), type: form.type.trim() }),
  },
  cameras: {
    label: 'Камеры',
    one: 'камера',
    create: createCamera,
    list: listCameras,
    update: updateCamera,
    remove: deleteCamera,
    addFreeTime: addCameraFreeTime,
    listFreeTimes: listCameraFreeTimes,
    columns: tableColumns.equipment,
    placeholders: { title: 'Sony A7S III', description: 'Основная камера для съемочного дня', type: 'mirrorless' },
    buildPayload: (form) => ({ title: form.title.trim(), description: form.description.trim(), type: form.type.trim() }),
  },
  'camera-tripods': {
    label: 'Штативы для камер',
    one: 'штатив для камеры',
    create: createCameraTripod,
    list: listCameraTripods,
    update: updateCameraTripod,
    remove: deleteCameraTripod,
    addFreeTime: addCameraTripodFreeTime,
    listFreeTimes: listCameraTripodFreeTimes,
    columns: tableColumns.equipment,
    placeholders: { title: 'Manfrotto 190', description: 'Штатив для статичных планов', type: 'tripod' },
    buildPayload: (form) => ({ title: form.title.trim(), description: form.description.trim(), type: form.type.trim() }),
  },
  lights: {
    label: 'Свет',
    one: 'осветитель',
    create: createLight,
    list: listLights,
    update: updateLight,
    remove: deleteLight,
    addFreeTime: addLightFreeTime,
    listFreeTimes: listLightFreeTimes,
    columns: tableColumns.equipment,
    placeholders: { title: 'Aputure 300D', description: 'Постоянный свет для ключевой сцены', type: 'led' },
    buildPayload: (form) => ({ title: form.title.trim(), description: form.description.trim(), type: form.type.trim() }),
  },
  'light-tripods': {
    label: 'Стойки для света',
    one: 'стойка для света',
    create: createLightTripod,
    list: listLightTripods,
    update: updateLightTripod,
    remove: deleteLightTripod,
    addFreeTime: addLightTripodFreeTime,
    listFreeTimes: listLightTripodFreeTimes,
    columns: tableColumns.equipment,
    placeholders: { title: 'C-Stand', description: 'Стойка для световых приборов', type: 'stand' },
    buildPayload: (form) => ({ title: form.title.trim(), description: form.description.trim(), type: form.type.trim() }),
  },
  sounds: {
    label: 'Звук',
    one: 'звуковое устройство',
    create: createSound,
    list: listSounds,
    update: updateSound,
    remove: deleteSound,
    addFreeTime: addSoundFreeTime,
    listFreeTimes: listSoundFreeTimes,
    columns: tableColumns.equipment,
    placeholders: { title: 'Zoom F6', description: 'Рекордер для полевого звука', type: 'recorder' },
    buildPayload: (form) => ({ title: form.title.trim(), description: form.description.trim(), type: form.type.trim() }),
  },
  requisites: {
    label: 'Реквизит',
    one: 'реквизит',
    create: createRequisite,
    list: listRequisites,
    update: updateRequisite,
    remove: deleteRequisite,
    addFreeTime: addRequisiteFreeTime,
    listFreeTimes: listRequisiteFreeTimes,
    columns: tableColumns.requisites,
    supportsImages: true,
    placeholders: { title: 'Винтажная лампа', description: 'Декоративная лампа в теплых тонах', type: 'decor', size: 'm' },
    buildPayload: (form) => ({
      title: form.title.trim(),
      description: form.description.trim(),
      type: form.type.trim(),
      size: form.size.trim(),
    }),
  },
};

const pad = (value) => String(value).padStart(2, '0');
const toDateKey = (value) => {
  const date = value instanceof Date ? value : new Date(value);
  return Number.isNaN(date.getTime()) ? '' : `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
};
const fromDateKey = (dateKey) => {
  const [year, month, day] = dateKey.split('-').map(Number);
  return new Date(year, month - 1, day);
};
const buildLocalDateTime = (dateKey, timeValue) => {
  const [hours, minutes] = timeValue.split(':').map(Number);
  const date = fromDateKey(dateKey);
  date.setHours(hours, minutes, 0, 0);
  return date;
};
const startOfMonth = (date) => new Date(date.getFullYear(), date.getMonth(), 1);

const monthFormatter = new Intl.DateTimeFormat('ru-RU', { month: 'long', year: 'numeric' });
const selectedDateFormatter = new Intl.DateTimeFormat('ru-RU', { day: 'numeric', month: 'long' });
const weekDayLabels = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];

const getColumnValue = (item, column) => (typeof column.render === 'function' ? column.render(item) : item[column.key] || '-');

const getCurrentUserId = (userData) =>
  userData?.user_id || userData?.sub || userData?.id || userData?.oid || '';

const getPreviewSource = (image) => {
  const candidate = image?.file || image?.storage_key || '';

  if (!candidate) {
    return '';
  }

  if (/^https?:\/\//i.test(candidate) || candidate.startsWith('data:')) {
    return candidate;
  }

  return `${API_BASE_URL}/${candidate.replace(/^\/+/, '')}`;
};

const buildItemCalendarMap = (items) => {
  const map = new Map();

  items.forEach((item) => {
    const dateKey = toDateKey(item.create_at);
    if (!dateKey) return;
    const currentItems = map.get(dateKey) || [];
    currentItems.push(item);
    map.set(dateKey, currentItems);
  });

  return map;
};

const buildAvailabilityMap = (items) => {
  const map = new Map();

  items.forEach((item) => {
    const start = new Date(item.start_time);
    const end = new Date(item.end_time);

    if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) {
      return;
    }

    const cursor = new Date(start.getFullYear(), start.getMonth(), start.getDate());
    const lastDay = new Date(end.getFullYear(), end.getMonth(), end.getDate());

    while (cursor <= lastDay) {
      const key = toDateKey(cursor);
      const currentItems = map.get(key) || [];
      currentItems.push(item);
      map.set(key, currentItems);
      cursor.setDate(cursor.getDate() + 1);
    }
  });

  return map;
};

const normalizeResourceKind = (value) => {
  if (!value) {
    return '';
  }

  const normalized = String(value).trim().toLowerCase().replace(/[_\s]+/g, '-');
  const matchedEntry = Object.entries(resourceKindAliases).find(([, aliases]) => aliases.includes(normalized));
  return matchedEntry ? matchedEntry[0] : normalized;
};

const getProjectResourceIds = (resources, resourceKey) =>
  new Set(
    resources
      .filter((resource) => normalizeResourceKind(resource.resource_kind || resource.resource_type) === resourceKey)
      .map((resource) => resource.resource_id)
      .filter(Boolean),
  );

const rangesOverlap = (leftStart, leftEnd, rightStart, rightEnd) =>
  !(leftEnd < rightStart || leftStart > rightEnd);

const buildCalendarDays = (visibleMonth, itemMap, selectedDateKey, todayKey) => {
  const firstDayOfMonth = new Date(visibleMonth.getFullYear(), visibleMonth.getMonth(), 1);
  const firstWeekDay = (firstDayOfMonth.getDay() + 6) % 7;
  const gridStart = new Date(firstDayOfMonth);
  gridStart.setDate(firstDayOfMonth.getDate() - firstWeekDay);

  return Array.from({ length: 35 }, (_, index) => {
    const date = new Date(gridStart);
    date.setDate(gridStart.getDate() + index);
    const dateKey = toDateKey(date);
    const dayItems = itemMap.get(dateKey) || [];

    return {
      date,
      dateKey,
      label: date.getDate(),
      isCurrentMonth: date.getMonth() === visibleMonth.getMonth(),
      isToday: dateKey === todayKey,
      isSelected: dateKey === selectedDateKey,
      itemCount: dayItems.length,
    };
  });
};

const getWindowPayload = (windowForm) => {
  const start_time = toIsoDateTime(windowForm.startTime);
  const end_time = toIsoDateTime(windowForm.endTime);

  if (!start_time || !end_time) {
    toast.error('Укажите корректные дату и время');
    return null;
  }

  if (new Date(start_time) >= new Date(end_time)) {
    toast.error('Время окончания должно быть позже времени начала');
    return null;
  }

  return { start_time, end_time };
};

const CircleIconButton = ({ children, title }) => (
  <button type="button" className="projects-icon-circle" title={title} aria-label={title}>
    {children}
  </button>
);

const MicrophoneIcon = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true">
    <path d="M12 3a3 3 0 0 0-3 3v6a3 3 0 1 0 6 0V6a3 3 0 0 0-3-3Z" />
    <path d="M6 11a6 6 0 0 0 12 0" />
    <path d="M12 17v4" />
    <path d="M8 21h8" />
  </svg>
);

const CameraIcon = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true">
    <path d="M4 8h4l1.5-2h5L16 8h4v10H4z" />
    <circle cx="12" cy="13" r="3.5" />
  </svg>
);

const TripodIcon = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true">
    <path d="M12 4v7" />
    <path d="M9 11h6" />
    <path d="M12 4l4 7H8z" />
    <path d="M12 11l-5 9" />
    <path d="M12 11l5 9" />
    <path d="M12 11v9" />
  </svg>
);

const LightIcon = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true">
    <path d="M12 3a6 6 0 0 0-4 10.5c.9.8 1.5 1.9 1.8 3h4.4c.3-1.1.9-2.2 1.8-3A6 6 0 0 0 12 3Z" />
    <path d="M10 19h4" />
    <path d="M10.5 21h3" />
  </svg>
);

const SoundIcon = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true">
    <path d="M4 10v4" />
    <path d="M8 7v10" />
    <path d="M12 5v14" />
    <path d="M16 7v10" />
    <path d="M20 10v4" />
  </svg>
);

const PropsIcon = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true">
    <path d="M6 7.5a2.5 2.5 0 1 1 5 0c0 1.4-1.1 2.5-2.5 2.5S6 8.9 6 7.5Z" />
    <path d="M13 6a2 2 0 1 1 4 0c0 1.1-.9 2-2 2s-2-.9-2-2Z" />
    <path d="M5 18v-2.5c0-2 1.6-3.5 3.5-3.5h0c2 0 3.5 1.6 3.5 3.5V18" />
    <path d="M12.5 18v-2c0-1.7 1.3-3 3-3h0c1.7 0 3 1.3 3 3v2" />
  </svg>
);

const ListIcon = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true">
    <path d="M8 7h12" />
    <path d="M8 12h12" />
    <path d="M8 17h12" />
    <path d="M4 7h.01" />
    <path d="M4 12h.01" />
    <path d="M4 17h.01" />
  </svg>
);

const HelpIcon = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true">
    <circle cx="12" cy="12" r="9" />
    <path d="M9.5 9.5a2.5 2.5 0 1 1 4.3 1.7c-.8.8-1.8 1.3-1.8 2.8" />
    <path d="M12 17h.01" />
  </svg>
);

const BellIcon = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true">
    <path d="M7 10a5 5 0 1 1 10 0v3.5l1.5 2.5h-13L7 13.5z" />
    <path d="M10 18a2 2 0 0 0 4 0" />
  </svg>
);

const ArrowIcon = ({ direction = 'right' }) => (
  <svg viewBox="0 0 24 24" aria-hidden="true" className={`projects-arrow projects-arrow-${direction}`}>
    <path d="M5 12h14" />
    <path d="M13 6l6 6-6 6" />
  </svg>
);

const PhotoIcon = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true">
    <rect x="3" y="5" width="18" height="14" rx="2" />
    <path d="M8 13l2.5-2.5L16 16" />
    <circle cx="15.5" cy="9" r="1.5" />
  </svg>
);

const getResourceIcon = (resourceKey) => {
  switch (resourceKey) {
    case 'microfons':
      return <MicrophoneIcon />;
    case 'cameras':
      return <CameraIcon />;
    case 'camera-tripods':
    case 'light-tripods':
      return <TripodIcon />;
    case 'lights':
      return <LightIcon />;
    case 'sounds':
      return <SoundIcon />;
    case 'requisites':
      return <PropsIcon />;
    default:
      return <ListIcon />;
  }
};

const Projects = () => {
  const navigate = useNavigate();
  const { userData } = useAuth();
  const {
    activeProject,
    activeProjectId,
    refreshProjects,
  } = useProjectContext();
  const [activeResource, setActiveResource] = useState(resourceOrder[0]);
  const [form, setForm] = useState(createInitialResourceForm);
  const [editingId, setEditingId] = useState(null);
  const [allItems, setAllItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [deletingId, setDeletingId] = useState(null);
  const [pagination, setPagination] = useState({ page: 1, pageSize: 20, totalPages: 1, totalCount: 0 });
  const [selectedItemId, setSelectedItemId] = useState(null);
  const [freeTimeForm, setFreeTimeForm] = useState(createDefaultTimeWindowForm);
  const [selectedFreeTimeDateKeys, setSelectedFreeTimeDateKeys] = useState([]);
  const [addedFreeTimeDateKeysByItem, setAddedFreeTimeDateKeysByItem] = useState({});
  const [selectedItemFreeTimes, setSelectedItemFreeTimes] = useState([]);
  const [isSelectedItemFreeTimesLoading, setIsSelectedItemFreeTimesLoading] = useState(false);
  const [reserveForm, setReserveForm] = useState(createInitialWindowForm);
  const [isSubmittingFreeTime, setIsSubmittingFreeTime] = useState(false);
  const [isSubmittingReservation, setIsSubmittingReservation] = useState(false);
  const [images, setImages] = useState([]);
  const [requisiteTableImagesById, setRequisiteTableImagesById] = useState({});
  const [imageForm, setImageForm] = useState(createInitialImageForm);
  const [imageInputKey, setImageInputKey] = useState(0);
  const [isImagesLoading, setIsImagesLoading] = useState(false);
  const [isUploadingImage, setIsUploadingImage] = useState(false);
  const [selectedImage, setSelectedImage] = useState(null);
  const [loadingImageId, setLoadingImageId] = useState(null);
  const [removingImageId, setRemovingImageId] = useState(null);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [visibleMonth, setVisibleMonth] = useState(() => startOfMonth(new Date()));
  const [selectedDateKey, setSelectedDateKey] = useState(() => toDateKey(new Date()));
  const [activeDateFilterKey, setActiveDateFilterKey] = useState(null);
  const [projectResources, setProjectResources] = useState([]);
  const [isProjectResourcesLoading, setIsProjectResourcesLoading] = useState(false);

  const currentResource = useMemo(() => resourceMeta[activeResource], [activeResource]);
  const todayKey = useMemo(() => toDateKey(new Date()), []);
  const currentUserId = useMemo(() => getCurrentUserId(userData), [userData]);
  const activeProjectTitle = activeProject?.title || 'Проект не выбран';
  const workspaceStatusLabel = !activeProject
    ? 'Не выбран'
    : isProjectResourcesLoading || loading
      ? 'Загрузка'
      : 'Активен';
  const projectResourceIds = useMemo(
    () => getProjectResourceIds(projectResources, activeResource),
    [activeResource, projectResources],
  );
  const items = useMemo(() => {
    if (!activeProjectId || projectResourceIds.size === 0) {
      return [];
    }

    return allItems.filter((item) => projectResourceIds.has(item.oid));
  }, [activeProjectId, allItems, projectResourceIds]);

  const selectedItem = useMemo(
    () => items.find((item) => item.oid === selectedItemId) || null,
    [items, selectedItemId],
  );

  const itemsByDate = useMemo(() => buildItemCalendarMap(items), [items]);
  const calendarDays = useMemo(
    () => buildCalendarDays(visibleMonth, itemsByDate, selectedDateKey, todayKey),
    [itemsByDate, selectedDateKey, todayKey, visibleMonth],
  );
  const dateFilteredItems = useMemo(
    () => (activeDateFilterKey ? items.filter((item) => toDateKey(item.create_at) === activeDateFilterKey) : items),
    [activeDateFilterKey, items],
  );
  const filteredItems = useMemo(() => {
    if (activeDateFilterKey) {
      return dateFilteredItems;
    }

    const startIndex = (pagination.page - 1) * pagination.pageSize;
    return dateFilteredItems.slice(startIndex, startIndex + pagination.pageSize);
  }, [activeDateFilterKey, dateFilteredItems, pagination.page, pagination.pageSize]);
  const selectedDayItems = useMemo(
    () => itemsByDate.get(activeDateFilterKey || selectedDateKey) || [],
    [activeDateFilterKey, itemsByDate, selectedDateKey],
  );
  const selectedFreeTimeDateSet = useMemo(
    () => new Set(selectedFreeTimeDateKeys),
    [selectedFreeTimeDateKeys],
  );
  const selectedItemFreeTimesByDate = useMemo(
    () => buildAvailabilityMap(selectedItemFreeTimes),
    [selectedItemFreeTimes],
  );
  const addedFreeTimeDateSet = useMemo(
    () =>
      new Set([
        ...selectedItemFreeTimesByDate.keys(),
        ...(selectedItemId ? addedFreeTimeDateKeysByItem[selectedItemId] || [] : []),
      ]),
    [addedFreeTimeDateKeysByItem, selectedItemFreeTimesByDate, selectedItemId],
  );
  const selectedFreeTimeDatesLabel = useMemo(
    () =>
      selectedFreeTimeDateKeys
        .map((dateKey) => selectedDateFormatter.format(fromDateKey(dateKey)))
        .join(', '),
    [selectedFreeTimeDateKeys],
  );
  const projectResourceSummary = useMemo(
    () =>
      projectResources.reduce((acc, resource) => {
        const key = resource.resource_kind || resource.resource_type || 'resource';
        acc[key] = (acc[key] || 0) + 1;
        return acc;
      }, {}),
    [projectResources],
  );
  const projectResourceSummaryLabel = useMemo(() => {
    const entries = Object.entries(projectResourceSummary);

    if (entries.length === 0) {
      return 'Ресурсы проекта пока не назначены';
    }

    return entries.map(([kind, count]) => `${kind}: ${count}`).join(', ');
  }, [projectResourceSummary]);
  const categoryCounts = useMemo(
    () =>
      resourceOrder.reduce((acc, resourceKey) => {
        acc[resourceKey] = getProjectResourceIds(projectResources, resourceKey).size;
        return acc;
      }, {}),
    [projectResources],
  );
  const totalWindows = useMemo(
    () =>
      projectResources.reduce(
        (acc, resource) => acc + (Array.isArray(resource.windows) ? resource.windows.length : 0),
        0,
      ),
    [projectResources],
  );
  const totalReservedWindows = useMemo(
    () =>
      projectResources.reduce(
        (acc, resource) =>
          acc + (Array.isArray(resource.windows)
            ? resource.windows.filter((window) => /(reserved|booked|busy|taken|occupied)/i.test(window.status || '')).length
            : 0),
        0,
      ),
    [projectResources],
  );
  const totalAvailableWindows = Math.max(totalWindows - totalReservedWindows, 0);
  const selectedDayStatLabel = activeDateFilterKey
    ? selectedDateFormatter.format(new Date(`${activeDateFilterKey}T00:00:00`))
    : selectedDateFormatter.format(new Date(`${selectedDateKey}T00:00:00`));
  const isWorkspaceLoading = loading || isProjectResourcesLoading;

  const handleScrollToForm = useCallback(() => {
    document.getElementById('workspace-resource-form')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }, []);

  const resetForm = useCallback(() => {
    setForm(createInitialResourceForm());
    setEditingId(null);
  }, []);

  const resetManagementState = useCallback(() => {
    setSelectedItemId(null);
    setFreeTimeForm(createDefaultTimeWindowForm());
    setSelectedFreeTimeDateKeys([]);
    setSelectedItemFreeTimes([]);
    setIsSelectedItemFreeTimesLoading(false);
    setReserveForm(createInitialWindowForm());
    setImages([]);
    setRequisiteTableImagesById({});
    setImageForm(createInitialImageForm());
    setImageInputKey((prev) => prev + 1);
    setSelectedImage(null);
  }, []);

  useEffect(() => {
    refreshProjects();
  }, [refreshProjects]);

  useEffect(() => {
    resetForm();
    resetManagementState();
    setActiveDateFilterKey(null);
    setAddedFreeTimeDateKeysByItem({});
    setProjectResources([]);
  }, [activeProjectId, resetForm, resetManagementState]);

  useEffect(() => {
    if (!activeProjectId || !currentUserId) {
      setProjectResources([]);
      return;
    }

    let isMounted = true;
    setIsProjectResourcesLoading(true);

    getProjectUserResources(activeProjectId, currentUserId)
      .then((response) => {
        if (!isMounted) {
          return;
        }

        setProjectResources(Array.isArray(response?.resources) ? response.resources : []);
      })
      .catch(() => {
        if (!isMounted) {
          return;
        }

        setProjectResources([]);
      })
      .finally(() => {
        if (isMounted) {
          setIsProjectResourcesLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [activeProjectId, currentUserId]);

  const fetchItems = useCallback(async () => {
    if (!activeProjectId) {
      setAllItems([]);
      setPagination((prev) => ({ ...prev, page: 1, totalPages: 1, totalCount: 0 }));
      return;
    }

    setLoading(true);

    try {
      const collectedItems = [];
      let page = 1;
      let totalPages = 1;

      do {
        const response = await currentResource.list({
          page,
          pageSize: RESOURCE_PAGE_SIZE,
          sortBy: 'create_at',
          sortDir: 'desc',
        });

        collectedItems.push(...(response.items || []));
        totalPages = response.pages || 1;
        page += 1;
      } while (page <= totalPages);

      setAllItems(collectedItems);
    } catch (error) {
      toast.error(error.message || `Не удалось загрузить ${currentResource.label.toLowerCase()}`);
    } finally {
      setLoading(false);
    }
  }, [activeProjectId, currentResource]);

  const loadSelectedItemFreeTimes = useCallback(
    async (itemId) => {
      if (!itemId) {
        setSelectedItemFreeTimes([]);
        return;
      }

      setIsSelectedItemFreeTimesLoading(true);

      try {
        const response = await currentResource.listFreeTimes(itemId);
        setSelectedItemFreeTimes(response.items || []);
      } catch (error) {
        setSelectedItemFreeTimes([]);
        toast.error(error.message || 'Не удалось загрузить окна доступности объекта');
      } finally {
        setIsSelectedItemFreeTimesLoading(false);
      }
    },
    [currentResource],
  );

  const loadRequisiteImages = useCallback(async (requisiteId) => {
    if (!requisiteId) {
      setImages([]);
      return [];
    }

    setIsImagesLoading(true);

    try {
      const response = await listRequisiteImages(requisiteId);
      const nextImages = response.items || [];
      setImages(nextImages);
      return nextImages;
    } catch (error) {
      toast.error(error.message || 'Не удалось загрузить изображения реквизита');
      setImages([]);
      return [];
    } finally {
      setIsImagesLoading(false);
    }
  }, []);

  const loadRequisiteTableImages = useCallback(async (requisites) => {
    if (activeResource !== 'requisites' || requisites.length === 0) {
      setRequisiteTableImagesById({});
      return;
    }

    const results = await Promise.allSettled(
      requisites.map(async (item) => {
        const response = await listRequisiteImages(item.oid);
        return [item.oid, response.items || []];
      }),
    );

    const nextImagesById = {};
    results.forEach((result) => {
      if (result.status === 'fulfilled') {
        const [requisiteId, nextImages] = result.value;
        nextImagesById[requisiteId] = nextImages;
      }
    });

    setRequisiteTableImagesById(nextImagesById);
  }, [activeResource]);

  useEffect(() => {
    fetchItems();
  }, [fetchItems]);

  useEffect(() => {
    if (!selectedItemId) {
      return;
    }

    if (!items.some((item) => item.oid === selectedItemId)) {
      resetManagementState();
    }
  }, [items, resetManagementState, selectedItemId]);

  useEffect(() => {
    if (!selectedItemId) {
      setSelectedItemFreeTimes([]);
      return;
    }

    loadSelectedItemFreeTimes(selectedItemId);
  }, [loadSelectedItemFreeTimes, selectedItemId]);

  useEffect(() => {
    if (activeResource !== 'requisites' || !selectedItem) {
      setImages([]);
      setSelectedImage(null);
      return;
    }

    loadRequisiteImages(selectedItem.oid);
  }, [activeResource, loadRequisiteImages, selectedItem]);

  useEffect(() => {
    loadRequisiteTableImages(items);
  }, [items, loadRequisiteTableImages]);

  useEffect(() => {
    if (activeDateFilterKey && !items.some((item) => toDateKey(item.create_at) === activeDateFilterKey)) {
      setActiveDateFilterKey(null);
    }
  }, [activeDateFilterKey, items]);

  useEffect(() => {
    setPagination((prev) => {
      const totalCount = items.length;
      const totalPages = Math.max(1, Math.ceil(totalCount / prev.pageSize));
      const page = Math.min(prev.page, totalPages);

      if (prev.totalCount === totalCount && prev.totalPages === totalPages && prev.page === page) {
        return prev;
      }

      return {
        ...prev,
        page,
        totalPages,
        totalCount,
      };
    });
  }, [items]);

  const switchResource = (nextResource) => {
    if (nextResource === activeResource) {
      return;
    }

    setActiveResource(nextResource);
    resetForm();
    resetManagementState();
    setPagination((prev) => ({ ...prev, page: 1, totalPages: 1, totalCount: 0 }));
    setVisibleMonth(startOfMonth(new Date()));
    setSelectedDateKey(toDateKey(new Date()));
    setActiveDateFilterKey(null);
  };

  const handleChange = (event) => {
    const { name, value } = event.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleWindowChange = (setter) => (event) => {
    const { name, value } = event.target;
    setter((prev) => ({ ...prev, [name]: value }));
  };

  const handleImageFieldChange = (event) => {
    const { name, value, files } = event.target;
    setImageForm((prev) => ({ ...prev, [name]: name === 'file' ? files?.[0] || null : value }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();

    const payload = currentResource.buildPayload(form);
    if (!payload.title || !payload.description || !payload.type || (activeResource === 'requisites' && !payload.size)) {
      toast.error('Заполните обязательные поля');
      return;
    }

    setSubmitting(true);

    try {
      if (editingId) {
        await currentResource.update(editingId, payload);
        toast.success(`${currentResource.one} обновлен`);
      } else {
        await currentResource.create(payload);
        toast.success(`${currentResource.one} добавлен`);
      }

      resetForm();
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) {
        toast.error('Объект не найден, список обновлен');
        resetForm();
      } else {
        toast.error(error.message || 'Не удалось сохранить данные');
      }
    } finally {
      await fetchItems();
      setSubmitting(false);
    }
  };

  const handleEdit = (item) => {
    setEditingId(item.oid);
    setForm({
      title: item.title || '',
      description: item.description || '',
      type: item.type || '',
      size: item.size || '',
    });
    setSelectedItemId(item.oid);
  };

  const handleDelete = async (itemId) => {
    if (!window.confirm('Удалить выбранный объект?')) {
      return;
    }

    setDeletingId(itemId);

    try {
      await currentResource.remove(itemId);
      toast.success(`${currentResource.one} удален`);

      if (selectedItemId === itemId) {
        resetManagementState();
      }

      await fetchItems();
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) {
        toast.error('Объект уже удален, список обновлен');
        if (selectedItemId === itemId) {
          resetManagementState();
        }
      } else {
        toast.error(error.message || 'Не удалось удалить объект');
      }
      await fetchItems();
    } finally {
      setDeletingId(null);
    }
  };

  const handleSelectItem = (item) => {
    setSelectedItemId(item.oid);
    setFreeTimeForm(createDefaultTimeWindowForm());
    setSelectedFreeTimeDateKeys([selectedDateKey]);
    setReserveForm(createInitialWindowForm());
    setImageForm(createInitialImageForm());
    setImageInputKey((prev) => prev + 1);
    setSelectedImage(null);
  };

  const handleAddFreeTime = async (event) => {
    event.preventDefault();

    if (!selectedItem) {
      toast.error('Сначала выберите объект из таблицы');
      return;
    }

    if (selectedFreeTimeDateKeys.length === 0) {
      toast.error('Выберите хотя бы один день на календаре');
      return;
    }

    const firstStart = buildLocalDateTime(selectedFreeTimeDateKeys[0], freeTimeForm.startTime);
    const firstEnd = buildLocalDateTime(selectedFreeTimeDateKeys[0], freeTimeForm.endTime);

    if (Number.isNaN(firstStart.getTime()) || Number.isNaN(firstEnd.getTime())) {
      toast.error('Укажите корректное время');
      return;
    }

    if (firstStart >= firstEnd) {
      toast.error('Время окончания должно быть позже времени начала');
      return;
    }

    const conflictingDateKeys = selectedFreeTimeDateKeys.filter((dateKey) => {
      const start = buildLocalDateTime(dateKey, freeTimeForm.startTime);
      const end = buildLocalDateTime(dateKey, freeTimeForm.endTime);
      const dayWindows = selectedItemFreeTimesByDate.get(dateKey) || [];

      return dayWindows.some((window) =>
        rangesOverlap(start, end, new Date(window.start_time), new Date(window.end_time)),
      );
    });

    if (conflictingDateKeys.length > 0) {
      toast.error(
        `Интервал пересекается с уже добавленными окнами: ${
          conflictingDateKeys.map((dateKey) => selectedDateFormatter.format(fromDateKey(dateKey))).join(', ')
        }`,
      );
      return;
    }

    setIsSubmittingFreeTime(true);

    try {
      await Promise.all(
        selectedFreeTimeDateKeys.map((dateKey) => {
          const start = buildLocalDateTime(dateKey, freeTimeForm.startTime);
          const end = buildLocalDateTime(dateKey, freeTimeForm.endTime);
          return currentResource.addFreeTime(selectedItem.oid, {
            start_time: start.toISOString(),
            end_time: end.toISOString(),
          });
        }),
      );
      setAddedFreeTimeDateKeysByItem((prev) => {
        const currentKeys = new Set(prev[selectedItem.oid] || []);
        selectedFreeTimeDateKeys.forEach((dateKey) => currentKeys.add(dateKey));
        return { ...prev, [selectedItem.oid]: [...currentKeys].sort() };
      });
      toast.success(`Окна доступности добавлены: ${selectedFreeTimeDateKeys.length}`);
      setFreeTimeForm(createDefaultTimeWindowForm());
      setSelectedFreeTimeDateKeys([]);
      await loadSelectedItemFreeTimes(selectedItem.oid);
    } catch (error) {
      toast.error(error.message || 'Не удалось добавить окно доступности');
    } finally {
      setIsSubmittingFreeTime(false);
    }
  };

  const handleReserve = async (event) => {
    event.preventDefault();

    if (!selectedItem) {
      toast.error('Сначала выберите объект из таблицы');
      return;
    }

    const payload = getWindowPayload(reserveForm);
    if (!payload) {
      return;
    }

    setIsSubmittingReservation(true);

    try {
      await reserveAvailability({
        request_id: crypto.randomUUID(),
        owner_id: selectedItem.user_id,
        obj_id: selectedItem.oid,
        ...payload,
      });
      toast.success('Бронирование отправлено');
      setReserveForm(createInitialWindowForm());
    } catch (error) {
      toast.error(error.message || 'Не удалось забронировать окно');
    } finally {
      setIsSubmittingReservation(false);
    }
  };

  const handleImageSubmit = async (event) => {
    event.preventDefault();

    if (!selectedItem) {
      toast.error('Сначала выберите реквизит');
      return;
    }

    if (!imageForm.file || !imageForm.title.trim() || !imageForm.description.trim()) {
      toast.error('Заполните данные изображения и выберите файл');
      return;
    }

    setIsUploadingImage(true);

    try {
      await addRequisiteImage(selectedItem.oid, {
        file: imageForm.file,
        title: imageForm.title.trim(),
        description: imageForm.description.trim(),
      });
      toast.success('Изображение загружено');
      setImageForm(createInitialImageForm());
      setImageInputKey((prev) => prev + 1);
      const nextImages = await loadRequisiteImages(selectedItem.oid);
      setRequisiteTableImagesById((prev) => ({ ...prev, [selectedItem.oid]: nextImages }));
    } catch (error) {
      toast.error(error.message || 'Не удалось загрузить изображение');
    } finally {
      setIsUploadingImage(false);
    }
  };

  const handleImageDetails = async (imageId) => {
    if (!selectedItem) {
      return;
    }

    setLoadingImageId(imageId);

    try {
      const image = await getRequisiteImage(selectedItem.oid, imageId);
      setSelectedImage(image);
    } catch (error) {
      toast.error(error.message || 'Не удалось получить информацию об изображении');
    } finally {
      setLoadingImageId(null);
    }
  };

  const handleRemoveImage = async (imageId) => {
    if (!selectedItem || !window.confirm('Удалить изображение реквизита?')) {
      return;
    }

    setRemovingImageId(imageId);

    try {
      await removeRequisiteImage(selectedItem.oid, imageId);
      toast.success('Изображение удалено');
      setImages((prev) => prev.filter((image) => image.oid !== imageId));
      setRequisiteTableImagesById((prev) => ({
        ...prev,
        [selectedItem.oid]: (prev[selectedItem.oid] || []).filter((image) => image.oid !== imageId),
      }));
      setSelectedImage((prev) => (prev?.oid === imageId ? null : prev));
    } catch (error) {
      toast.error(error.message || 'Не удалось удалить изображение');
    } finally {
      setRemovingImageId(null);
    }
  };

  const handlePageChange = (newPage) => {
    if (newPage < 1 || newPage > pagination.totalPages || newPage === pagination.page) {
      return;
    }

    setPagination((prev) => ({ ...prev, page: newPage }));
  };

  const handleCalendarDayClick = (dateKey, date) => {
    setSelectedDateKey(dateKey);
    setVisibleMonth(startOfMonth(date));

    if (selectedItem) {
      setActiveDateFilterKey(null);
      setSelectedFreeTimeDateKeys((prev) => {
        if (prev.includes(dateKey)) {
          return prev.filter((key) => key !== dateKey);
        }

        return [...prev, dateKey].sort();
      });
      return;
    }

    setActiveDateFilterKey((current) => (current === dateKey ? null : dateKey));
  };

  const activeDayLabel = activeDateFilterKey
    ? selectedDateFormatter.format(new Date(`${activeDateFilterKey}T00:00:00`))
    : null;

  return (
    <section className="projects-wrapper">
      <div className={`projects-page projects-dashboard-layout${isSidebarCollapsed ? ' is-sidebar-collapsed' : ''}`}>
        <div className="dashboard-panel projects-overview-panel">
          <div className="projects-overview-copy">
            <span className="projects-panel-eyebrow">Рабочая область</span>
            <h1>{activeProjectTitle}</h1>
            <p>
              {activeProject
                ? `Открыт раздел: ${currentResource.label}. ${projectResourceSummaryLabel}.`
                : 'Выберите проект, чтобы рабочая область показала нужный контекст.'}
            </p>
            <div className="project-switcher-inline project-switcher-readonly">
              <div className="active-project-readout">
                <span>Проект</span>
                <strong>{activeProject ? activeProject.title : 'Выберите проект'}</strong>
              </div>
              <button type="button" className="ghost-action-btn" onClick={() => navigate('/my-projects')}>
                Перейти к проектам
              </button>
            </div>
          </div>

          <div className="projects-overview-controls">
            <div className="projects-status-chip-wrap">
              <span>Статус</span>
              <strong className="projects-status-chip">{workspaceStatusLabel}</strong>
              <div className="projects-header-tools" aria-hidden="true">
                <CircleIconButton title="Помощь">
                  <HelpIcon />
                </CircleIconButton>
                <CircleIconButton title="Уведомления">
                  <BellIcon />
                </CircleIconButton>
                <CircleIconButton title="AI">
                  <strong>AI</strong>
                </CircleIconButton>
              </div>
            </div>

            <div className="projects-overview-stats">
              <article className="projects-stat-card">
                <span>Объектов</span>
                <strong>{projectResources.length}</strong>
              </article>
              <article className="projects-stat-card">
                <span>Доступно</span>
                <strong>{totalAvailableWindows}</strong>
              </article>
              <article className="projects-stat-card">
                <span>Занято</span>
                <strong>{totalReservedWindows}</strong>
              </article>
            </div>

            <div className="projects-overview-actions">
              <button
                type="button"
                className="secondary-btn projects-layout-toggle"
                onClick={() => setIsSidebarCollapsed((prev) => !prev)}
                aria-expanded={!isSidebarCollapsed}
                aria-controls="projects-categories-panel"
              >
                <span>{isSidebarCollapsed ? 'Показать категории' : 'Скрыть категории'}</span>
              </button>
            </div>
          </div>
        </div>
        <aside id="projects-categories-panel" className="dashboard-panel projects-sidebar">
          <div className="projects-sidebar-heading">
            <span className="projects-panel-eyebrow">Разделы инвентаря</span>
            <h1>Категории</h1>
          </div>

          <div className="projects-sidebar-nav" role="tablist" aria-label="Категории инвентаря">
            {resourceOrder.map((resourceKey) => {
              const resource = resourceMeta[resourceKey];
              const isActive = resourceKey === activeResource;

              return (
                <button
                  key={resourceKey}
                  type="button"
                  className={`projects-sidebar-button ${isActive ? 'is-active' : ''}`}
                  onClick={() => switchResource(resourceKey)}
                >
                  <span className="projects-sidebar-button-icon" aria-hidden="true">
                    {getResourceIcon(resourceKey)}
                  </span>
                  <span>{resource.label}</span>
                  <small>{isActive ? `${categoryCounts[resourceKey] || 0} позиций` : 'Открыть'}</small>
                </button>
              );
            })}
          </div>

          <div className="projects-sidebar-note">
            <strong>{currentResource.label}</strong>
            <span>{categoryCounts[activeResource] || 0} позиций</span>
          </div>
        </aside>

        <div className="projects-center-column">
          <section className="dashboard-panel project-context-panel">
            <div className="section-heading project-context-heading">
              <div>
                <span className="projects-panel-eyebrow">Данные проекта</span>
                <h2>{activeProject ? activeProject.title : 'Проект не выбран'}</h2>
              </div>
              <p>
                {isProjectResourcesLoading
                  ? 'Загружаем данные проекта...'
                  : `Ресурсов в проекте: ${projectResources.length}`}
              </p>
            </div>

            <div className="project-context-summary-grid">
              <article className="project-context-summary-card is-blue">
                <span>Объектов</span>
                <strong>{projectResources.length}</strong>
              </article>
              <article className="project-context-summary-card">
                <span>Забронировано</span>
                <strong>{totalReservedWindows}</strong>
              </article>
              <article className="project-context-summary-card is-green">
                <span>Доступно</span>
                <strong>{totalAvailableWindows}</strong>
              </article>
            </div>

            {activeProject ? (
              <>
                <div className="project-context-grid">
                  {projectResources.slice(0, 6).map((resource) => (
                    <article key={`${resource.resource_kind}-${resource.resource_id}`} className="project-context-card">
                      <span>{resource.resource_kind || resource.resource_type || 'Ресурс'}</span>
                      <strong>{resource.title}</strong>
                      <p>{resource.description || 'Без описания'}</p>
                      <small>
                        Окон доступности: {Array.isArray(resource.windows) ? resource.windows.length : 0}
                      </small>
                    </article>
                  ))}
                </div>

                {!isProjectResourcesLoading && projectResources.length === 0 ? (
                  <p className="helper-note">
                    Для этого проекта пока не назначены ресурсы или backend еще не вернул их для вашей роли.
                  </p>
                ) : null}
              </>
            ) : (
              <p className="helper-note">Создайте или выберите проект на странице проектов.</p>
            )}
          </section>
          <section className="dashboard-panel">
            <div className="section-heading">
              <h2>{editingId ? `Редактирование: ${currentResource.one}` : `Новый объект: ${currentResource.one}`}</h2>
              <p>Центральная панель отвечает за создание и редактирование элементов выбранной категории.</p>
            </div>

            <form id="workspace-resource-form" className="stacked-form resource-form" onSubmit={handleSubmit}>
              <div className="projects-resource-form-grid">
                <div className="projects-resource-form-fields">
                  <label className="field-block">
                    <span>Название</span>
                    <input
                      name="title"
                      value={form.title}
                      onChange={handleChange}
                      placeholder={currentResource.placeholders.title}
                    />
                  </label>

                  <div className="grid-two-columns">
                    <label className="field-block">
                      <span>Тип</span>
                      <input
                        name="type"
                        value={form.type}
                        onChange={handleChange}
                        placeholder={currentResource.placeholders.type}
                      />
                    </label>

                    {activeResource === 'requisites' ? (
                      <label className="field-block">
                        <span>Размер</span>
                        <input
                          name="size"
                          value={form.size}
                          onChange={handleChange}
                          placeholder={currentResource.placeholders.size}
                        />
                      </label>
                    ) : (
                      <div className="projects-form-placeholder" aria-hidden="true" />
                    )}
                  </div>
                </div>

                <label className="field-block projects-form-description">
                  <span>Описание</span>
                  <textarea
                    name="description"
                    value={form.description}
                    onChange={handleChange}
                    placeholder={currentResource.placeholders.description}
                    rows={4}
                  />
                </label>

                <div className="projects-upload-tile" aria-hidden="true">
                  <PhotoIcon />
                  <strong>Добавьте фото</strong>
                  <span>(необязательно)</span>
                  <small>JPG, PNG до 5 МБ</small>
                </div>
              </div>

              <div className="inline-actions">
                <button type="submit" className="profile-save-btn compact" disabled={submitting}>
                  {submitting ? 'Сохраняем...' : editingId ? 'Сохранить изменения' : 'Добавить объект'}
                </button>
                <button
                  type="button"
                  className="secondary-btn"
                  onClick={resetForm}
                  disabled={submitting || (!editingId && !form.title && !form.description && !form.type && !form.size)}
                >
                  Очистить
                </button>
              </div>
            </form>
          </section>

          <section className="dashboard-panel management-card">
            <div className="section-heading">
              <h2>Управление выбранным объектом</h2>
              <p>
                {selectedItem
                  ? `Сейчас выбран: ${selectedItem.title}`
                  : 'Выберите запись справа, чтобы открыть управление доступностью, бронированием и медиа.'}
              </p>
            </div>

            {selectedItem ? (
              <>
                <div className="selected-entity-summary">
                  <div>
                    <strong>{selectedItem.title}</strong>
                    <p>{selectedItem.description || 'Без описания'}</p>
                  </div>

                  <dl className="entity-meta-list">
                    <div>
                      <dt>Тип</dt>
                      <dd>{selectedItem.type || '-'}</dd>
                    </div>
                    {activeResource === 'requisites' ? (
                      <div>
                        <dt>Размер</dt>
                        <dd>{selectedItem.size || '-'}</dd>
                      </div>
                    ) : null}
                    <div>
                      <dt>Создано</dt>
                      <dd>{formatDateTime(selectedItem.create_at)}</dd>
                    </div>
                  </dl>
                </div>

                <div className="management-grid projects-management-grid">
                  <section className="management-panel">
                    <h3>Добавить окно доступности</h3>
                    <p className="helper-note">
                      {isSelectedItemFreeTimesLoading
                        ? 'Загружаем уже добавленные окна объекта...'
                        : 'Выберите один или несколько дней в календаре и задайте общий интервал времени.'}
                    </p>
                    <form className="stacked-form" onSubmit={handleAddFreeTime}>
                      <div className="profile-selected-days">
                        <span>Выбрано дней: {selectedFreeTimeDateKeys.length}</span>
                        <p>{selectedFreeTimeDatesLabel || 'Нажмите на даты в календаре справа.'}</p>
                      </div>
                      <label className="field-block">
                        <span>Начало</span>
                        <input
                          type="time"
                          name="startTime"
                          value={freeTimeForm.startTime}
                          onChange={handleWindowChange(setFreeTimeForm)}
                        />
                      </label>
                      <label className="field-block">
                        <span>Окончание</span>
                        <input
                          type="time"
                          name="endTime"
                          value={freeTimeForm.endTime}
                          onChange={handleWindowChange(setFreeTimeForm)}
                        />
                      </label>
                      <button type="submit" className="profile-save-btn compact" disabled={isSubmittingFreeTime}>
                        {isSubmittingFreeTime ? 'Добавляем...' : `Добавить на ${selectedFreeTimeDateKeys.length || 0} дн.`}
                      </button>
                    </form>
                  </section>

                  <section className="management-panel">
                    <h3>Забронировать интервал</h3>
                    <p className="helper-note">Бронь отправляется на общий endpoint `availability/reserve`.</p>
                    <form className="stacked-form" onSubmit={handleReserve}>
                      <label className="field-block">
                        <span>Начало</span>
                        <input
                          type="datetime-local"
                          name="startTime"
                          value={reserveForm.startTime}
                          onChange={handleWindowChange(setReserveForm)}
                        />
                      </label>
                      <label className="field-block">
                        <span>Окончание</span>
                        <input
                          type="datetime-local"
                          name="endTime"
                          value={reserveForm.endTime}
                          onChange={handleWindowChange(setReserveForm)}
                        />
                      </label>
                      <button type="submit" className="profile-save-btn compact" disabled={isSubmittingReservation}>
                        {isSubmittingReservation ? 'Отправляем...' : 'Забронировать'}
                      </button>
                    </form>
                  </section>
                </div>

                {currentResource.supportsImages ? (
                  <section className="requisite-media-section">
                    <div className="management-panel">
                      <h3>Изображения реквизита</h3>
                      <form className="stacked-form" onSubmit={handleImageSubmit}>
                        <label className="field-block">
                          <span>Файл</span>
                          <input
                            key={imageInputKey}
                            type="file"
                            name="file"
                            accept="image/*"
                            onChange={handleImageFieldChange}
                          />
                        </label>

                        <div className="grid-two-columns">
                          <label className="field-block">
                            <span>Название</span>
                            <input
                              name="title"
                              value={imageForm.title}
                              onChange={handleImageFieldChange}
                              placeholder="Основное фото"
                            />
                          </label>
                          <label className="field-block">
                            <span>Описание</span>
                            <input
                              name="description"
                              value={imageForm.description}
                              onChange={handleImageFieldChange}
                              placeholder="Крупный план"
                            />
                          </label>
                        </div>

                        <button type="submit" className="profile-save-btn compact" disabled={isUploadingImage}>
                          {isUploadingImage ? 'Загружаем...' : 'Загрузить изображение'}
                        </button>
                      </form>
                    </div>

                    <div className="media-grid">
                      <section className="management-panel">
                        <h3>Галерея</h3>
                        <p className="helper-note">
                          {isImagesLoading ? 'Загружаем изображения...' : `Всего изображений: ${images.length}`}
                        </p>
                        <div className="media-grid media-grid-compact">
                          {images.map((image) => (
                            <article key={image.oid} className="media-card">
                              {getPreviewSource(image) ? (
                                <img
                                  className="requisite-image-preview"
                                  src={getPreviewSource(image)}
                                  alt={image.title}
                                />
                              ) : null}
                              <h4>{image.title}</h4>
                              <p>{image.description}</p>
                              <div className="table-actions">
                                <button
                                  type="button"
                                  className="ghost-action-btn"
                                  onClick={() => handleImageDetails(image.oid)}
                                  disabled={loadingImageId === image.oid}
                                >
                                  {loadingImageId === image.oid ? 'Загрузка...' : 'Детали'}
                                </button>
                                <button
                                  type="button"
                                  className="ghost-action-btn danger"
                                  onClick={() => handleRemoveImage(image.oid)}
                                  disabled={removingImageId === image.oid}
                                >
                                  {removingImageId === image.oid ? 'Удаляем...' : 'Удалить'}
                                </button>
                              </div>
                            </article>
                          ))}

                          {!isImagesLoading && images.length === 0 ? (
                            <p className="helper-note">Изображения еще не добавлены.</p>
                          ) : null}
                        </div>
                      </section>

                      {selectedImage ? (
                        <section className="image-details-card">
                          <h3>Детали изображения</h3>
                          {getPreviewSource(selectedImage) ? (
                            <img
                              className="requisite-image-preview"
                              src={getPreviewSource(selectedImage)}
                              alt={selectedImage.title}
                            />
                          ) : null}
                          <dl className="details-list">
                            <div>
                              <dt>Название</dt>
                              <dd>{selectedImage.title}</dd>
                            </div>
                            <div>
                              <dt>Описание</dt>
                              <dd>{selectedImage.description}</dd>
                            </div>
                            <div>
                              <dt>MIME</dt>
                              <dd>{selectedImage.mime_type}</dd>
                            </div>
                            <div>
                              <dt>Размер файла</dt>
                              <dd>{selectedImage.size}</dd>
                            </div>
                            <div>
                              <dt>Storage key</dt>
                              <dd>{selectedImage.storage_key}</dd>
                            </div>
                            <div>
                              <dt>Создано</dt>
                              <dd>{formatDateTime(selectedImage.create_at)}</dd>
                            </div>
                          </dl>
                        </section>
                      ) : null}
                    </div>
                  </section>
                ) : null}
              </>
            ) : (
              <div className="management-panel">
                <p className="helper-note">После выбора строки здесь появятся быстрые действия для объекта.</p>
              </div>
            )}
          </section>
        </div>

        <aside className="projects-right-column">
          <section className="dashboard-panel profile-calendar-card projects-calendar-panel">
            <div className="projects-calendar-header">
              <div>
                <span className="projects-panel-eyebrow">Календарь</span>
                <h2>{monthFormatter.format(visibleMonth)}</h2>
              </div>
              <div className="profile-calendar-toolbar">
                <button
                  type="button"
                  className="ghost-action-btn"
                  onClick={() => setVisibleMonth((prev) => new Date(prev.getFullYear(), prev.getMonth() - 1, 1))}
                >
                  <ArrowIcon direction="left" />
                </button>
                <button
                  type="button"
                  className="ghost-action-btn"
                  onClick={() => setVisibleMonth((prev) => new Date(prev.getFullYear(), prev.getMonth() + 1, 1))}
                >
                  <ArrowIcon direction="right" />
                </button>
                <button type="button" className="ghost-action-btn" onClick={() => setVisibleMonth(startOfMonth(new Date()))}>
                  Сегодня
                </button>
              </div>
            </div>

            <div className="profile-weekdays">
              {weekDayLabels.map((dayLabel) => (
                <span key={dayLabel}>{dayLabel}</span>
              ))}
            </div>

            <div className="profile-calendar-grid">
              {calendarDays.map((day) => (
                <button
                  key={day.dateKey}
                  type="button"
                  className={[
                    'calendar-day-btn',
                    day.isCurrentMonth ? '' : 'is-muted',
                    day.isToday ? 'is-today' : '',
                    day.isSelected ? 'is-selected' : '',
                    day.itemCount > 0 ? 'has-availability' : '',
                    addedFreeTimeDateSet.has(day.dateKey) ? 'has-workspace-availability' : '',
                    selectedFreeTimeDateSet.has(day.dateKey) ? 'is-pending-availability' : '',
                  ].filter(Boolean).join(' ')}
                  onClick={() => handleCalendarDayClick(day.dateKey, day.date)}
                >
                  <span>{day.label}</span>
                  {day.itemCount > 0 ? <small>{day.itemCount}</small> : null}
                </button>
              ))}
            </div>

            <div className="projects-calendar-summary">
              <p>
                {selectedItem
                  ? 'Нажмите на день, чтобы отметить его для нового окна доступности.'
                  : activeDateFilterKey
                    ? `Записи за день: ${activeDayLabel}. Найдено: ${selectedDayItems.length}.`
                    : 'Нажмите на день, чтобы открыть таблицу по дате создания.'}
              </p>
              {selectedItem && selectedFreeTimeDateKeys.length > 0 ? (
                <button type="button" className="ghost-action-btn" onClick={() => setSelectedFreeTimeDateKeys([])}>
                  Сбросить выбор
                </button>
              ) : activeDateFilterKey ? (
                <button type="button" className="ghost-action-btn" onClick={() => setActiveDateFilterKey(null)}>
                  Очистить день
                </button>
              ) : null}
            </div>
          </section>

          <section className="dashboard-panel projects-side-info-card">
            <div className="section-heading compact-heading">
              <div>
                <span className="projects-panel-eyebrow">Доступность на выбранный день</span>
                <h2>{selectedDayStatLabel}</h2>
              </div>
            </div>
            <div className="projects-mini-stats-grid">
              <article className="projects-mini-stat is-green">
                <span>Доступно</span>
                <strong>{selectedItem ? selectedFreeTimeDateKeys.length : selectedDayItems.length}</strong>
              </article>
              <article className="projects-mini-stat">
                <span>Занято</span>
                <strong>{selectedItem ? selectedItemFreeTimes.length : totalReservedWindows}</strong>
              </article>
              <article className="projects-mini-stat is-blue">
                <span>Всего</span>
                <strong>{selectedItem ? selectedItemFreeTimes.length + selectedFreeTimeDateKeys.length : projectResources.length}</strong>
              </article>
            </div>
          </section>

          <section className="dashboard-panel projects-side-info-card">
            <div className="section-heading compact-heading">
              <div>
                <span className="projects-panel-eyebrow">Последняя активность</span>
                <h2>Журнал рабочей зоны</h2>
              </div>
            </div>
            <div className="projects-activity-card">
              <p>
                {selectedItem
                  ? `Сейчас в фокусе: ${selectedItem.title}. Вы можете редактировать доступность, бронирование и медиа.`
                  : 'Нет данных о действиях. Выберите объект в таблице или день в календаре.'}
              </p>
              <button type="button" className="ghost-action-btn">
                <ListIcon />
                <span>Журнал активности</span>
              </button>
            </div>
          </section>
        </aside>

        <section className="dashboard-panel projects-table-panel projects-table-full">
          <div className="section-heading projects-table-heading">
            <div>
              <span className="projects-panel-eyebrow">Таблица</span>
              <h2>{currentResource.label}</h2>
            </div>
            <p>
              {isWorkspaceLoading
                ? 'Загружаем список...'
                : activeDateFilterKey
                  ? `Показаны записи за ${activeDayLabel}`
                  : `Показана страница ${pagination.page} из ${pagination.totalPages}`}
            </p>
          </div>

          <div className="table-shell">
            <table className="user-table">
              <thead>
                <tr>
                  {activeResource === 'requisites' ? <th>Фото</th> : null}
                  {currentResource.columns.map((column) => (
                    <th key={column.key}>{column.label}</th>
                  ))}
                  <th>Действия</th>
                </tr>
              </thead>
              <tbody>
                {filteredItems.map((item) => {
                  const isSelected = selectedItemId === item.oid;

                  return (
                    <tr key={item.oid} className={isSelected ? 'table-row-selected' : ''}>
                      {activeResource === 'requisites' ? (
                        <td data-label="Фото">
                          <span
                            className={[
                              'requisite-photo-status',
                              (requisiteTableImagesById[item.oid] || []).length > 0 ? 'has-photo' : '',
                            ].filter(Boolean).join(' ')}
                          >
                            {(requisiteTableImagesById[item.oid] || []).length > 0 ? 'Фото есть' : 'Нет фото'}
                          </span>
                        </td>
                      ) : null}
                      {currentResource.columns.map((column) => (
                        <td key={column.key} data-label={column.label}>{getColumnValue(item, column)}</td>
                      ))}
                      <td data-label="Действия">
                        <div className="table-actions">
                          <button type="button" className="ghost-action-btn" onClick={() => handleEdit(item)}>
                            Изменить
                          </button>
                          <button type="button" className="ghost-action-btn" onClick={() => handleSelectItem(item)}>
                            {isSelected ? 'Выбрано' : 'Выбрать'}
                          </button>
                          <button
                            type="button"
                            className="ghost-action-btn danger"
                            onClick={() => handleDelete(item.oid)}
                            disabled={deletingId === item.oid}
                          >
                            {deletingId === item.oid ? 'Удаляем...' : 'Удалить'}
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>

            {!isWorkspaceLoading && filteredItems.length === 0 ? (
              <p className="helper-note projects-empty-state">
                {activeDateFilterKey
                  ? 'На выбранную дату записей нет. Снимите фильтр или выберите другой день.'
                  : activeProjectId
                    ? 'В этом проекте пока нет элементов этой категории.'
                    : 'Сначала выберите проект, чтобы увидеть его таблицу.'}
              </p>
            ) : null}
          </div>

          {!activeDateFilterKey ? (
            <div className="pagination">
              <button
                type="button"
                onClick={() => handlePageChange(pagination.page - 1)}
                disabled={pagination.page <= 1 || isWorkspaceLoading}
              >
                Назад
              </button>
              <span>Страница {pagination.page} из {pagination.totalPages}</span>
              <button
                type="button"
                onClick={() => handlePageChange(pagination.page + 1)}
                disabled={pagination.page >= pagination.totalPages || isWorkspaceLoading}
              >
                Вперед
              </button>
            </div>
          ) : null}
        </section>
      </div>
    </section>
  );
};

export default Projects;
