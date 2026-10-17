import type { Lesson } from './lesson';
import type { LearningSession } from './session';
import { sessionProgress } from './session';

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
