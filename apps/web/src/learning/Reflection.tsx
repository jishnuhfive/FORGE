import { useId } from 'react';
import type { Dispatch } from 'react';
import { Button } from '@forge/design-system';
import { notSure } from './lesson';
import type { Investigation, LessonStep, PredictionPrompt } from './lesson';
import { activeInvestigation } from './session';
import type {
  Guidance,
  InvestigationState,
  LearningAction,
  StepInteraction,
} from './session';

const notSureLabel = 'I’m not sure yet';
const notSureResponse =
  'That’s fine. Compare what Forge observed with what you can see in your model.';

// Neutral reflection: never graded, never colored as right or wrong.
function Choices({
  name,
  prompt,
  selected,
  onSelect,
}: {
  name: string;
  prompt: PredictionPrompt;
  selected: string | undefined;
  onSelect: (choice: string) => void;
}) {
  const feedback = useId();
  const options = [
    ...prompt.choices.map((c) => ({ id: c.id, label: c.label })),
    { id: notSure, label: notSureLabel },
  ];
  const response =
    selected === undefined
      ? null
      : selected === notSure
        ? notSureResponse
        : (prompt.choices.find((c) => c.id === selected)?.response ?? null);
  return (
    <>
      <fieldset className="learning-choices" aria-describedby={feedback}>
        <legend>{prompt.question}</legend>
        {options.map((option, index) => (
          <label key={option.id} className="learning-choice">
            <input
              type="radio"
              name={name}
              value={option.id}
              tabIndex={
                selected === option.id ||
                (selected === undefined && index === 0)
                  ? 0
                  : -1
              }
              checked={selected === option.id}
              onChange={() => onSelect(option.id)}
            />
            <span>{option.label}</span>
          </label>
        ))}
      </fieldset>
      <p id={feedback} className="muted small" aria-live="polite">
        {response}
      </p>
    </>
  );
}

export function ExpectationPrompt({
  step,
  interaction,
  dispatch,
}: {
  step: LessonStep;
  interaction: StepInteraction;
  dispatch: Dispatch<LearningAction>;
}) {
  if (!step.expectation || interaction.completed) return null;
  return (
    <section className="learning-section" aria-label="Before you try it">
      <h2>Before you try it</h2>
      <Choices
        name={`expectation-${step.id}`}
        prompt={step.expectation}
        selected={interaction.expectation}
        onSelect={(choice) =>
          dispatch({ type: 'expectation', stepId: step.id, choice })
        }
      />
    </section>
  );
}

const guidanceNote: Record<Guidance, string | null> = {
  full: null,
  reduced:
    'Reduced guidance: you resolved a similar kind of issue earlier in this session, so the walkthrough is shorter. Everything is still one click away.',
  independent:
    'Independent challenge: Forge shows what it observed and asks first. Explanations are available when you ask.',
};

export function InvestigationPanel({
  step,
  interaction,
  dispatch,
}: {
  step: LessonStep;
  interaction: StepInteraction;
  dispatch: Dispatch<LearningAction>;
}) {
  const active = activeInvestigation(step, interaction);
  if (!active) return null;
  return (
    <Investigating
      stepId={step.id}
      authored={active.authored}
      state={active.state}
      dispatch={dispatch}
    />
  );
}

function Investigating({
  stepId,
  authored,
  state,
  dispatch,
}: {
  stepId: string;
  authored: Investigation;
  state: InvestigationState;
  dispatch: Dispatch<LearningAction>;
}) {
  const reveal = (part: 'hypothesis' | 'recommendation') =>
    dispatch({
      type: 'investigation-reveal',
      stepId,
      investigationId: authored.id,
      part,
    });
  const open = state.status === 'open';
  const full = state.guidance === 'full';
  const answered = state.prediction !== undefined;
  const note = guidanceNote[state.guidance];
  return (
    <section className="learning-investigation" aria-label="Investigate">
      <h2>Investigate</h2>
      {note && <p className="muted small">{note}</p>}
      <h3>What Forge observed</h3>
      <p>{state.observed}</p>
      {open && (
        <>
          <Choices
            name={`prediction-${authored.id}`}
            prompt={authored.prediction}
            selected={state.prediction}
            onSelect={(choice) =>
              dispatch({
                type: 'investigation-predict',
                stepId,
                investigationId: authored.id,
                choice,
              })
            }
          />
          {state.hypothesis && (
            <div className="learning-reveal">
              <h3>Possible explanation</h3>
              <p>{authored.possibleExplanation}</p>
              <p className="muted small">
                This is a possibility, not something Forge has verified.
              </p>
            </div>
          )}
          {state.recommendation && (
            <div className="learning-reveal">
              <h3>Try next</h3>
              <p>{full ? authored.tryNext : authored.shortTryNext}</p>
              <p className="muted small">
                This is a suggestion, not a guarantee. Need more help? The hints
                above open one level at a time.
              </p>
            </div>
          )}
          <div className="learning-continuation">
            {answered && !state.hypothesis && (
              <Button
                tabIndex={0}
                variant="ghost"
                className="glass-action"
                onClick={() => reveal('hypothesis')}
              >
                Show a possible explanation
              </Button>
            )}
            {answered &&
              !state.recommendation &&
              (state.hypothesis || !full) && (
                <Button
                  tabIndex={0}
                  variant="ghost"
                  className="glass-action"
                  onClick={() => reveal('recommendation')}
                >
                  Show what to try next
                </Button>
              )}
            <p className="muted small">
              After you change your model, press Check my step again. Forge
              doesn’t re-check on its own.
            </p>
          </div>
        </>
      )}
      {state.rechecked && (
        <div className="learning-verified" role="status">
          <h3>Verified after re-check</h3>
          <p>
            {open ? 'Not resolved yet. ' : 'Resolved. '}
            {state.latest}
          </p>
        </div>
      )}
    </section>
  );
}
