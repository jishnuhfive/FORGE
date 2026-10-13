import { useId, useState } from 'react';
import { Button, Textarea } from '@forge/design-system';
import { sectionNames } from '../api';
import type { ReadProof } from '../api';

export default function ReadDiagnostic({ result }: { result: ReadProof }) {
  const textId = useId();
  const massId = useId();
  const [notice, setNotice] = useState('');
  const [manualText, setManualText] = useState('');
  if (!import.meta.env.DEV) return null;
  const copy = async () => {
    const report = {
      diagnostic: 'forge-rest-diagnostic-v1',
      requestId: result.request_id,
      capturedAt: result.captured_at,
      consistency: result.consistency,
      sections: Object.fromEntries(
        sectionNames.map((name) => [
          name,
          {
            status: result[name].status,
            code: result[name].code,
            retryAfterSeconds: result[name].retry_after_seconds,
          },
        ]),
      ),
    };
    const text = JSON.stringify(report, null, 2);
    // Validated proof fields keep this fixed projection below the limit.
    if (text.length > 2000) {
      setManualText('');
      setNotice('Sanitized read diagnostic exceeds the size limit.');
      return;
    }
    try {
      await navigator.clipboard.writeText(text);
      setManualText('');
      setNotice('Sanitized read diagnostic copied.');
    } catch {
      setManualText(text);
      setNotice(
        'Clipboard unavailable — select and copy the sanitized diagnostic below.',
      );
    }
  };
  return (
    <div className="small muted">
      <p>DEVELOPMENT ONLY · REST diagnostic</p>
      <Button
        variant="ghost"
        onClick={() => {
          void copy();
        }}
      >
        Copy sanitized read diagnostic
      </Button>
      <p role="status">{notice}</p>
      {manualText && (
        <>
          <label htmlFor={textId}>Sanitized read diagnostic</label>
          <Textarea
            id={textId}
            readOnly
            spellCheck={false}
            value={manualText}
            rows={10}
            style={{ maxHeight: '16rem', resize: 'vertical' }}
          />
        </>
      )}
      {result.massStructure && (
        <>
          <p>DEVELOPMENT ONLY · Mass response structure</p>
          <p>
            Select and copy the sanitized mass structure below. No numeric CAD
            values or body IDs are included.
          </p>
          <label htmlFor={massId}>Sanitized mass response structure</label>
          <Textarea
            id={massId}
            readOnly
            spellCheck={false}
            value={result.massStructure}
            rows={10}
            style={{ maxHeight: '16rem', resize: 'vertical' }}
          />
        </>
      )}
    </div>
  );
}
