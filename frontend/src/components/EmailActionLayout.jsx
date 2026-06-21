const TONE_COLORS = {
  success: '#22c55e',
  error: '#ef4444',
  info: 'var(--accent)',
  loading: 'var(--accent)',
};

const Spinner = () => (
  <svg width="26" height="26" viewBox="0 0 24 24" fill="none" aria-hidden="true">
    <circle cx="12" cy="12" r="9" stroke="currentColor" strokeOpacity="0.25" strokeWidth="3" />
    <path d="M21 12a9 9 0 0 0-9-9" stroke="currentColor" strokeWidth="3" strokeLinecap="round">
      <animateTransform
        attributeName="transform"
        type="rotate"
        from="0 12 12"
        to="360 12 12"
        dur="0.8s"
        repeatCount="indefinite"
      />
    </path>
  </svg>
);

const StatusGlyph = ({ tone }) => {
  if (tone === 'success') {
    return (
      <svg width="26" height="26" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path
          d="M5 12.5l4 4 10-10"
          stroke="currentColor"
          strokeWidth="2.4"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    );
  }
  if (tone === 'error') {
    return (
      <svg width="26" height="26" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path d="M7 7l10 10M17 7L7 17" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" />
      </svg>
    );
  }
  return (
    <svg width="26" height="26" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M4 7l8 6 8-6M4 7v10h16V7M4 7h16"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinejoin="round"
      />
    </svg>
  );
};

const EmailActionLayout = ({ eyebrow, title, message, tone = 'info', children }) => (
  <main
    style={{
      minHeight: 'calc(100vh - 90px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '32px 16px',
    }}
  >
    <div
      style={{
        width: '100%',
        maxWidth: 460,
        background: 'var(--surface)',
        border: '1px solid rgba(127, 140, 165, 0.22)',
        borderRadius: 18,
        padding: '36px 32px',
        textAlign: 'center',
        boxShadow: '0 24px 50px rgba(0, 0, 0, 0.25)',
      }}
    >
      <div
        style={{
          width: 58,
          height: 58,
          margin: '0 auto 20px',
          borderRadius: '50%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'var(--accent-soft)',
          color: TONE_COLORS[tone] ?? TONE_COLORS.info,
        }}
      >
        {tone === 'loading' ? <Spinner /> : <StatusGlyph tone={tone} />}
      </div>

      {eyebrow ? (
        <p
          style={{
            margin: '0 0 8px',
            fontSize: 12,
            fontWeight: 700,
            letterSpacing: '0.14em',
            textTransform: 'uppercase',
            color: 'var(--accent)',
          }}
        >
          {eyebrow}
        </p>
      ) : null}

      <h1 style={{ margin: '0 0 12px', fontSize: 24, color: 'var(--text)' }}>{title}</h1>
      <p style={{ margin: '0 0 24px', color: 'var(--text-muted)', lineHeight: 1.6 }}>{message}</p>

      {children ? (
        <div style={{ display: 'flex', justifyContent: 'center', gap: 12, flexWrap: 'wrap' }}>
          {children}
        </div>
      ) : null}
    </div>
  </main>
);

export default EmailActionLayout;
