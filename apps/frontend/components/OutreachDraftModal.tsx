'use client';

import { useState } from 'react';
import { Button, Label, Modal, TextArea, TextField } from '@heroui/react';
import { generateOutreachDraft, type OutreachDraft } from '@/lib/api';

const PURPOSES: [string, string][] = [
  ['phd_inquiry', 'PhD inquiry'],
  ['masters_research_inquiry', "Master's research inquiry"],
  ['undergraduate_research_inquiry', 'Undergraduate research inquiry'],
  ['research_assistantship', 'Research assistantship'],
  ['general_introduction', 'General introduction'],
  ['follow_up', 'Follow-up email'],
];

export function OutreachDraftModal({ isOpen, onClose, professorId, professorName, onToast }: {
  isOpen: boolean;
  onClose: () => void;
  professorId: number;
  professorName: string;
  onToast?: (message: string) => void;
}) {
  const [purpose, setPurpose] = useState('phd_inquiry');
  const [extraContext, setExtraContext] = useState('');
  const [draft, setDraft] = useState<OutreachDraft | null>(null);
  const [error, setError] = useState('');
  const [generating, setGenerating] = useState(false);

  async function generate() {
    setError('');
    setGenerating(true);
    try {
      setDraft(await generateOutreachDraft({ professor_id: professorId, purpose, extra_context: extraContext.trim() || undefined }));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not generate a draft. Try again.');
    } finally {
      setGenerating(false);
    }
  }

  async function copyDraft() {
    if (!draft) return;
    await navigator.clipboard.writeText(`Subject: ${draft.subject}\n\n${draft.body}`);
    onToast?.('Draft copied. Personalize it before sending.');
  }

  return (
    <Modal isOpen={isOpen} onOpenChange={(open: boolean) => { if (!open) onClose(); }}>
      <Modal.Backdrop>
        <Modal.Container>
          <Modal.Dialog className="sm:max-w-[560px]" aria-labelledby="outreach-title">
            <Modal.CloseTrigger />
            <Modal.Header>
              <Modal.Heading id="outreach-title">Draft outreach email · {professorName}</Modal.Heading>
            </Modal.Header>
            <Modal.Body style={{ display: 'grid', gap: 14 }}>
              <div className="notice">ProfMatch does not send this email. Review the professor&apos;s website and personalize the draft before sending.</div>
              <label className="label">
                Purpose
                <select className="select" value={purpose} onChange={e => setPurpose(e.target.value)}>
                  {PURPOSES.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                </select>
              </label>
              <TextField>
                <Label>Anything specific to mention? (optional)</Label>
                <TextArea value={extraContext} onChange={e => setExtraContext(e.target.value)} placeholder="e.g. a project of yours that connects to their recent work" rows={2} />
              </TextField>
              {error && <div className="error">{error}</div>}
              {draft && (
                <div className="card soft" style={{ display: 'grid', gap: 10 }}>
                  <strong>Subject: {draft.subject}</strong>
                  <p style={{ whiteSpace: 'pre-wrap', lineHeight: 1.6, margin: 0 }}>{draft.body}</p>
                  {draft.suggested_paper && <p className="muted small-text">Suggested paper to mention: {draft.suggested_paper}</p>}
                  {draft.personalization_checklist.length > 0 && (
                    <ul className="muted small-text" style={{ margin: 0, paddingLeft: 18 }}>
                      {draft.personalization_checklist.map(item => <li key={item}>{item}</li>)}
                    </ul>
                  )}
                </div>
              )}
            </Modal.Body>
            <Modal.Footer>
              <Button variant="secondary" onPress={onClose}>Close</Button>
              {draft && <Button variant="secondary" onPress={copyDraft}>Copy draft</Button>}
              <Button onPress={generate} isDisabled={generating} isPending={generating}>{generating ? 'Generating…' : draft ? 'Regenerate' : 'Generate draft'}</Button>
            </Modal.Footer>
          </Modal.Dialog>
        </Modal.Container>
      </Modal.Backdrop>
    </Modal>
  );
}
