const HomePage = ({ onOpenAuth }) => {
  const handleScroll = (sectionId) => {
    const element = document.getElementById(sectionId);
    if (element) {
      const offsetTop = element.offsetTop - 80; // Account for header height
      window.scrollTo({
        top: offsetTop,
        behavior: 'smooth'
      });
    }
  };

  return (
    <>
    <main className="hero-section">
      <div className="hero-content">
        <h1>Продакшн-панель для режиссёров и команд</h1>
        <p className="subtitle">
          Планируйте смены, контролируйте этапы и держите всю команду в одном рабочем пространстве.
        </p>
        <div className="cta-buttons">
          <button className="primary-btn" onClick={onOpenAuth}>Начать работу</button>
          <button className="secondary-btn">Посмотреть демо</button>
        </div>
      </div>
    </main>

    <section id="features" className="features-section">
      <div className="features-container">
        <h2>Ключевые инструменты площадки</h2>
        <div className="features-grid">
          <div className="feature-card">
            <div className="feature-icon">📁</div>
            <h3>Структура проекта</h3>
            <p>Сцены, документы и медиафайлы в едином пространстве с быстрым доступом по ролям.</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">👥</div>
            <h3>Командная работа</h3>
            <p>Постановка задач, статусы и комментарии по каждому этапу без лишних чатов.</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">📊</div>
            <h3>Контроль дедлайнов</h3>
            <p>Видно, где проект в риске: от препродакшна до финального монтажа.</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">🎬</div>
            <h3>Управление шотами</h3>
            <p>Shot-list, референсы, таймлайн и версия материалов под рукой у всей команды.</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">💬</div>
            <h3>Согласование правок</h3>
            <p>Комментарии и решения фиксируются в контексте сцены, а не теряются в переписке.</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">🔒</div>
            <h3>Безопасный доступ</h3>
            <p>Роли, приватные проекты и защищённое хранение производственных данных.</p>
          </div>
        </div>
      </div>
    </section>

    <section id="pricing" className="pricing-section">
      <div className="pricing-container">
        <h2>Тарифы для команд любого масштаба</h2>
        <div className="pricing-grid">
          <div className="pricing-card">
            <div className="pricing-header">
              <h3>Start</h3>
              <div className="price">
                <span className="currency">$</span>
                <span className="amount">9</span>
                <span className="period">/мес</span>
              </div>
            </div>
            <ul className="pricing-features">
              <li>До 5 активных проектов</li>
              <li>Базовые инструменты команды</li>
              <li>5 GB медиа-хранилища</li>
              <li>Поддержка по почте</li>
            </ul>
            <button className="pricing-btn">Подключить</button>
          </div>
          <div className="pricing-card">
            <div className="pricing-header">
              <h3>Studio</h3>
              <div className="price">
                <span className="currency">$</span>
                <span className="amount">29</span>
                <span className="period">/мес</span>
              </div>
            </div>
            <ul className="pricing-features">
              <li>Неограниченные проекты</li>
              <li>Расширенная совместная работа</li>
              <li>50 GB хранилища</li>
              <li>Приоритетная поддержка</li>
              <li>Аналитика по этапам</li>
            </ul>
            <button className="pricing-btn">Подключить</button>
          </div>
          <div className="pricing-card">
            <div className="pricing-header">
              <h3>Enterprise</h3>
              <div className="price">
                <span className="currency">$</span>
                <span className="amount">99</span>
                <span className="period">/мес</span>
              </div>
            </div>
            <ul className="pricing-features">
              <li>Всё из Studio +</li>
              <li>Безлимитное хранилище</li>
              <li>Кастомные интеграции</li>
              <li>Персональный менеджер</li>
              <li>Поддержка 24/7</li>
            </ul>
            <button className="pricing-btn">Связаться с нами</button>
          </div>
        </div>
      </div>
    </section>

    <section id="about" className="about-section">
      <div className="about-container">
        <div className="about-content">
          <h2>Почему команды выбирают KinoFlow</h2>
          <p>
            Платформа создана для реального продакшна: от таблиц смен и call sheet
            до контроля правок в посте. Меньше хаоса в коммуникации, больше фокуса на результате.
          </p>
          <div className="stats">
            <div className="stat">
              <div className="stat-number">10K+</div>
              <div className="stat-label">Сцен и задач в работе</div>
            </div>
            <div className="stat">
              <div className="stat-number">500+</div>
              <div className="stat-label">Команд и агентств</div>
            </div>
            <div className="stat">
              <div className="stat-number">99.9%</div>
              <div className="stat-label">Стабильность сервиса</div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <footer className="footer">
      <div className="footer-container">
        <div className="footer-content">
          <div className="footer-logo">
            <h3>KinoFlow</h3>
          </div>
          <div className="footer-links">
            <div className="footer-column">
              <h4>Продукт</h4>
              <button onClick={() => handleScroll('features')} className="nav-link">Возможности</button>
              <button onClick={() => handleScroll('pricing')} className="nav-link">Тарифы</button>
              <a href="#integrations">Интеграции</a>
            </div>
            <div className="footer-column">
              <h4>Компания</h4>
              <button onClick={() => handleScroll('about')} className="nav-link">О платформе</button>
              <a href="#blog">Блог</a>
              <a href="#careers">Карьера</a>
            </div>
            <div className="footer-column">
              <h4>Поддержка</h4>
              <a href="#help">Центр помощи</a>
              <a href="#contact">Контакты</a>
              <a href="#status">Статус системы</a>
            </div>
          </div>
        </div>
        <div className="footer-bottom">
          <p>&copy; 2026 KinoFlow. Все права защищены.</p>
        </div>
      </div>
    </footer>
    </>
  );
};

export default HomePage;
