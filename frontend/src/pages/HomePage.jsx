const HomePage = ({ onOpenAuth }) => {
  return (
    <>
      <main id="home" className="hero-section">
        <div className="hero-content">
          <h1>Продакшн-панель для режиссеров и команд</h1>
          <p className="subtitle">
            Планируйте смены, контролируйте этапы и держите всю команду в одном рабочем пространстве.
          </p>
          <div className="cta-buttons">
            <button className="primary-btn" onClick={onOpenAuth}>Начать работу</button>
            <button className="secondary-btn">Посмотреть демо</button>
          </div>
        </div>
      </main>
    </>
  );
};

export default HomePage;
