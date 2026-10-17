import { isExperience, isLearningGoal } from './lesson';
import type { Experience, LearningGoal, Lesson } from './lesson';

export type HintLevel = 0 | 1 | 2 | 3;
export interface StepInteraction {
  stepId: string;
  hintLevel: HintLevel;
  vocabularyOpened: string[];
  whyOpen: boolean;
  vocabularyVisible: string[];
  completed: boolean;
  // Set only by a backend deterministic check that returned `verified`.
  forgeVerified?: true;
}
interface Profile {
  experience: Experience;
  goal: LearningGoal;
}
export type LearningSession =
  | { phase: 'setup'; experience: Experience | null; goal: LearningGoal | null }
  | { phase: 'introduction'; profile: Profile }
  | {
      phase: 'active' | 'completed';
      profile: Profile;
      stepIndex: number;
      interactions: StepInteraction[];
    };
export type LearningAction =
  | { type: 'experience'; value: Experience }
  | { type: 'goal'; value: LearningGoal }
  | { type: 'review' | 'start' | 'reset' | 'edit-setup' }
  | { type: 'hint'; stepId: string; level: Exclude<HintLevel, 0> }
  | { type: 'why' | 'mark-done' | 'advance' | 'check-verified'; stepId: string }
  | { type: 'vocabulary'; stepId: string; termId: string };
export const initialSession = (): LearningSession => ({
  phase: 'setup',
  experience: null,
  goal: null,
});
export function reduceSession(
  lesson: Lesson,
  state: LearningSession,
  action: LearningAction,
): LearningSession {
  if (action.type === 'reset') return initialSession();
  if (state.phase === 'setup') {
    if (action.type === 'experience' && isExperience(action.value))
      return { ...state, experience: action.value };
    if (action.type === 'goal' && isLearningGoal(action.value))
      return { ...state, goal: action.value };
    if (action.type === 'review' && state.experience && state.goal)
      return {
        phase: 'introduction',
        profile: { experience: state.experience, goal: state.goal },
      };
    return state;
  }
  if (state.phase === 'introduction') {
    if (action.type === 'edit-setup')
      return { phase: 'setup', ...state.profile };
    if (action.type !== 'start') return state;
    return {
      phase: 'active',
      profile: state.profile,
      stepIndex: 0,
      interactions: lesson.steps.map((step) => ({
        stepId: step.id,
        hintLevel: 0,
        vocabularyOpened: [],
        vocabularyVisible: [],
        whyOpen: false,
        completed: false,
      })),
    };
  }
  if (state.phase !== 'active' || !('stepId' in action)) return state;
  const step = lesson.steps[state.stepIndex];
  const current = state.interactions[state.stepIndex];
  // Stable step IDs reject late/double events after progression.
  if (!step || !current || action.stepId !== step.id) return state;
  if (action.type === 'advance') {
    if (!current.completed) return state;
    if (state.stepIndex < lesson.steps.length - 1)
      return { ...state, stepIndex: state.stepIndex + 1 };
    return state.interactions.length === lesson.steps.length &&
      state.interactions.every((item) => item.completed)
      ? { ...state, phase: 'completed' }
      : state;
  }
  let next = current;
  if (
    action.type === 'check-verified' &&
    step.check === 'deterministic' &&
    !current.forgeVerified
  )
    next = { ...current, forgeVerified: true };
  if (
    action.type === 'hint' &&
    [1, 2, 3].includes(action.level) &&
    !current.completed &&
    action.level === current.hintLevel + 1
  )
    next = { ...current, hintLevel: action.level };
  if (action.type === 'mark-done' && !current.completed)
    next = { ...current, completed: true };
  if (action.type === 'why') next = { ...current, whyOpen: !current.whyOpen };
  if (
    action.type === 'vocabulary' &&
    step.vocabulary?.some((term) => term.id === action.termId)
  ) {
    const visible = current.vocabularyVisible.includes(action.termId);
    next = {
      ...current,
      vocabularyVisible: visible
        ? current.vocabularyVisible.filter((id) => id !== action.termId)
        : [...current.vocabularyVisible, action.termId],
      vocabularyOpened: current.vocabularyOpened.includes(action.termId)
        ? current.vocabularyOpened
        : [...current.vocabularyOpened, action.termId],
    };
  }
  return next === current
    ? state
    : {
        ...state,
        interactions: state.interactions.map((item, index) =>
          index === state.stepIndex ? next : item,
        ),
      };
}
export function sessionProgress(state: LearningSession, lesson: Lesson) {
  const interactions = 'interactions' in state ? state.interactions : [];
  return {
    total: lesson.steps.length,
    completed: interactions.filter((item) => item.completed).length,
    hints: interactions.reduce((count, item) => count + item.hintLevel, 0),
    vocabulary: new Set(interactions.flatMap((item) => item.vocabularyOpened))
      .size,
    forgeVerified: interactions.filter((item) => item.forgeVerified).length,
    checkable: lesson.steps.filter((step) => step.check).length,
    withoutHints: interactions.filter(
      (item) => item.completed && item.hintLevel === 0,
    ).length,
  };
}
