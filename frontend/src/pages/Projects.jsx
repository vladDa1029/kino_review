import { NavLink } from 'react-router-dom';

const Projects = () => {
  return (
    <section className="projects-wrapper">
      <div className="projects-page">
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

        <h1>Рабочая зона</h1>
        <p>Здесь будет ваш дашборд проектов и задач.</p>
      </div>
    </section>
  );
};

export default Projects;
