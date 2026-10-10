import { useState, useSyncExternalStore } from 'react';
import { Button } from '@forge/design-system';
import { useOnshapeContext } from '../store';
import {
  clearDiagnostics,
  diagnosticSnapshot,
  enableDiagnostics,
  resetDiagnostics,
  subscribeDiagnostics,
} from './diagnostics';

export default function SelectionDiagnostic() {
  const client = useOnshapeContext();
  const state = useSyncExternalStore(subscribeDiagnostics, diagnosticSnapshot);
  const [notice, setNotice] = useState('');
  if (!import.meta.env.DEV || !client.context) return null;
  return (
    <section
      className="selection-diagnostic"
      aria-label="Development selection diagnostic"
    >
      <span className="eyebrow">DEVELOPMENT ONLY</span>
      <h2>Selection diagnostic</h2>
      <p>
        Inspect structure from the verified Onshape parent. Values and unknown
        field names are redacted. Diagnostic capture is separate from live
        selection validation.
      </p>
      {!state.enabled ? (
        <Button
          onClick={() => {
            enableDiagnostics();
            setNotice('');
          }}
        >
          Enable sanitized selection diagnostic
        </Button>
      ) : (
        <>
          <p role="status">
            {state.structure
              ? 'Sanitized SELECTION structure received.'
              : 'Listening for SELECTION. Select a face or edge in Onshape.'}
          </p>
          {state.structure && (
            <>
              <label htmlFor="selection-structure">Sanitized structure</label>
              <textarea
                id="selection-structure"
                readOnly
                spellCheck={false}
                value={state.structure}
                rows={16}
              />
            </>
          )}
          <div className="diagnostic-actions">
            <Button
              disabled={!state.structure}
              onClick={() => {
                if (!state.structure) return;
                if (!navigator.clipboard) {
                  setNotice('Select the sanitized text and copy it manually.');
                  return;
                }
                void navigator.clipboard.writeText(state.structure).then(
                  () => setNotice('Sanitized structure copied.'),
                  () =>
                    setNotice(
                      'Select the sanitized text and copy it manually.',
                    ),
                );
              }}
            >
              Copy sanitized structure
            </Button>
            <Button
              onClick={() => {
                clearDiagnostics();
                setNotice('');
              }}
            >
              Clear diagnostic
            </Button>
            <Button
              onClick={() => {
                resetDiagnostics();
                setNotice('');
              }}
            >
              Disable diagnostic
            </Button>
          </div>
          {notice && <p role="status">{notice}</p>}
          <p className="small muted">
            Only the latest sanitized structure stays in memory. Clear before
            each sample. Reloading disables capture. Share only the copied
            structure, labeled face, edge, or cleared.
          </p>
        </>
      )}
    </section>
  );
}
