import type { Lesson } from './lesson';
import type { LearningSession } from './session';
import {
  challengeProgress,
  reflectionProgress,
  sessionProgress,
} from './session';

export function LessonProgress({
  session,
  lesson,
  summary = false,
}: {
  session: LearningSession;
  lesson: Lesson;
  summary?: boolean;
}) {
  const progress = sessionProgress(session, lesson);
  const reflection = reflectionProgress(session);
  const reflective = lesson.steps.some(
    (step) => step.expectation || step.investigations?.length,
  );
  return (
    <section className="learning-progress" aria-label="Session progress">
      <p>
        Steps completed: {progress.completed} of {progress.total}
      </p>
      <progress
        aria-label="Steps marked done by you"
        max={progress.total}
        value={progress.completed}
      />
      <dl className="learning-metrics">
        <div>
          <dt>Hints requested</dt>
          <dd>{progress.hints}</dd>
        </div>
        <div>
          <dt>Vocabulary terms opened</dt>
          <dd>{progress.vocabulary}</dd>
        </div>
        {reflective && (
          <>
            <div>
              <dt>Prediction questions answered</dt>
              <dd>{reflection.predictions}</dd>
            </div>
            <div>
              <dt>Investigations resolved after re-check</dt>
              <dd>
                {reflection.investigationsResolved} of{' '}
                {reflection.investigationsOpened}
              </dd>
            </div>
          </>
        )}
        {progress.checkable > 0 && (
          <div>
            <dt>Steps Forge verified</dt>
            <dd>
              {progress.forgeVerified} of {progress.checkable}
            </dd>
          </div>
        )}
        {summary && (
          <div>
            <dt>Steps completed without hints</dt>
            <dd>{progress.withoutHints}</dd>
          </div>
        )}
      </dl>
    </section>
  );
}

// Transparent session facts about the transfer challenge. No score, grade or
// mastery claim of any kind; only what the learner did and Forge verified.
export function ChallengeProgress({
  session,
  lesson,
}: {
  session: LearningSession;
  lesson: Lesson;
}) {
  const progress = challengeProgress(session, lesson);
  if (!progress) return null;
  return (
    <section className="learning-progress" aria-label="Challenge progress">
      <dl className="learning-metrics">
        <div>
          <dt>Challenge steps Forge verified</dt>
          <dd>
            {progress.forgeVerified} of {progress.checkable}
          </dd>
        </div>
        <div>
          <dt>Challenge hints requested</dt>
          <dd>{progress.hints}</dd>
        </div>
        {progress.finished && (
          <>
            <div>
              <dt>Completed without hints</dt>
              <dd>{progress.withoutHints ? 'Yes' : 'No'}</dd>
            </div>
            <div>
              <dt>Full explanation used</dt>
              <dd>{progress.fullExplanationUsed ? 'Yes' : 'No'}</dd>
            </div>
          </>
        )}
      </dl>
    </section>
  );
}
