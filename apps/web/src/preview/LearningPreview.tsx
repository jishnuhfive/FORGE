import { useReducer, useState } from 'react';
import { Learn } from '../features/Learn';
import { LearningContext } from '../learning/context';
import { sketchToSolid } from '../learning/sample';
import { initialSession, reduceSession } from '../learning/session';
import type { LearningAction, LearningSession } from '../learning/session';
import type { LessonResource } from '../learning/catalog';

const states = [
  'Setup',
  'Experience selected',
  'Introduction',
  'Active step',
  'Why open',
  'Vocabulary open',
  'Conceptual hint',
  'Tool-specific hint',
  'Full explanation',
  'Mid-lesson',
  'Completion',
  'No lesson selected',
  'Lesson unavailable',
  'Loading failure',
  'Invalid definition',
] as const;
type PreviewState = (typeof states)[number];
function previewSession(view: PreviewState) {
  let state = initialSession();
  const send = (action: LearningAction) => {
    state = reduceSession(sketchToSolid, state, action);
  };
  if (view === 'Setup') return state;
  send({ type: 'experience', value: 'beginner' });
  if (view === 'Experience selected') return state;
  send({ type: 'goal', value: 'fundamentals' });
  send({ type: 'review' });
  if (view === 'Introduction') return state;
  send({ type: 'start' });
  if (view === 'Why open') send({ type: 'why', stepId: 'sketch' });
  if (view === 'Vocabulary open')
    send({ type: 'vocabulary', stepId: 'sketch', termId: 'sketch' });
  const hints =
    view === 'Conceptual hint'
      ? 1
      : view === 'Tool-specific hint'
        ? 2
        : ['Full explanation', 'Mid-lesson', 'Completion'].includes(view)
          ? 3
          : 0;
  for (let level = 1; level <= hints; level++)
    send({ type: 'hint', stepId: 'sketch', level: level as 1 | 2 | 3 });
  if (view === 'Mid-lesson' || view === 'Completion') {
    for (const step of view === 'Completion'
      ? sketchToSolid.steps
      : sketchToSolid.steps.slice(0, 1)) {
      send({ type: 'mark-done', stepId: step.id });
      send({ type: 'advance', stepId: step.id });
    }
  }
  return state;
}
function PreviewSession({ view }: { view: PreviewState }) {
  const [session, dispatch] = useReducer(
    (state: LearningSession, action: LearningAction) =>
      reduceSession(sketchToSolid, state, action),
    view,
    previewSession,
  );
  const unavailable: Record<string, LessonResource> = {
    'No lesson selected': { status: 'empty' },
    'Lesson unavailable': { status: 'unavailable' },
    'Loading failure': { status: 'load-error' },
    'Invalid definition': { status: 'invalid' },
  };
  return (
    <LearningContext.Provider
      value={{ lesson: sketchToSolid, session, dispatch }}
    >
      <Learn resource={unavailable[view]} />
    </LearningContext.Provider>
  );
}
export default function LearningPreview() {
  const [view, setView] = useState<PreviewState>('Setup');
  return (
    <>
      <label className="inspector-preview-control">
        Learning preview state
        <select
          value={view}
          onChange={(event) => setView(event.target.value as PreviewState)}
        >
          {states.map((state) => (
            <option key={state}>{state}</option>
          ))}
        </select>
      </label>
      <PreviewSession key={view} view={view} />
    </>
  );
}
