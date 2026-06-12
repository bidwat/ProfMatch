'use client';

import Link from 'next/link';
import { Modal } from '@heroui/react';

export function LoginModal({ isOpen, onClose, message }: { isOpen: boolean; onClose: () => void; message?: string }) {
  return (
    <Modal isOpen={isOpen} onOpenChange={(open: boolean) => { if (!open) onClose(); }}>
      <Modal.Backdrop>
        <Modal.Container>
          <Modal.Dialog className="sm:max-w-[400px]" aria-labelledby="login-modal-title">
            <Modal.CloseTrigger />
            <Modal.Header>
              <Modal.Icon className="bg-default text-foreground"><span style={{ fontFamily: 'var(--font-display)', fontWeight: 700 }}>PM</span></Modal.Icon>
              <Modal.Heading id="login-modal-title">Log in required</Modal.Heading>
            </Modal.Header>
            <Modal.Body>
              <p className="muted" style={{ lineHeight: 1.6 }}>
                {message || 'You must be logged in to use this feature.'}
              </p>
            </Modal.Body>
            <Modal.Footer style={{ display: 'grid', gap: 10 }}>
              <Link className="button primary" href="/signin">Sign in</Link>
              <Link className="button secondary" href="/signup">Create an account</Link>
            </Modal.Footer>
          </Modal.Dialog>
        </Modal.Container>
      </Modal.Backdrop>
    </Modal>
  );
}
