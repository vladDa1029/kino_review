import { useState, useEffect } from 'react';

const ThemeToggle = ({ darkMode, onToggle }) => {
  const [isDark, setIsDark] = useState(darkMode);

  useEffect(() => {
    setIsDark(darkMode);
  }, [darkMode]);

  const toggle = () => {
    onToggle();
  };

  return (
    <button
      className="theme-toggle"
      onClick={toggle}
      aria-label={isDark ? 'Переключить на светлую тему' : 'Переключить на темную тему'}
    >
      {isDark ? (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
          <path d="M12 3c.132 0 .263 0 .393 0a7.5 7.5 0 0 0 7.92 12.446a9 9 0 1 1-8.313-12.454z" />
        </svg>
      ) : (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
          <circle cx="12" cy="12" r="5" />
          <path d="M12 1v2" />
          <path d="M12 21v2" />
          <path d="M4.22 4.22l1.42 1.42" />
          <path d="M18.36 18.36l1.42 1.42" />
          <path d="M1 12h2" />
          <path d="M21 12h2" />
          <path d="M4.22 19.78l1.42-1.42" />
          <path d="M18.36 5.64l1.42-1.42" />
        </svg>
      )}
    </button>
  );
};

export default ThemeToggle;
