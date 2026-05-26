const getProfileUsername = (profile) =>
  profile?.username ??
  profile?.description?.username ??
  '';

const getProfilePhone = (profile) =>
  profile?.phone ??
  profile?.description?.phone ??
  '';

export const PROFILE_COMPLETION_STORAGE_KEY = 'kinoflow.profileComplete';
export const PROFILE_COMPLETION_EVENT = 'kinoflow:profile-complete-change';

export const isProfileComplete = (profile) =>
  Boolean(getProfileUsername(profile)?.trim() && getProfilePhone(profile)?.trim());

export const setStoredProfileCompletion = (value) => {
  localStorage.setItem(PROFILE_COMPLETION_STORAGE_KEY, value ? 'true' : 'false');
  window.dispatchEvent(
    new CustomEvent(PROFILE_COMPLETION_EVENT, {
      detail: { isComplete: value },
    }),
  );
};

export const getStoredProfileCompletion = () =>
  localStorage.getItem(PROFILE_COMPLETION_STORAGE_KEY) === 'true';
