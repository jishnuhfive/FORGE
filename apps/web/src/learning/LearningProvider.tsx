import { useState } from 'react';
import type { ReactNode } from 'react';
import type { LearningGoal, Lesson } from './lesson';
import { initialSession, reduceSession } from './session';
import type { LearningAction } from './session';
import { LearningContext } from './context';

export function LearningProvider({
  lesson: defaultLesson,
  lessonFor,
  owner = 'local',
  children,
}: {
  lesson: Lesson;
  // Optional: a different lesson for the learner's chosen goal.
  lessonFor?: (goal: LearningGoal) => Lesson | null;
  owner?: string;
  children: ReactNode;
}) {
  const [binding, setBinding] = useState(() => ({
    owner,
    session: initialSession(),
  }));
  // Reset only learning when the authenticated owner changes. A keyed workspace
  // would also erase account-operation feedback and unrelated local UI state.
  if (binding.owner !== owner) setBinding({ owner, session: initialSession() });
  const goal =
    binding.session.phase === 'setup'
      ? binding.session.goal
      : binding.session.profile.goal;
  const lesson = (goal && lessonFor?.(goal)) || defaultLesson;
  const dispatch = (action: LearningAction) =>
    setBinding((current) =>
      current.owner === owner
        ? { owner, session: reduceSession(lesson, current.session, action) }
        : current,
    );
  return (
    <LearningContext.Provider
      value={{ lesson, session: binding.session, dispatch }}
    >
      {children}
    </LearningContext.Provider>
  );
}
