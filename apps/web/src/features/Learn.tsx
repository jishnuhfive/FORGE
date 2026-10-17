import { useEffect, useRef, useState } from 'react';
import { Button, Dialog, ErrorState } from '@forge/design-system';
import { sampleResource } from '../learning/catalog';
import type { LessonResource } from '../learning/catalog';
import { useLearning } from '../learning/context';
import { LearningProvider } from '../learning/LearningProvider';
import { LearnerSetup } from '../learning/Setup';
import { experienceOptions, goalOptions } from '../learning/options';
import { HintLadder, LessonDisclosure, Vocabulary } from '../learning/Guidance';
import { LessonProgress } from '../learning/Progress';
import { CheckStep } from '../learning/CheckStep';

export function Learn({
  resource = sampleResource,
}: {
  resource?: LessonResource;
}) {
  const learning = useLearning();
  if (resource.status !== 'ready')
    return <LessonUnavailable status={resource.status} />;
  if (!learning)
    return (
      <LearningProvider lesson={resource.lesson}>
        <LearnWorkspace />
      </LearningProvider>
    );
  return <LearnWorkspace />;
}
function LessonUnavailable({
  status,
}: {
  status: Exclude<LessonResource['status'], 'ready'>;
}) {
  const messages = {
    empty: [
      'Choose a lesson',
      'No lesson is selected. The sample lesson introduces sketches, extrusion and solid bodies.',
    ],
    unavailable: [
      'Lesson unavailable',
      'This lesson is not available here. You can open the CAD fundamentals sample.',
    ],
    'load-error': [
      'The lesson couldn’t open',
      'Try opening the sample lesson again. Your model has not been changed.',
    ],
    invalid: [
      'This lesson needs an update',
      'Its content could not be opened safely. Try the available sample lesson.',
    ],
  } as const;
  const [retry, setRetry] = useState(false);
  if (retry && sampleResource.status === 'ready')
    return (
      <LearningProvider lesson={sampleResource.lesson}>
        <Learn />
      </LearningProvider>
    );
  return (
    <div className="feature learning-workspace">
      <h1>Learn</h1>
      <ErrorState title={messages[status][0]} description={messages[status][1]}>
        <Button tabIndex={0} onClick={() => setRetry(true)}>
          Open sample lesson
        </Button>
      </ErrorState>
    </div>
  );
}
function LearnWorkspace() {
  const learning = useLearning();
  const [resetOpen, setResetOpen] = useState(false);
  const heading = useRef<HTMLHeadingElement>(null);
  const session = learning?.session;
  const screen = session
    ? `${session.phase}:${'stepIndex' in session ? session.stepIndex : ''}`
    : '';
  const previousScreen = useRef(screen);
  useEffect(() => {
    // Only explicit flow transitions move focus; tab remounts and hint reveals do not.
    if (previousScreen.current !== screen) heading.current?.focus();
    previousScreen.current = screen;
  }, [screen]);
  if (!learning) return null;
  const { lesson, session: state, dispatch } = learning;
  const checkable = lesson.steps.some((step) => step.check);
  const active =
    state.phase === 'active' ? lesson.steps[state.stepIndex] : undefined;
  const interaction =
    state.phase === 'active' ? state.interactions[state.stepIndex] : undefined;
  const title =
    state.phase === 'setup'
      ? 'Learn with Forge'
      : state.phase === 'introduction'
        ? lesson.title
        : state.phase === 'completed'
          ? 'Lesson complete'
          : active?.title;
  return (
    <div className="feature learning-workspace">
      <div className="learning-context">
        <span>
          {state.phase === 'setup' ? 'Learning workspace' : lesson.title}
        </span>
        <Button
          tabIndex={0}
          variant="ghost"
          onClick={(event) => {
            event.currentTarget.focus();
            setResetOpen(true);
          }}
          disabled={state.phase === 'setup' && !state.experience && !state.goal}
        >
          Reset lesson
        </Button>
      </div>
      {active && (
        <p className="muted small">
          Step {'stepIndex' in state ? state.stepIndex + 1 : 1} of{' '}
          {lesson.steps.length}
        </p>
      )}
      <h1 ref={heading} tabIndex={-1} className="learning-title">
        {title}
      </h1>
      {state.phase === 'setup' && (
        <LearnerSetup
          experience={state.experience}
          goal={state.goal}
          dispatch={dispatch}
        />
      )}
      {state.phase === 'introduction' && (
        <>
          <p>{lesson.summary}</p>
          <p className="muted">
            {state.profile.experience === 'beginner'
              ? 'Take your time. Open unfamiliar terms and request help whenever you want.'
              : state.profile.experience === 'some-experience'
                ? 'Connect familiar tools to the reasons for choosing them. Help is available at every step.'
                : 'Focus on the reasoning behind each operation. Vocabulary and practical guidance are available when useful.'}
          </p>
          <p className="muted small">
            Your goal:{' '}
            {
              goalOptions.find((option) => option.id === state.profile.goal)
                ?.title
            }
            .{' '}
            {state.profile.goal === 'guided-project'
              ? checkable
                ? 'You build the model yourself. When you ask, Forge checks the parts of it that it can read.'
                : 'This short fundamentals sample prepares you for future guided projects.'
              : 'Start with this short fundamentals sample.'}
          </p>
          <section className="learning-section">
            <h2>What you’ll explore</h2>
            <ul>
              {lesson.learningObjectives.map((objective) => (
                <li key={objective}>{objective}</li>
              ))}
            </ul>
          </section>
          <section className="learning-section">
            <h2>Before you begin</h2>
            {lesson.prerequisites.map((item) => (
              <p key={item} className="muted">
                {item}
              </p>
            ))}
          </section>
          <p className="muted small">
            {lesson.steps.length} steps ·{' '}
            {
              experienceOptions.find(
                (option) => option.id === state.profile.experience,
              )?.title
            }{' '}
            · Progress marked by you
          </p>
          <div className="learning-continuation">
            <Button
              tabIndex={0}
              variant="primary"
              onClick={() => dispatch({ type: 'start' })}
            >
              Begin lesson
            </Button>
            <Button
              tabIndex={0}
              variant="ghost"
              onClick={() => dispatch({ type: 'edit-setup' })}
            >
              Change setup
            </Button>
          </div>
        </>
      )}
      {state.phase === 'active' && active && interaction && (
        <>
          <p className="learning-objective">
            <span className="muted">Objective</span>
            {active.objective}
          </p>
          <section className="learning-section">
            <h2>What to do</h2>
            <p>{active.instruction}</p>
          </section>
          <LessonDisclosure
            title="Why this step"
            open={interaction.whyOpen}
            onToggle={() => dispatch({ type: 'why', stepId: active.id })}
          >
            <p>{active.why}</p>
          </LessonDisclosure>
          {active.vocabulary && (
            <Vocabulary
              terms={active.vocabulary}
              interaction={interaction}
              dispatch={dispatch}
            />
          )}
          <HintLadder
            step={active}
            interaction={interaction}
            dispatch={dispatch}
          />
          {active.check && (
            <CheckStep key={active.id} stepId={active.id} dispatch={dispatch} />
          )}
          <LessonProgress session={state} lesson={lesson} />
          <div className="learning-continuation">
            <p className="muted small">
              {checkable
                ? 'Marking a step done records your own progress. It is separate from what Forge verifies.'
                : 'Forge isn’t checking the model in this sample lesson. Marking a step done records your own progress.'}
            </p>
            {interaction.completed && (
              <p role="status">Step marked done by you.</p>
            )}
            <Button
              tabIndex={0}
              variant="primary"
              onClick={() =>
                dispatch({
                  type: interaction.completed ? 'advance' : 'mark-done',
                  stepId: active.id,
                })
              }
            >
              {interaction.completed
                ? state.stepIndex === lesson.steps.length - 1
                  ? 'View completion summary'
                  : 'Next step'
                : 'Mark step done'}
            </Button>
            {!checkable && (
              <p className="muted small">
                Model checking becomes available in supported guided projects.
              </p>
            )}
          </div>
        </>
      )}
      {state.phase === 'completed' && (
        <>
          <p>{lesson.completionMessage}</p>
          <LessonProgress session={state} lesson={lesson} summary />
          <p className="muted">
            {checkable
              ? 'This summary reflects your lesson interactions, the steps you marked done and the steps Forge verified when you asked. Forge could not check dimensions, units, mass, fit or strength, and a verified step is not a guarantee that your design is correct.'
              : 'This summary reflects your lesson interactions and steps you marked done. Forge did not inspect or check your CAD model.'}
          </p>
          {lesson.followUpChallenge && (
            <section className="learning-section">
              <h2>{lesson.followUpChallenge.title}</h2>
              <p>{lesson.followUpChallenge.prompt}</p>
            </section>
          )}
          <p className="muted small">
            Your progress stays here until you reset or this panel session ends.
          </p>
        </>
      )}
      <Dialog
        open={resetOpen}
        onOpenChange={setResetOpen}
        title="Reset this lesson?"
        description="This clears your experience choice, goal, steps, hints and vocabulary history from this panel session."
      >
        <div className="action-bar">
          <Button tabIndex={0} onClick={() => setResetOpen(false)}>
            Keep learning
          </Button>
          <Button
            tabIndex={0}
            variant="danger"
            onClick={() => {
              dispatch({ type: 'reset' });
              setResetOpen(false);
            }}
          >
            Reset lesson progress
          </Button>
        </div>
      </Dialog>
    </div>
  );
}
