import { useState } from 'react';
import RefinementComparison from './RefinementComparison';
import Phase65Preview from './Phase65Preview';
import InspectorPreview from './InspectorPreview';
import {
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorState,
  Skeleton,
  StatusBadge,
} from '@forge/design-system';
import { Shell } from '../components/Shell';
import { Onboarding } from '../components/Onboarding';
import { CadContext } from '../components/CadContext';
import { Design } from '../features/Design';
import { EngineeringBrief } from '../features/EngineeringBrief';
import { DesignPlan } from '../features/DesignPlan';
import { AgentProgress } from '../features/AgentProgress';
import { ValidationReport } from '../features/ValidationReport';
import { Modify } from '../features/Modify';
import { Learn } from '../features/Learn';
import { Settings } from '../features/Settings';
import { History } from '../features/History';
import { errors } from '../lib/errors';
import type {
  CadContext as Context,
  ErrorCode,
  Preferences,
} from '../lib/types';
import {
  sampleBrief,
  sampleContext,
  sampleHistory,
  sampleSteps,
  sampleValidation,
} from './data';

const views = [
  'Material comparison',
  'Logo candidates',
  'Phase 6.5 workspace',
  'Phase 6.5 design system',
  'CAD inspector',
  'Design empty',
  'Engineering brief',
  'Plan',
  'Agent running',
  'Agent failed',
  'Validation report',
  'Validation failure',
  'No validation results',
  'Modify mode',
  'Learn mode',
  'Settings',
  'History',
  'Onshape disconnected',
  'No document',
  'Error states',
  'Loading states',
  'Components',
] as const;
type View = (typeof views)[number];
export default function UiLab({
  preferences,
  onPreferencesChange,
  storageAvailable,
}: {
  preferences: Preferences;
  onPreferencesChange: (preferences: Preferences) => void;
  storageAvailable: boolean;
}) {
  const [view, setView] = useState<View>('Design empty');
  const [width, setWidth] = useState('narrow');
  const [error, setError] = useState<ErrorCode>('network');
  const [reduceMotion, setReduceMotion] = useState(false);
  const [reduceTransparency, setReduceTransparency] = useState(false);
  const [contrast, setContrast] = useState(false);
  const [intro, setIntro] = useState(false);
  const [message, setMessage] = useState('');
  const context: Context =
    view === 'Onshape disconnected'
      ? { kind: 'disconnected' }
      : view === 'No document'
        ? { kind: 'no-document' }
        : sampleContext;
  let content;
  switch (view) {
    case 'Material comparison':
    case 'Logo candidates':
      content = <RefinementComparison logos={view === 'Logo candidates'} />;
      break;
    case 'Phase 6.5 workspace':
    case 'Phase 6.5 design system':
      content = (
        <Phase65Preview showcase={view === 'Phase 6.5 design system'} />
      );
      break;
    case 'CAD inspector':
      content = <InspectorPreview />;
      break;
    case 'Design empty':
      content = (
        <Design preview onSubmit={() => setView('Engineering brief')} />
      );
      break;
    case 'Engineering brief':
      content = (
        <EngineeringBrief
          sections={sampleBrief}
          onContinue={() => setView('Plan')}
        />
      );
      break;
    case 'Plan':
      content = (
        <DesignPlan
          onApprove={() => setView('Agent running')}
          onRevise={() => setView('Engineering brief')}
          onCancel={() => setView('Design empty')}
        />
      );
      break;
    case 'Agent running':
    case 'Agent failed':
      content = (
        <AgentProgress
          key={view}
          steps={sampleSteps}
          initial={view === 'Agent failed' ? 'failed' : 'active'}
          onReport={() => setView('Validation report')}
        />
      );
      break;
    case 'Validation report':
    case 'Validation failure':
    case 'No validation results':
      content = (
        <ValidationReport
          checks={
            view === 'No validation results'
              ? []
              : view === 'Validation failure'
                ? sampleValidation.map((check) =>
                    check.id === 'travel'
                      ? { ...check, measured: '380 mm', status: 'fail' }
                      : check,
                  )
                : sampleValidation
          }
        />
      );
      break;
    case 'Modify mode':
      content = <Modify preview />;
      break;
    case 'Learn mode':
      content = <Learn />;
      break;
    case 'Settings':
      content = (
        <Settings
          preferences={preferences}
          onChange={onPreferencesChange}
          storageAvailable={storageAvailable}
        />
      );
      break;
    case 'History':
      content = <History entries={sampleHistory} />;
      break;
    case 'Onshape disconnected':
    case 'No document':
      content = (
        <div className="feature">
          <h1>{view}</h1>
          <CadContext context={context} />
          <EmptyState
            title="Context is unavailable"
            description="No integration runs in this preview."
          />
        </div>
      );
      break;
    case 'Error states':
      content = (
        <div className="feature">
          <h1>Error states</h1>
          <label className="field-label" htmlFor="error-preview">
            Preview error
          </label>
          <select
            id="error-preview"
            className="input"
            value={error}
            onChange={(event) => {
              const next = (Object.keys(errors) as ErrorCode[]).find(
                (code) => code === event.target.value,
              );
              if (next) setError(next);
            }}
          >
            {Object.entries(errors).map(([code, info]) => (
              <option value={code} key={code}>
                {info.title}
              </option>
            ))}
          </select>
          <ErrorState {...errors[error]}>
            <Button onClick={() => setView('Design empty')}>
              Return to workspace preview
            </Button>
          </ErrorState>
          <p className="local-notice">
            Synthetic error only. No service request was made.
          </p>
        </div>
      );
      break;
    case 'Loading states':
      content = (
        <div className="feature">
          <h1>Loading workspace</h1>
          <Card>
            <Skeleton label="Loading sample engineering brief" rows={6} />
          </Card>
          <p className="local-notice">
            Static loading preview. No request is in flight.
          </p>
        </div>
      );
      break;
    case 'Components':
      content = (
        <div className="feature">
          <h1>Component reference</h1>
          <div className="chip-list">
            {(['pass', 'warning', 'fail', 'unverified'] as const).map(
              (status) => (
                <StatusBadge key={status} status={status} />
              ),
            )}
          </div>
          <div className="action-bar">
            <Button
              variant="primary"
              onClick={() =>
                setMessage('Sample action selected. No service was called.')
              }
            >
              Primary
            </Button>
            <Button
              onClick={() => setMessage('Sample secondary action selected.')}
            >
              Secondary
            </Button>
            <Button disabled>Disabled</Button>
          </div>
          <EmptyState
            title="No history"
            description="Empty-state component preview."
          />
          <ErrorState
            title="Preview error"
            description="A useful message with no raw diagnostics."
          />
          <Skeleton />
        </div>
      );
      break;
  }
  return (
    <div className="ui-lab">
      <div className="lab-banner">
        <Badge tone="accent">DEVELOPMENT ONLY</Badge>
        <strong>Forge UI lab</strong>
        <span>
          All project data, progress and validation are mock previews. No AI
          runs. No CAD changes.
        </span>
        <a href="#/" className="text-link">
          Exit lab
        </a>
      </div>
      <div className="lab-controls">
        <div>
          <label htmlFor="preview-view">Preview state</label>
          <select
            id="preview-view"
            className="input"
            value={view}
            onChange={(event) => {
              const next = views.find((v) => v === event.target.value);
              if (next) {
                setView(next);
                setMessage('');
              }
            }}
          >
            {views.map((v) => (
              <option key={v}>{v}</option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="preview-width">Layout</label>
          <select
            id="preview-width"
            className="input"
            value={width}
            onChange={(event) => setWidth(event.target.value)}
          >
            <option value="narrow">Narrow panel · 380 px</option>
            <option value="320">320 px</option>
            <option value="360">360 px</option>
            <option value="400">400 px</option>
            <option value="480">480 px</option>
            <option value="600">600 px</option>
            <option value="wide">Wide standalone</option>
          </select>
        </div>
        <div>
          <label htmlFor="preview-theme">Theme</label>
          <select
            id="preview-theme"
            className="input"
            value={preferences.theme}
            onChange={(event) => {
              const theme = event.target.value;
              if (theme === 'system' || theme === 'light' || theme === 'dark')
                onPreferencesChange({ ...preferences, theme });
            }}
          >
            <option value="system">System</option>
            <option value="light">Light</option>
            <option value="dark">Dark</option>
          </select>
        </div>
        <Button
          onClick={(event) => {
            event.currentTarget.focus();
            setIntro(true);
          }}
        >
          Preview onboarding
        </Button>
      </div>
      <div className="lab-adaptations">
        <label>
          <input
            type="checkbox"
            checked={reduceMotion}
            onChange={(event) => setReduceMotion(event.target.checked)}
          />
          Reduce motion
        </label>
        <label>
          <input
            type="checkbox"
            checked={reduceTransparency}
            onChange={(event) => setReduceTransparency(event.target.checked)}
          />
          Reduce transparency
        </label>
        <label>
          <input
            type="checkbox"
            checked={contrast}
            onChange={(event) => setContrast(event.target.checked)}
          />
          Increase contrast
        </label>
      </div>
      <div
        className={`lab-frame lab-frame--${width}`}
        style={{ maxWidth: /^\d+$/.test(width) ? `${width}px` : undefined }}
        data-motion={reduceMotion ? 'reduced' : undefined}
        data-transparency={reduceTransparency ? 'reduced' : undefined}
        data-contrast={contrast ? 'more' : undefined}
      >
        {view === 'Material comparison' || view === 'Logo candidates' ? (
          <main>{content}</main>
        ) : (
          <Shell
            context={context}
            onOnboarding={() => setIntro(true)}
            onNotify={setMessage}
          >
            <main key={view}>
              {content}
              {message && (
                <p className="notice" role="status">
                  {message}
                </p>
              )}
            </main>
          </Shell>
        )}
      </div>
      <Onboarding open={intro} onClose={() => setIntro(false)} />
    </div>
  );
}
