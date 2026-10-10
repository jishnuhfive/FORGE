import { useState } from 'react';
import { Button } from '@forge/design-system';
import { sanitizedLaunchDiagnostic } from './launch';

export default function LaunchDiagnostic() {
  const [report, setReport] = useState<string | null>(null);
  const [notice, setNotice] = useState('');
  if (!import.meta.env.DEV || window.location.pathname !== '/extension')
    return null;
  return (
    <section
      className="selection-diagnostic"
      aria-label="Development launch diagnostic"
    >
      <span className="eyebrow">DEVELOPMENT ONLY</span>
      <h2>Launch context diagnostic</h2>
      <p>
        Inspect parameter names, presence, types, lengths and validation
        reasons. Values stay hidden. This does not authorize the launch or
        change validation.
      </p>
      <Button
        onClick={() => {
          setReport(
            sanitizedLaunchDiagnostic(
              window.location.search,
              window.parent !== window,
              true,
            ),
          );
          setNotice('');
        }}
      >
        Show sanitized launch diagnostic
      </Button>
      {report && (
        <>
          <label className="field-label" htmlFor="launch-diagnostic">
            Sanitized launch context
          </label>
          <textarea
            id="launch-diagnostic"
            readOnly
            spellCheck={false}
            rows={16}
            value={report}
          />
          <div className="diagnostic-actions">
            <Button
              onClick={() => {
                if (!navigator.clipboard) {
                  setNotice('Select the sanitized text and copy it manually.');
                  return;
                }
                void navigator.clipboard.writeText(report).then(
                  () => setNotice('Sanitized launch diagnostic copied.'),
                  () =>
                    setNotice(
                      'Select the sanitized text and copy it manually.',
                    ),
                );
              }}
            >
              Copy sanitized launch diagnostic
            </Button>
            <Button
              onClick={() => {
                setReport(null);
                setNotice('');
              }}
            >
              Clear launch diagnostic
            </Button>
          </div>
        </>
      )}
      {notice && <p role="status">{notice}</p>}
      <p className="small muted">
        Only sanitized text stays in memory. All query values are strings.
        Untrusted origins and suspicious parameter names are redacted. No
        logging or uploads.
      </p>
    </section>
  );
}
