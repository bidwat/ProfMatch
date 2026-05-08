'use client';

import { useEffect } from 'react';

export function Toast({ message, tone = 'success', onClose }: { message: string; tone?: 'success' | 'warning' | 'error'; onClose?: () => void }) {
  useEffect(() => {
    if (!message || !onClose) return;
    const id = window.setTimeout(onClose, 3200);
    return () => window.clearTimeout(id);
  }, [message, onClose]);
  if (!message) return null;
  return (
    <div className={`toast toast-${tone}`} role="status" aria-live="polite">
      <span className="toast-dot" />
      <span>{message}</span>
      {onClose && <button className="ghost small" onClick={onClose} aria-label="Dismiss notification">✕</button>}
    </div>
  );
}
