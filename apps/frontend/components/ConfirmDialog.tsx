'use client';

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: 'default' | 'warning' | 'danger';
  value?: string;
  valueLabel?: string;
  valuePlaceholder?: string;
  onValueChange?: (value: string) => void;
  onConfirm: () => void;
  onCancel: () => void;
  confirming?: boolean;
}

export function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  variant = 'default',
  value,
  valueLabel,
  valuePlaceholder,
  onValueChange,
  onConfirm,
  onCancel,
  confirming,
}: ConfirmDialogProps) {
  if (!open) return null;
  const needsValue = value !== undefined && onValueChange;
  const disabled = confirming || (needsValue && !value.trim());
  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={onCancel}>
      <div className={`modal-card confirm-dialog ${variant}`} role="dialog" aria-modal="true" aria-labelledby="confirm-title" onMouseDown={e => e.stopPropagation()}>
        <div className={`modal-icon ${variant}`}>{variant === 'danger' ? '!' : variant === 'warning' ? '•' : '✓'}</div>
        <h3 id="confirm-title">{title}</h3>
        <p className="muted">{message}</p>
        {needsValue && (
          <label className="label" style={{ marginTop: 14 }}>
            {valueLabel || 'Value'}
            <input className="input" value={value} placeholder={valuePlaceholder} onChange={e => onValueChange(e.target.value)} autoFocus />
          </label>
        )}
        <div className="row end" style={{ marginTop: 18 }}>
          <button className="button secondary" onClick={onCancel} disabled={confirming}>{cancelLabel}</button>
          <button className={`button ${variant === 'danger' ? 'danger-primary' : 'primary'}`} onClick={onConfirm} disabled={disabled}>{confirming ? 'Working…' : confirmLabel}</button>
        </div>
      </div>
    </div>
  );
}
