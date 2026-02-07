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
        <h1>Smart Video Project Management</h1>
        <p className="subtitle">
          Organize, track and collaborate on your video projects with ease
        </p>
        <div className="cta-buttons">
          <button className="primary-btn" onClick={onOpenAuth}>Get Started</button>
          <button className="secondary-btn">Watch Demo</button>
        </div>
      </div>
      <div className="hero-image">
        <div className="network-animation">
          <svg width="100%" height="100%" viewBox="0 0 400 400" className="connections">
            <defs>
              <linearGradient id="gradientLine" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" style={{stopColor:'#3498db', stopOpacity:0.3}} />
                <stop offset="100%" style={{stopColor:'#8e44ad', stopOpacity:0.8}} />
              </linearGradient>
            </defs>
            <line x1="200" y1="120" x2="120" y2="200" className="line" />
            <line x1="200" y1="120" x2="280" y2="200" className="line" />
            <line x1="120" y1="200" x2="200" y2="280" className="line" />
            <line x1="280" y1="200" x2="200" y2="280" className="line" />
            <line x1="200" y1="280" x2="200" y2="360" className="line" />
          </svg>
          <div className="node node1"></div>
          <div className="node node2"></div>
          <div className="node node3"></div>
          <div className="node node4"></div>
          <div className="node node5"></div>
        </div>
      </div>
    </main>

    <section id="features" className="features-section">
      <div className="features-container">
        <h2>Powerful Features for Video Creators</h2>
        <div className="features-grid">
          <div className="feature-card">
            <div className="feature-icon">📁</div>
            <h3>Project Organization</h3>
            <p>Keep all your video projects neatly organized with intuitive folder structures and tagging systems.</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">👥</div>
            <h3>Team Collaboration</h3>
            <p>Work seamlessly with your team members, assign tasks, and track progress in real-time.</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">📊</div>
            <h3>Progress Tracking</h3>
            <p>Monitor project milestones, deadlines, and completion status with detailed analytics.</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">🎬</div>
            <h3>Video Asset Management</h3>
            <p>Centralize all your video files, scripts, and related assets in one secure location.</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">💬</div>
            <h3>Communication Tools</h3>
            <p>Built-in messaging and feedback systems to streamline client and team communications.</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">🔒</div>
            <h3>Secure & Private</h3>
            <p>Enterprise-grade security ensures your projects and data remain safe and confidential.</p>
          </div>
        </div>
      </div>
    </section>

    <section id="pricing" className="pricing-section">
      <div className="pricing-container">
        <h2>Choose Your Plan</h2>
        <div className="pricing-grid">
          <div className="pricing-card">
            <div className="pricing-header">
              <h3>Starter</h3>
              <div className="price">
                <span className="currency">$</span>
                <span className="amount">9</span>
                <span className="period">/month</span>
              </div>
            </div>
            <ul className="pricing-features">
              <li>Up to 5 projects</li>
              <li>Basic collaboration tools</li>
              <li>5GB storage</li>
              <li>Email support</li>
            </ul>
            <button className="pricing-btn">Get Started</button>
          </div>
          <div className="pricing-card popular">
            <div className="popular-badge">Most Popular</div>
            <div className="pricing-header">
              <h3>Professional</h3>
              <div className="price">
                <span className="currency">$</span>
                <span className="amount">29</span>
                <span className="period">/month</span>
              </div>
            </div>
            <ul className="pricing-features">
              <li>Unlimited projects</li>
              <li>Advanced collaboration</li>
              <li>50GB storage</li>
              <li>Priority support</li>
              <li>Analytics dashboard</li>
            </ul>
            <button className="pricing-btn primary">Get Started</button>
          </div>
          <div className="pricing-card">
            <div className="pricing-header">
              <h3>Enterprise</h3>
              <div className="price">
                <span className="currency">$</span>
                <span className="amount">99</span>
                <span className="period">/month</span>
              </div>
            </div>
            <ul className="pricing-features">
              <li>Everything in Professional</li>
              <li>Unlimited storage</li>
              <li>Custom integrations</li>
              <li>Dedicated account manager</li>
              <li>24/7 phone support</li>
            </ul>
            <button className="pricing-btn">Contact Sales</button>
          </div>
        </div>
      </div>
    </section>

    <section id="about" className="about-section">
      <div className="about-container">
        <div className="about-content">
          <h2>Why Choose Our Platform?</h2>
          <p>
            We've built the ultimate video project management solution for creators, agencies, and production teams.
            Our platform combines powerful organization tools with seamless collaboration features to help you
            deliver projects on time and exceed expectations.
          </p>
          <div className="stats">
            <div className="stat">
              <div className="stat-number">10K+</div>
              <div className="stat-label">Projects Managed</div>
            </div>
            <div className="stat">
              <div className="stat-number">500+</div>
              <div className="stat-label">Happy Creators</div>
            </div>
            <div className="stat">
              <div className="stat-number">99.9%</div>
              <div className="stat-label">Uptime</div>
            </div>
          </div>
        </div>
        <div className="about-image">
          <div className="placeholder-image">
            <span>🎯</span>
          </div>
        </div>
      </div>
    </section>

    <footer className="footer">
      <div className="footer-container">
        <div className="footer-content">
          <div className="footer-logo">
            <h3>VideoProject Manager</h3>
          </div>
          <div className="footer-links">
            <div className="footer-column">
              <h4>Product</h4>
              <button onClick={() => handleScroll('features')} className="nav-link">Features</button>
              <button onClick={() => handleScroll('pricing')} className="nav-link">Pricing</button>
              <a href="#integrations">Integrations</a>
            </div>
            <div className="footer-column">
              <h4>Company</h4>
              <button onClick={() => handleScroll('about')} className="nav-link">About</button>
              <a href="#blog">Blog</a>
              <a href="#careers">Careers</a>
            </div>
            <div className="footer-column">
              <h4>Support</h4>
              <a href="#help">Help Center</a>
              <a href="#contact">Contact Us</a>
              <a href="#status">System Status</a>
            </div>
          </div>
        </div>
        <div className="footer-bottom">
          <p>&copy; 2024 VideoProject Manager. All rights reserved.</p>
        </div>
      </div>
    </footer>
    </>
  );
};

export default HomePage;
