import { useState } from 'react';
import {
  Badge,
  Button,
  Dropdown,
  ErrorState,
  ForgeMark,
  GlassSurface,
  Skeleton,
  StatusBadge,
  Tabs,
} from '@forge/design-system';
import { MoreHorizontal } from 'lucide-react';
import { AnalysisEmpty, AnswerContent } from '../ai/Analysis';
import { messages, stages } from '../ai/api';
import {
  syntheticAnswer,
  syntheticOverview,
  syntheticSelectionAnswer,
  syntheticWriteAnswer,
} from '../ai/__fixtures__/response';
import { PromptComposer } from '../components/PromptComposer';

const states = [
  'First launch',
  'Answer',
  'Mass unavailable',
  'Validation unavailable',
  'Write request',
  'Capacity limit',
  'Provider timeout',
  'Verification failure',
  'Cancelled',
  'Context changed',
  'Empty Part Studio',
  'Selection unknown',
  'No selection',
  'FACE',
  'EDGE',
  'Sending',
  'Inspecting CAD',
  'Reviewing evidence',
  'Preparing answer',
  'AI unavailable',
  'CAD unavailable',
  'Signed out',
] as const;
type State = (typeof states)[number];
export default function Phase65Preview({
  showcase = false,
}: {
  showcase?: boolean;
}) {
  const [state, setState] = useState<State>('First launch');
  const [mode, setMode] = useState('design');
  const [brightBackdrop, setBrightBackdrop] = useState(false);
  const errors = {
    'Capacity limit': messages.capacity_unavailable,
    'Provider timeout': messages.timeout,
    'Verification failure': messages.invalid_response,
    Cancelled: messages.cancelled,
    'AI unavailable': messages.not_configured,
    'CAD unavailable': messages.context_unavailable,
    'Signed out': 'Connect your Onshape account to continue.',
  };
  const error = state in errors ? errors[state as keyof typeof errors] : null;
  const progress =
    state === 'Sending'
      ? stages.understanding
      : state === 'Inspecting CAD'
        ? stages.inspecting
        : state === 'Reviewing evidence'
          ? stages.reviewing
          : state === 'Preparing answer'
            ? stages.preparing
            : undefined;
  const answer = [
    'Answer',
    'Mass unavailable',
    'Validation unavailable',
    'Write request',
    'Empty Part Studio',
    'FACE',
    'EDGE',
  ].includes(state);
  const result =
    state === 'Write request'
      ? syntheticWriteAnswer
      : state === 'FACE' || state === 'EDGE'
        ? syntheticSelectionAnswer(state)
        : state === 'Empty Part Studio'
          ? {
              ...syntheticAnswer,
              answer:
                'This Part Studio has no returned features, parts or bodies.',
              evidence: [
                {
                  id: 'empty',
                  status: 'verified' as const,
                  statement:
                    'The returned feature, part and body lists are empty.',
                },
              ],
              uncertainties: [
                'An empty inventory does not establish engineering validity.',
              ],
            }
          : state === 'Validation unavailable'
            ? {
                ...syntheticAnswer,
                answer: 'No deterministic engineering validation has run.',
                uncertainties: [
                  'Strength, fit and manufacturing suitability are unverified.',
                ],
              }
            : state === 'Mass unavailable'
              ? {
                  ...syntheticOverview,
                  uncertainties: [
                    'Mass is unavailable; material or density may be missing.',
                    ...syntheticAnswer.uncertainties,
                  ],
                }
              : syntheticOverview;
  return (
    <>
      <div className="feature">
        <label className="field-label" htmlFor="phase65-state">
          Workspace state
        </label>
        <select
          id="phase65-state"
          className="input"
          value={state}
          onChange={(event) => {
            const next = states.find((value) => value === event.target.value);
            if (next) setState(next);
          }}
        >
          {states.map((value) => (
            <option key={value}>{value}</option>
          ))}
        </select>
        <p className="small muted">
          Synthetic Phase 6.5 review. State changes are manual.
        </p>
      </div>
      {showcase ? (
        <div className="feature material-showcase">
          <h1>Quiet engineering precision</h1>
          <section>
            <h2>Oblique Plane</h2>
            <div className="brand-samples">
              <ForgeMark />
              <ForgeMark />
              <ForgeMark />
              <span className="brand-light">
                <ForgeMark />
              </span>
            </div>
          </section>
          <section>
            <h2>Functional material</h2>
            <label className="settings-row">
              <span>Bright backdrop stress test</span>
              <input
                type="checkbox"
                checked={brightBackdrop}
                onChange={(event) => setBrightBackdrop(event.target.checked)}
              />
            </label>
            <div
              className={`material-backdrop${brightBackdrop ? ' material-backdrop--bright' : ''}`}
            >
              <GlassSurface className="material-sample">
                <span>Local edge light · move the pointer</span>
                <div className="action-bar">
                  <Button variant="primary">Primary</Button>
                  <Button>Secondary</Button>
                  <Button disabled>Disabled</Button>
                  <Dropdown
                    label="Material menu"
                    items={[
                      {
                        label: 'Sample menu action',
                        onSelect: () => undefined,
                      },
                    ]}
                  >
                    <MoreHorizontal size={16} aria-hidden="true" />
                  </Dropdown>
                </div>
              </GlassSurface>
            </div>
          </section>
          <section>
            <h2>Navigation</h2>
            <Tabs
              label="Sample navigation"
              value={mode}
              onValueChange={setMode}
              items={[
                {
                  id: 'design',
                  label: 'Design',
                  content: <p className="small muted">Read-only analysis</p>,
                },
                {
                  id: 'modify',
                  label: 'Modify',
                  content: (
                    <p className="small muted">CAD changes are planned.</p>
                  ),
                },
                {
                  id: 'learn',
                  label: 'Learn',
                  content: (
                    <p className="small muted">
                      Authored reading. CAD validation unavailable.
                    </p>
                  ),
                },
              ]}
            />
          </section>
          <section>
            <h2>Evidence and validation states</h2>
            <div className="chip-list">
              <StatusBadge status="pass" label="Verified" />
              <StatusBadge status="pending" label="Unknown" />
              <StatusBadge status="unverified" label="Unverified" />
              <StatusBadge status="warning" label="Warning" />
              <StatusBadge status="fail" label="Failed" />
            </div>
            <article className="ai-exchange">
              <AnswerContent result={result} />
            </article>
          </section>
          <section>
            <h2>Error</h2>
            <ErrorState
              title="AI capacity temporarily unavailable"
              description="Wait a moment, then try again."
            >
              <Button>Try again</Button>
            </ErrorState>
          </section>
          <section>
            <h2>Loading</h2>
            <Skeleton label="Loading preview" rows={2} />
          </section>
          <section>
            <h2>Empty state</h2>
            <AnalysisEmpty />
          </section>
          <section>
            <h2>Selection</h2>
            <div className="chip-list">
              {[
                'Selection unknown',
                'No selection',
                '1 face selected',
                '1 edge selected',
              ].map((label) => (
                <Badge key={label}>{label}</Badge>
              ))}
            </div>
          </section>
          <section>
            <h2>Composer and progress</h2>
            <PromptComposer
              label="Sample prompt"
              placeholder="Ask about this model…"
              context="1 face selected"
              progress={progress}
              busy={!!progress}
              onCancel={() => setState('Cancelled')}
              onSubmit={() => setState('Answer')}
              hint="Synthetic preview only"
            />
          </section>
        </div>
      ) : (
        <>
          <Tabs
            label="Preview engineering mode"
            value={mode}
            onValueChange={setMode}
            items={['design', 'modify', 'learn'].map((id) => ({
              id,
              label: id[0]!.toUpperCase() + id.slice(1),
              content: (
                <p className="sr-only">
                  {id === 'design' ? 'Read-only workspace' : 'Preview only'}
                </p>
              ),
            }))}
          />
          {mode === 'design' ? (
            <div className="feature design-feature">
              <h1 className="sr-only">Design workspace preview</h1>
              <section
                className="ai-analysis"
                data-empty={!answer}
                aria-label="Synthetic analysis preview"
              >
                {!answer && (
                  <div className="analysis-intro-slot">
                    {progress ? (
                      <div className="user-prompt">
                        What is in this Part Studio?
                      </div>
                    ) : !error ? (
                      <AnalysisEmpty />
                    ) : null}
                  </div>
                )}
                {state === 'Context changed' && (
                  <p className="notice">
                    Part Studio changed. The previous conversation has been
                    cleared.
                  </p>
                )}
                {answer && (
                  <article key={state} className="ai-exchange">
                    <div className="user-prompt">
                      {state === 'Write request'
                        ? 'Make this model 20 mm wider.'
                        : 'What is in this Part Studio?'}
                    </div>
                    <AnswerContent result={result} />
                  </article>
                )}
                {error && (
                  <ErrorState title={state} description={error}>
                    <Button onClick={() => setState('Sending')}>
                      {state === 'Signed out'
                        ? 'Continue with Onshape'
                        : 'Try again'}
                    </Button>
                  </ErrorState>
                )}
                <PromptComposer
                  label="Preview prompt"
                  placeholder="Ask about this Part Studio…"
                  context={
                    state === 'FACE'
                      ? '1 face selected'
                      : state === 'EDGE'
                        ? '1 edge selected'
                        : state === 'No selection'
                          ? 'No selection'
                          : 'Selection unknown'
                  }
                  progress={progress}
                  busy={!!progress}
                  onCancel={() => setState('Cancelled')}
                  onSubmit={() => setState('Answer')}
                  showSuggestions={!answer}
                  suggestions={[
                    "What's in this model?",
                    'Explain the selected face',
                    'How would you approach modifying this?',
                  ]}
                  hint="Ask about the current model"
                  privacy="Synthetic preview. No prompt or CAD evidence leaves this lab."
                />
                <p className="sr-only">
                  No engineering validation has run. Synthetic preview only.
                </p>
              </section>
            </div>
          ) : (
            <div className="feature">
              <h1>
                {mode === 'modify'
                  ? 'CAD changes are planned'
                  : 'Authored learning'}
              </h1>
              <p className="muted">
                {mode === 'modify'
                  ? 'Ask Design to explain an approach. This preview cannot apply changes.'
                  : 'Open Learn in the workspace for the local reading lesson. CAD validation is unavailable.'}
              </p>
            </div>
          )}
        </>
      )}
    </>
  );
}
