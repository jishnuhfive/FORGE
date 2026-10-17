import { useState } from 'react';
import type { ReactNode } from 'react';
import type { Lesson } from './lesson';
import { initialSession, reduceSession } from './session';
import type { LearningAction } from './session';
import { LearningContext } from './context';

export function LearningProvider({
  lesson,
  owner = 'local',
  children,
}: {
  lesson: Lesson;
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
