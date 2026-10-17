import { createContext, useContext } from 'react';
import type { Dispatch } from 'react';
import type { Lesson } from './lesson';
import type { LearningAction, LearningSession } from './session';
export const LearningContext = createContext<{
  lesson: Lesson;
  session: LearningSession;
  dispatch: Dispatch<LearningAction>;
} | null>(null);
export const useLearning = () => useContext(LearningContext);
