import apiClient from './httpClient';

const buildQueryString = (params = {}) => {
  const searchParams = new URLSearchParams();

  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') {
      return;
    }

    searchParams.set(key, String(value));
  });

  return searchParams.toString();
};

const withQuery = (path, params) => {
  const queryString = buildQueryString(params);
  return queryString ? `${path}?${queryString}` : path;
};

const createJsonRequest = (path, method, payload) =>
  apiClient(path, {
    method,
    body: JSON.stringify(payload),
  });

const createCollectionHelpers = (collectionPath, buildListParams) => ({
  create: async (payload) => createJsonRequest(collectionPath, 'POST', payload),
  list: async (params = {}) =>
    apiClient(withQuery(collectionPath, buildListParams(params)), {
      method: 'GET',
    }),
  update: async (itemId, payload) => createJsonRequest(`${collectionPath}/${itemId}`, 'PUT', payload),
  remove: async (itemId) =>
    apiClient(`${collectionPath}/${itemId}`, {
      method: 'DELETE',
    }),
});

const buildEquipmentListParams = ({
  page = 1,
  pageSize = 20,
  sortBy,
  sortDir = 'asc',
  type,
  search,
  createdFrom,
  createdTo,
} = {}) => ({
  page,
  page_size: pageSize,
  sort_by: sortBy,
  sort_dir: sortDir,
  type,
  search,
  created_from: createdFrom,
  created_to: createdTo,
});

const buildRequisiteListParams = ({
  page = 1,
  pageSize = 20,
  sortBy,
  sortDir = 'asc',
  type,
  size,
  search,
  createdFrom,
  createdTo,
} = {}) => ({
  page,
  page_size: pageSize,
  sort_by: sortBy,
  sort_dir: sortDir,
  type,
  size,
  search,
  created_from: createdFrom,
  created_to: createdTo,
});

const createEquipmentFreeTimeHelper = (resourcePath) => async (itemId, payload) =>
  createJsonRequest(`/user/users/me/${resourcePath}/${itemId}/free-times`, 'POST', payload);

const createEquipmentFreeTimeListHelper = (resourcePath) => async (itemId) =>
  apiClient(`/user/users/me/${resourcePath}/${itemId}/free-times`, {
    method: 'GET',
  });

const createImageUploadFormData = (payload) => {
  if (payload instanceof FormData) {
    return payload;
  }

  const formData = new FormData();
  formData.append('file', payload.file);
  formData.append('title', payload.title);
  formData.append('description', payload.description);
  return formData;
};

const microfonsApi = createCollectionHelpers('/user/users/me/microfons', buildEquipmentListParams);
const camerasApi = createCollectionHelpers('/user/users/me/cameras', buildEquipmentListParams);
const cameraTripodsApi = createCollectionHelpers('/user/users/me/camera-tripods', buildEquipmentListParams);
const lightsApi = createCollectionHelpers('/user/users/me/lights', buildEquipmentListParams);
const lightTripodsApi = createCollectionHelpers('/user/users/me/light-tripods', buildEquipmentListParams);
const soundsApi = createCollectionHelpers('/user/users/me/sounds', buildEquipmentListParams);
const requisitesApi = createCollectionHelpers('/user/users/me/requisites', buildRequisiteListParams);

export const register = async (email, password) =>
  createJsonRequest('/auth/register', 'POST', { email, password });

export const login = async (username, password) => {
  const formData = new URLSearchParams();
  formData.append('username', username);
  formData.append('password', password);
  formData.append('grant_type', 'password');

  return apiClient('/auth/login', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: formData,
  });
};

export const refreshToken = async () =>
  apiClient('/auth/refresh', {
    method: 'POST',
    withCredentials: true,
    skipAuth: true,
    skipJsonContentType: true,
  });

export const logout = async () =>
  apiClient('/auth/logout', {
    method: 'GET',
    withCredentials: true,
  });

export const getUsers = async (page = 1, pageSize = 5) =>
  apiClient(
    withQuery('/auth/users', {
      page,
      page_size: pageSize,
    }),
    {
      method: 'GET',
    },
  );

export const checkCurrentUserExists = async () =>
  apiClient('/user/users/me', {
    method: 'GET',
  });

export const createUserDescription = async (payload) =>
  createJsonRequest('/user/users/me/description', 'POST', payload);

export const getUserDescription = async () =>
  apiClient('/user/users/me/description', {
    method: 'GET',
  });

export const updateUserDescription = async (descriptionId, payload) =>
  createJsonRequest(`/user/users/me/description/${descriptionId}`, 'PUT', payload);

export const createSpareTime = async (payload) =>
  createJsonRequest('/user/users/me/spare-times', 'POST', payload);

export const listSpareTimes = async () =>
  apiClient('/user/users/me/spare-times', {
    method: 'GET',
  });

export const getSpareTime = async (spareTimeId) =>
  apiClient(`/user/users/me/spare-times/${spareTimeId}`, {
    method: 'GET',
  });

export const updateSpareTime = async (spareTimeId, payload) =>
  createJsonRequest(`/user/users/me/spare-times/${spareTimeId}`, 'PUT', payload);

export const deleteSpareTime = async (spareTimeId) =>
  apiClient(`/user/users/me/spare-times/${spareTimeId}`, {
    method: 'DELETE',
  });

export const reserveAvailability = async (payload) =>
  createJsonRequest('/user/users/me/availability/reserve', 'POST', payload);

export const createMicrofon = microfonsApi.create;
export const listMicrofons = microfonsApi.list;
export const updateMicrofon = microfonsApi.update;
export const deleteMicrofon = microfonsApi.remove;
export const addMicrofonFreeTime = createEquipmentFreeTimeHelper('microfons');
export const listMicrofonFreeTimes = createEquipmentFreeTimeListHelper('microfons');

export const createCamera = camerasApi.create;
export const listCameras = camerasApi.list;
export const updateCamera = camerasApi.update;
export const deleteCamera = camerasApi.remove;
export const addCameraFreeTime = createEquipmentFreeTimeHelper('cameras');
export const listCameraFreeTimes = createEquipmentFreeTimeListHelper('cameras');

export const createCameraTripod = cameraTripodsApi.create;
export const listCameraTripods = cameraTripodsApi.list;
export const updateCameraTripod = cameraTripodsApi.update;
export const deleteCameraTripod = cameraTripodsApi.remove;
export const addCameraTripodFreeTime = createEquipmentFreeTimeHelper('camera-tripods');
export const listCameraTripodFreeTimes = createEquipmentFreeTimeListHelper('camera-tripods');

export const createLight = lightsApi.create;
export const listLights = lightsApi.list;
export const updateLight = lightsApi.update;
export const deleteLight = lightsApi.remove;
export const addLightFreeTime = createEquipmentFreeTimeHelper('lights');
export const listLightFreeTimes = createEquipmentFreeTimeListHelper('lights');

export const createLightTripod = lightTripodsApi.create;
export const listLightTripods = lightTripodsApi.list;
export const updateLightTripod = lightTripodsApi.update;
export const deleteLightTripod = lightTripodsApi.remove;
export const addLightTripodFreeTime = createEquipmentFreeTimeHelper('light-tripods');
export const listLightTripodFreeTimes = createEquipmentFreeTimeListHelper('light-tripods');

export const createSound = soundsApi.create;
export const listSounds = soundsApi.list;
export const updateSound = soundsApi.update;
export const deleteSound = soundsApi.remove;
export const addSoundFreeTime = createEquipmentFreeTimeHelper('sounds');
export const listSoundFreeTimes = createEquipmentFreeTimeListHelper('sounds');

export const createRequisite = requisitesApi.create;
export const listRequisites = requisitesApi.list;
export const updateRequisite = requisitesApi.update;
export const deleteRequisite = requisitesApi.remove;
export const addRequisiteFreeTime = createEquipmentFreeTimeHelper('requisites');
export const listRequisiteFreeTimes = createEquipmentFreeTimeListHelper('requisites');

export const addRequisiteImage = async (requisiteId, payload) =>
  apiClient(`/user/users/me/requisites/${requisiteId}/images`, {
    method: 'POST',
    body: createImageUploadFormData(payload),
  });

export const listRequisiteImages = async (requisiteId) =>
  apiClient(`/user/users/me/requisites/${requisiteId}/images`, {
    method: 'GET',
  });

export const getRequisiteImage = async (requisiteId, imageId) =>
  apiClient(`/user/users/me/requisites/${requisiteId}/images/${imageId}`, {
    method: 'GET',
  });

export const removeRequisiteImage = async (requisiteId, imageId) =>
  apiClient(`/user/users/me/requisites/${requisiteId}/images/${imageId}`, {
    method: 'DELETE',
  });
