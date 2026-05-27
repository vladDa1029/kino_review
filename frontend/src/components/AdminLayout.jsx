import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/useAuth';
import ThemeToggle from './ThemeToggle';

const UsersIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
    <path d="M16.5 20C16.5 17.7909 14.4853 16 12 16C9.51472 16 7.5 17.7909 7.5 20" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    <path d="M12 12C13.933 12 15.5 10.433 15.5 8.5C15.5 6.567 13.933 5 12 5C10.067 5 8.5 6.567 8.5 8.5C8.5 10.433 10.067 12 12 12Z" stroke="currentColor" strokeWidth="1.8" />
    <path d="M19 19.5C19 17.9772 18.1203 16.66 16.8428 16" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    <path d="M16.5 5.5C17.8261 5.7423 18.8338 6.90281 18.8338 8.29885C18.8338 9.6949 17.8261 10.8554 16.5 11.0977" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
  </svg>
);

const FolderIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
    <path d="M4 7.5C4 6.67157 4.67157 6 5.5 6H10L12 8H18.5C19.3284 8 20 8.67157 20 9.5V16.5C20 17.3284 19.3284 18 18.5 18H5.5C4.67157 18 4 17.3284 4 16.5V7.5Z" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
  </svg>
);

const ReportIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
    <path d="M7 4.5H13L17 8.5V19.5H7C6.44772 19.5 6 19.0523 6 18.5V5.5C6 4.94772 6.44772 4.5 7 4.5Z" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
    <path d="M13 4.5V8.5H17" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
    <path d="M9 12H14" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    <path d="M9 15H14" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
  </svg>
);

const ExitIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
    <path
      d="M10 7V5.75C10 5.05964 10.5596 4.5 11.25 4.5H17.25C17.9404 4.5 18.5 5.05964 18.5 5.75V18.25C18.5 18.9404 17.9404 19.5 17.25 19.5H11.25C10.5596 19.5 10 18.9404 10 18.25V17"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
    />
    <path d="M14 12H5.5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    <path d="M8.5 9L5.5 12L8.5 15" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

const navItems = [
  { to: '/admin/users', label: 'Пользователи', icon: UsersIcon },
  { to: '/admin/projects', label: 'Проекты', icon: FolderIcon },
  { to: '/admin/reports', label: 'Отчёты', icon: ReportIcon },
];

const AdminLayout = ({ darkMode, onToggleTheme }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const { token, handleLogout } = useAuth();

  return (
    <div className="admin-shell">
      <div className="admin-main">
        <header className="admin-topbar">
          <div className="admin-topbar-breadcrumb">
            <strong>KINOFLOW</strong>
            <span>Админ-панель</span>
          </div>

          <div className="admin-topbar-tools">
            <ThemeToggle darkMode={darkMode} onToggle={onToggleTheme} />
            <button
              type="button"
              className="admin-icon-btn admin-exit-btn"
              onClick={() => {
                if (token) {
                  handleLogout();
                  return;
                }
                navigate('/');
              }}
              aria-label={token ? 'Выйти из админки' : 'Вернуться на главную'}
              title={token ? 'Выйти' : 'Домой'}
            >
              <ExitIcon />
            </button>
          </div>
        </header>

        <div className="admin-tabbar" role="tablist" aria-label="Admin sections">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname.startsWith(item.to);
            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={`admin-tab ${isActive ? 'is-active' : ''}`}
              >
                <Icon />
                <span>{item.label}</span>
              </NavLink>
            );
          })}
        </div>

        <main className="admin-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
};

export default AdminLayout;
