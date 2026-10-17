import { Button } from '@forge/design-system';
import type { Dispatch } from 'react';
import type { Experience, LearningGoal } from './lesson';
import type { LearningAction } from './session';

import { experienceOptions, goalOptions } from './options';
export function LearnerSetup({
  experience,
  goal,
  dispatch,
}: {
  experience: Experience | null;
  goal: LearningGoal | null;
  dispatch: Dispatch<LearningAction>;
}) {
  return (
    <>
      <p className="muted">
        Build understanding one step at a time. Start with what feels familiar.
      </p>
      <fieldset className="learning-choices">
        <legend>Your CAD experience</legend>
        {experienceOptions.map((option, index) => (
          <label key={option.id} className="learning-choice">
            <input
              type="radio"
              name="experience"
              value={option.id}
              tabIndex={
                experience === option.id || (!experience && index === 0)
                  ? 0
                  : -1
              }
              checked={experience === option.id}
              onChange={() =>
                dispatch({ type: 'experience', value: option.id })
              }
            />
            <span>
              <strong>{option.title}</strong>
              <span>{option.description}</span>
            </span>
          </label>
        ))}
      </fieldset>
      {experience && (
        <fieldset className="learning-choices learning-reveal">
          <legend>What would you like to work toward?</legend>
          {goalOptions.map((option, index) => (
            <label key={option.id} className="learning-choice">
              <input
                type="radio"
                name="learning-goal"
                value={option.id}
                tabIndex={goal === option.id || (!goal && index === 0) ? 0 : -1}
                checked={goal === option.id}
                onChange={() => dispatch({ type: 'goal', value: option.id })}
              />
              <span>{option.title}</span>
            </label>
          ))}
        </fieldset>
      )}
      <div className="learning-continuation">
        <Button
          tabIndex={0}
          variant="primary"
          disabled={!experience || !goal}
          onClick={() => dispatch({ type: 'review' })}
        >
          Review sample lesson
        </Button>
        <p className="muted small">
          Your choices and progress stay in this running panel. Closing or
          reloading it clears them.
        </p>
      </div>
    </>
  );
}
