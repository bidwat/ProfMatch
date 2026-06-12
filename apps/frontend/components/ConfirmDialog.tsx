'use client';

import { Button, Input, Label, Modal, TextField } from '@heroui/react';

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
  const needsValue = value !== undefined && onValueChange;
  const disabled = !!confirming || (!!needsValue && !value!.trim());
  return (
    <Modal isOpen={open} onOpenChange={(next: boolean) => { if (!next && !confirming) onCancel(); }}>
      <Modal.Backdrop>
        <Modal.Container>
          <Modal.Dialog className="sm:max-w-[420px]" aria-labelledby="confirm-title">
            <Modal.Header>
              <Modal.Icon className={variant === 'danger' ? 'bg-danger text-danger-foreground' : variant === 'warning' ? 'bg-warning text-warning-foreground' : 'bg-default text-foreground'}>
                <span aria-hidden>{variant === 'danger' ? '!' : variant === 'warning' ? '•' : '✓'}</span>
              </Modal.Icon>
              <Modal.Heading id="confirm-title">{title}</Modal.Heading>
            </Modal.Header>
            <Modal.Body>
              <p className="muted">{message}</p>
              {needsValue && (
                <TextField style={{ marginTop: 14 }}>
                  <Label>{valueLabel || 'Value'}</Label>
                  <Input value={value} placeholder={valuePlaceholder} onChange={e => onValueChange!(e.target.value)} autoFocus />
                </TextField>
              )}
            </Modal.Body>
            <Modal.Footer>
              <Button variant="secondary" onPress={onCancel} isDisabled={confirming}>{cancelLabel}</Button>
              <Button variant={variant === 'danger' ? 'danger' : 'primary'} onPress={onConfirm} isDisabled={disabled} isPending={confirming}>
                {confirming ? 'Working…' : confirmLabel}
              </Button>
            </Modal.Footer>
          </Modal.Dialog>
        </Modal.Container>
      </Modal.Backdrop>
    </Modal>
  );
}
