import type { Dispatch } from 'react';
import { CheckStep } from './CheckStep';
import { HintLadder, LessonDisclosure, Vocabulary } from './Guidance';
import type { LessonStep } from './lesson';
import { ExpectationPrompt, InvestigationPanel } from './Reflection';
import type { LearningAction, StepInteraction } from './session';

// The shared body of one lesson step, used by the guided lesson and the
// transfer challenge alike. There is exactly one hint ladder and one checker.
export function StepBody({
  step,
  interaction,
  dispatch,
}: {
  step: LessonStep;
  interaction: StepInteraction;
  dispatch: Dispatch<LearningAction>;
}) {
  return (
    <>
      <p className="learning-objective">
        <span className="muted">Objective</span>
        {step.objective}
      </p>
      <section className="learning-section">
        <h2>What to do</h2>
        <p>{step.instruction}</p>
      </section>
      <LessonDisclosure
        title="Why this step"
        open={interaction.whyOpen}
        onToggle={() => dispatch({ type: 'why', stepId: step.id })}
      >
        <p>{step.why}</p>
      </LessonDisclosure>
      {step.vocabulary && (
        <Vocabulary
          terms={step.vocabulary}
          interaction={interaction}
          dispatch={dispatch}
        />
      )}
      <ExpectationPrompt
        step={step}
        interaction={interaction}
        dispatch={dispatch}
      />
      <HintLadder step={step} interaction={interaction} dispatch={dispatch} />
      {step.check && (
        <CheckStep key={step.id} stepId={step.id} dispatch={dispatch} />
      )}
      <InvestigationPanel
        step={step}
        interaction={interaction}
        dispatch={dispatch}
      />
    </>
  );
}
