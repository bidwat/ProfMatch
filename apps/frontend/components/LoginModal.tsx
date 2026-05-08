'use client';

import Link from 'next/link';

export function LoginModal({ isOpen, onClose, message }: { isOpen: boolean; onClose: () => void; message?: string }) {
  if (!isOpen) return null;

  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={onClose}>
      <div className="modal-card" role="dialog" aria-modal="true" aria-labelledby="login-modal-title" onMouseDown={event => event.stopPropagation()}>
        <button className="ghost small" aria-label="Close" onClick={onClose} style={{ float: 'right' }}>✕</button>
        <div className="modal-icon">PM</div>
        <h3 id="login-modal-title">Log in required</h3>
        <p className="muted" style={{ marginTop: 8, lineHeight: 1.6 }}>
          {message || 'You must be logged in to use this feature.'}
        </p>
        <div style={{ display: 'grid', gap: 10, marginTop: 22 }}>
          <Link className="button primary" href="/signin">Sign in</Link>
          <Link className="button secondary" href="/signup">Create an account</Link>
        </div>
      </div>
    </div>
  );
}
