import { useEffect, useState } from 'react';
import { NavLink } from 'react-router-dom';
import { toast } from 'react-toastify';
import { ApiError } from '../services/httpClient';
import {
  createUserDescription,
  getUserDescription,
  updateUserDescription,
} from '../services/api';

const ProfilePage = () => {
  const [profile, setProfile] = useState({
    username: '',
    phone: '',
  });
  const [descriptionId, setDescriptionId] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [avatarPreview, setAvatarPreview] = useState('');

  const handleChange = (event) => {
    const { name, value } = event.target;
    setProfile((prev) => ({ ...prev, [name]: value }));
  };

  const handleAvatarChange = (event) => {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }

    const reader = new FileReader();
    reader.onload = () => {
      if (typeof reader.result === 'string') {
        setAvatarPreview(reader.result);
      }
    };
    reader.readAsDataURL(file);
  };

  useEffect(() => {
    const loadDescription = async () => {
      try {
        const data = await getUserDescription();
        setDescriptionId(data.oid);
        setProfile({
          username: data.username || '',
          phone: data.phone || '',
        });
      } catch (error) {
        if (!(error instanceof ApiError) || error.status !== 404) {
          toast.error(error.message || 'Не удалось загрузить описание профиля');
        }
      } finally {
        setIsLoading(false);
      }
    };

    loadDescription();
  }, []);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setIsSubmitting(true);

    try {
      const payload = {
        username: profile.username.trim(),
        phone: profile.phone.trim(),
      };

      if (descriptionId) {
        await updateUserDescription(descriptionId, payload);
      } else {
        await createUserDescription(payload);
        const data = await getUserDescription();
        setDescriptionId(data.oid);
      }

      toast.success('Описание профиля сохранено');
    } catch (error) {
      toast.error(error.message || 'Не удалось сохранить описание профиля');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <section className="profile-page">
      <div className="profile-page-inner">
        <div className="page-switcher">
          <NavLink
            to="/profile"
            className={({ isActive }) => `switcher-btn ${isActive ? 'active' : ''}`}
          >
            Профиль
          </NavLink>
          <NavLink
            to="/projects"
            className={({ isActive }) => `switcher-btn ${isActive ? 'active' : ''}`}
          >
            Рабочая зона
          </NavLink>
        </div>

        {isLoading ? (
          <div className="profile-card">Загрузка профиля...</div>
        ) : (
          <form className="profile-card" onSubmit={handleSubmit}>
            <h2>Профиль</h2>

            <div className="profile-avatar-block">
              <label
                className={`profile-avatar-preview ${avatarPreview ? '' : 'is-empty'}`}
                htmlFor="avatar-upload"
              >
                {avatarPreview ? <img src={avatarPreview} alt="Avatar preview" /> : null}
              </label>
              <input
                id="avatar-upload"
                className="profile-avatar-input"
                type="file"
                accept="image/*"
                onChange={handleAvatarChange}
              />
            </div>

            <div className="profile-fields">
              <label htmlFor="profile-username">Имя пользователя</label>
              <input
                id="profile-username"
                name="username"
                type="text"
                value={profile.username}
                onChange={handleChange}
                placeholder="Например: Ivan Petrov"
                className="profile-input"
                required
              />

              <label htmlFor="profile-phone">Телефон</label>
              <input
                id="profile-phone"
                name="phone"
                type="tel"
                value={profile.phone}
                onChange={handleChange}
                placeholder="+79991234567"
                className="profile-input"
                required
              />
            </div>

            <button type="submit" className="profile-save-btn" disabled={isSubmitting}>
              {isSubmitting ? 'Сохранение...' : 'Сохранить'}
            </button>
          </form>
        )}
      </div>
    </section>
  );
};

export default ProfilePage;
