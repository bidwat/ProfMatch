export default function Loading() {
  return (
    <div className="page" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '40vh' }}>
      <div className="muted" style={{ fontSize: '1.2rem', display: 'flex', alignItems: 'center', gap: '12px' }}>
        <span className="spinner" style={{
          display: 'inline-block',
          width: '24px',
          height: '24px',
          border: '3px solid var(--border)',
          borderTopColor: 'var(--primary)',
          borderRadius: '50%',
          animation: 'spin 1s linear infinite'
        }}></span>
        Loading...
      </div>
    </div>
  );
}
