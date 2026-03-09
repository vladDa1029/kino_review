import { useState } from 'react';

const ProfilePage = () => {
  const [profile, setProfile] = useState({
    name: '',
    bio: '',
    location: '',
    website: '',
  });
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

  const handleSubmit = (event) => {
    event.preventDefault();
  };

  return (
    <section className="profile-page">
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
          <label htmlFor="profile-name">Имя</label>
          <input
            id="profile-name"
            name="name"
            type="text"
            value={profile.name}
            onChange={handleChange}
            placeholder="Введите имя"
            className="profile-input"
          />

          <label htmlFor="profile-bio">Описание</label>
          <textarea
            id="profile-bio"
            name="bio"
            value={profile.bio}
            onChange={handleChange}
            placeholder="Расскажите о себе"
            className="profile-textarea"
            rows={4}
          />

          <label htmlFor="profile-location">Город</label>
          <input
            id="profile-location"
            name="location"
            type="text"
            value={profile.location}
            onChange={handleChange}
            placeholder="Например: Москва"
            className="profile-input"
          />

          <label htmlFor="profile-website">Сайт</label>
          <input
            id="profile-website"
            name="website"
            type="url"
            value={profile.website}
            onChange={handleChange}
            placeholder="https://example.com"
            className="profile-input"
          />
        </div>

        <button type="submit" className="profile-save-btn">
          Сохранить
        </button>
      </form>
    </section>
  );
};

export default ProfilePage;
