'use client';

import { useState } from 'react';
import { Button, Input, Label, Modal, TextArea, TextField } from '@heroui/react';
import { submitReport } from '@/lib/api';
import { track } from '@/lib/analytics';

const REASONS: [string, string][] = [
  ['wrong_email', 'Wrong email'],
  ['wrong_title', 'Wrong title'],
  ['wrong_photo', 'Wrong photo'],
  ['wrong_bio', 'Wrong bio or summary'],
  ['wrong_papers', 'Wrong publications'],
  ['wrong_tags', 'Wrong research tags'],
  ['duplicate', 'Duplicate professor'],
  ['retired_moved', 'Retired or moved'],
  ['other', 'Something else'],
];

export function ReportIssueModal({ isOpen, onClose, professorId, onSubmitted }: {
  isOpen: boolean;
  onClose: () => void;
  professorId: number;
  onSubmitted?: (message: string) => void;
}) {
  const [reason, setReason] = useState('wrong_email');
  const [description, setDescription] = useState('');
  const [sourceUrl, setSourceUrl] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  async function submit() {
    setError('');
    if (description.trim().length < 10) {
      setError('Describe the problem in at least 10 characters so admins can act on it.');
      return;
    }
    setSubmitting(true);
    try {
      const response = await submitReport({
        target_type: 'professor',
        target_id: professorId,
        reason,
        description: description.trim(),
        source_url: sourceUrl.trim() || undefined,
      });
      track('report_submitted', { target_type: 'professor', reason });
      onSubmitted?.(response.message);
      setDescription('');
      setSourceUrl('');
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not submit the report. Try again.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal isOpen={isOpen} onOpenChange={(open: boolean) => { if (!open) onClose(); }}>
      <Modal.Backdrop>
        <Modal.Container>
          <Modal.Dialog className="sm:max-w-[460px]" aria-labelledby="report-title">
            <Modal.CloseTrigger />
            <Modal.Header>
              <Modal.Heading id="report-title">Report incorrect data</Modal.Heading>
            </Modal.Header>
            <Modal.Body style={{ display: 'grid', gap: 14 }}>
              <p className="muted small-text">Reports go to an admin review queue. Nothing changes on the public profile until an admin verifies the correction.</p>
              <label className="label">
                What is wrong?
                <select className="select" value={reason} onChange={e => setReason(e.target.value)}>
                  {REASONS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                </select>
              </label>
              <TextField>
                <Label>Describe the problem</Label>
                <TextArea value={description} onChange={e => setDescription(e.target.value)} placeholder="What is incorrect, and what should it say instead?" rows={4} />
              </TextField>
              <TextField>
                <Label>Source URL (optional)</Label>
                <Input value={sourceUrl} onChange={e => setSourceUrl(e.target.value)} placeholder="https://… page that shows the correct information" />
              </TextField>
              {error && <div className="error">{error}</div>}
            </Modal.Body>
            <Modal.Footer>
              <Button variant="secondary" onPress={onClose} isDisabled={submitting}>Cancel</Button>
              <Button onPress={submit} isDisabled={submitting} isPending={submitting}>{submitting ? 'Submitting…' : 'Submit report'}</Button>
            </Modal.Footer>
          </Modal.Dialog>
        </Modal.Container>
      </Modal.Backdrop>
    </Modal>
  );
}
