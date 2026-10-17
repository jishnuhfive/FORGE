import { isExperience, isLearningGoal, notSure } from './lesson';
import type {
  Experience,
  Investigation,
  InvestigationFamily,
  LearningGoal,
  Lesson,
  LessonStep,
} from './lesson';

export type HintLevel = 0 | 1 | 2 | 3;
export type CheckOutcome = 'verified' | 'not_met' | 'unverified';
// full: early attempts. reduced: a similar issue was resolved earlier this
// session. independent: the transfer challenge. Honesty caveats never fade.
export type Guidance = 'full' | 'reduced' | 'independent';
// The compact, server-authored slice of one requirement result that the
// session needs. Findings are the server's own words, never AI output.
export interface CheckFinding {
  requirementId: string;
  blocking: boolean;
  status: 'PASS' | 'FAIL' | 'WARNING' | 'UNVERIFIED';
  reason: string;
  finding: string;
}
export interface InvestigationState {
  // Follows the latest deterministic result for the trigger requirement.
  status: 'open' | 'resolved';
  guidance: Guidance;
  // Server finding when the investigation opened / at the latest check.
  observed: string;
  latest: string;
  // Session-local reflection. Never graded, never sent anywhere.
  prediction?: string;
  hypothesis?: true;
  recommendation?: true;
  // True once a check has happened after the investigation opened.
  rechecked?: true;
}
export interface StepInteraction {
  stepId: string;
  hintLevel: HintLevel;
  vocabularyOpened: string[];
  whyOpen: boolean;
  vocabularyVisible: string[];
  completed: boolean;
  // True only while the latest deterministic server check of this step was
  // `verified`; any later non-verified result removes it.
  forgeVerified?: true;
  expectation?: string;
  investigations?: Record<string, InvestigationState>;
  // The server-signed proof of the latest check of this step, kept in memory so
  // Ask Forge can send it back. Opaque; never persisted.
  evidenceToken?: string;
}
interface Profile {
  experience: Experience;
  goal: LearningGoal;
}
export interface TransferState {
  phase: 'active' | 'completed';
  stepIndex: number;
  interactions: StepInteraction[];
}
export type LearningSession =
  | { phase: 'setup'; experience: Experience | null; goal: LearningGoal | null }
  | { phase: 'introduction'; profile: Profile }
  | {
      phase: 'active' | 'completed';
      profile: Profile;
      stepIndex: number;
      interactions: StepInteraction[];
      // Separate from guided progress; only present after the guided lesson.
      transfer?: TransferState;
    };
export type LearningAction =
  | { type: 'experience'; value: Experience }
  | { type: 'goal'; value: LearningGoal }
  | {
      type:
        | 'review'
        | 'start'
        | 'reset'
        | 'edit-setup'
        | 'transfer-start'
        | 'transfer-restart';
    }
  | { type: 'hint'; stepId: string; level: Exclude<HintLevel, 0> }
  | { type: 'why' | 'mark-done' | 'advance'; stepId: string }
  // The latest accepted deterministic server outcome for the active step.
  | {
      type: 'check-result';
      stepId: string;
      outcome: CheckOutcome;
      findings?: CheckFinding[];
      evidenceToken?: string;
    }
  | { type: 'vocabulary'; stepId: string; termId: string }
  | { type: 'expectation'; stepId: string; choice: string }
  | {
      type: 'investigation-predict';
      stepId: string;
      investigationId: string;
      choice: string;
    }
  | {
      type: 'investigation-reveal';
      stepId: string;
      investigationId: string;
      part: 'hypothesis' | 'recommendation';
    };
type StepAction = Extract<LearningAction, { stepId: string }>;
export const initialSession = (): LearningSession => ({
  phase: 'setup',
  experience: null,
  goal: null,
});
const freshInteractions = (steps: LessonStep[]): StepInteraction[] =>
  steps.map((step) => ({
    stepId: step.id,
    hintLevel: 0,
    vocabularyOpened: [],
    vocabularyVisible: [],
    whyOpen: false,
    completed: false,
  }));

function resolvedFamilies(
  steps: LessonStep[],
  interactions: StepInteraction[],
): Set<InvestigationFamily> {
  const families = new Set<InvestigationFamily>();
  for (const interaction of interactions) {
    const step = steps.find((item) => item.id === interaction.stepId);
    for (const [id, state] of Object.entries(
      interaction.investigations ?? {},
    )) {
      const authored = step?.investigations?.find((item) => item.id === id);
      if (authored && state.status === 'resolved')
        families.add(authored.family);
    }
  }
  return families;
}
const matches = (investigation: Investigation, finding: CheckFinding) =>
  finding.blocking &&
  finding.requirementId === investigation.trigger.requirementId &&
  (finding.status === 'FAIL' || finding.status === 'WARNING') &&
  investigation.trigger.statuses.includes(finding.status) &&
  (!investigation.trigger.reasons ||
    investigation.trigger.reasons.includes(finding.reason));

// Investigations follow the latest deterministic evidence, never a past claim.
function updateInvestigations(
  step: LessonStep,
  current: StepInteraction,
  findings: CheckFinding[],
  guidanceFor: (investigation: Investigation) => Guidance,
): Record<string, InvestigationState> | undefined {
  const authored = step.investigations;
  if (!authored?.length) return undefined;
  const previous = current.investigations ?? {};
  const next: Record<string, InvestigationState> = { ...previous };
  let changed = false;
  for (const investigation of authored) {
    const state = previous[investigation.id];
    const finding = findings.find(
      (item) => item.requirementId === investigation.trigger.requirementId,
    );
    if (!state || !finding) continue;
    // Only a PASS supports "resolved". Failures, warnings and an inability to
    // verify all revoke it, exactly like the verified count.
    const status = finding.status === 'PASS' ? 'resolved' : 'open';
    if (
      state.status !== status ||
      state.latest !== finding.finding ||
      !state.rechecked
    ) {
      next[investigation.id] = {
        ...state,
        status,
        latest: finding.finding,
        rechecked: true,
      };
      changed = true;
    }
  }
  // At most one open investigation per step, so help never piles up.
  if (!Object.values(next).some((state) => state.status === 'open'))
    for (const investigation of authored) {
      if (next[investigation.id]) continue;
      const finding = findings.find((item) => matches(investigation, item));
      if (!finding) continue;
      next[investigation.id] = {
        status: 'open',
        guidance: guidanceFor(investigation),
        observed: finding.finding,
        latest: finding.finding,
      };
      changed = true;
      break;
    }
  return changed ? next : undefined;
}

interface Context {
  steps: LessonStep[];
  interactions: StepInteraction[];
  independent: boolean;
}
function reduceInteraction(
  step: LessonStep,
  current: StepInteraction,
  action: StepAction,
  context: Context,
): StepInteraction {
  let next = current;
  if (action.type === 'check-result' && step.check === 'deterministic') {
    if (action.evidenceToken && action.evidenceToken !== current.evidenceToken)
      next = { ...next, evidenceToken: action.evidenceToken };
    // Verified reflects the latest result only: anything else revokes it.
    if (action.outcome === 'verified' && !current.forgeVerified)
      next = { ...next, forgeVerified: true };
    else if (action.outcome !== 'verified' && current.forgeVerified) {
      next = { ...next };
      delete next.forgeVerified;
    }
    if (action.findings) {
      const families = resolvedFamilies(context.steps, context.interactions);
      const investigations = updateInvestigations(
        step,
        next,
        action.findings,
        (investigation) =>
          context.independent
            ? 'independent'
            : families.has(investigation.family)
              ? 'reduced'
              : 'full',
      );
      if (investigations) next = { ...next, investigations };
    }
  }
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
  if (
    action.type === 'expectation' &&
    step.expectation &&
    current.expectation !== action.choice &&
    (action.choice === notSure ||
      step.expectation.choices.some((choice) => choice.id === action.choice))
  )
    next = { ...current, expectation: action.choice };
  if (
    action.type === 'investigation-predict' ||
    action.type === 'investigation-reveal'
  ) {
    const authored = step.investigations?.find(
      (item) => item.id === action.investigationId,
    );
    const state = current.investigations?.[action.investigationId];
    let updated: InvestigationState | undefined;
    if (authored && state && action.type === 'investigation-predict') {
      if (
        state.prediction !== action.choice &&
        (action.choice === notSure ||
          authored.prediction.choices.some(
            (choice) => choice.id === action.choice,
          ))
      )
        updated = { ...state, prediction: action.choice };
    } else if (authored && state && action.type === 'investigation-reveal') {
      // Think first: nothing is revealed before the student has answered
      // (an "I'm not sure yet" answer counts). Never blocks forever.
      if (state.prediction !== undefined) {
        if (action.part === 'hypothesis' && !state.hypothesis)
          updated = { ...state, hypothesis: true };
        // Full guidance walks explanation -> next step; reduced/independent
        // guidance may go straight to the short next step.
        if (
          action.part === 'recommendation' &&
          !state.recommendation &&
          (state.hypothesis || state.guidance !== 'full')
        )
          updated = { ...state, recommendation: true };
      }
    }
    if (updated)
      next = {
        ...current,
        investigations: {
          ...current.investigations,
          [action.investigationId]: updated,
        },
      };
  }
  return next;
}

interface Applied {
  interactions: StepInteraction[];
  stepIndex: number;
  finished: boolean;
}
function applyStepAction(
  context: Context,
  stepIndex: number,
  action: StepAction,
): Applied | null {
  const { steps, interactions } = context;
  const step = steps[stepIndex];
  const current = interactions[stepIndex];
  // Stable step IDs reject late/double events after progression.
  if (!step || !current || action.stepId !== step.id) return null;
  if (action.type === 'advance') {
    if (!current.completed) return null;
    if (stepIndex < steps.length - 1)
      return { interactions, stepIndex: stepIndex + 1, finished: false };
    return interactions.length === steps.length &&
      interactions.every((item) => item.completed)
      ? { interactions, stepIndex, finished: true }
      : null;
  }
  const next = reduceInteraction(step, current, action, context);
  return next === current
    ? null
    : {
        interactions: interactions.map((item, index) =>
          index === stepIndex ? next : item,
        ),
        stepIndex,
        finished: false,
      };
}

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
      interactions: freshInteractions(lesson.steps),
    };
  }
  if (state.phase === 'completed' && lesson.transfer) {
    // Transfer progress is separate: restarting it never touches the guided
    // lesson, and only a full reset clears both.
    if (
      (action.type === 'transfer-start' && !state.transfer) ||
      (action.type === 'transfer-restart' && state.transfer)
    )
      return {
        ...state,
        transfer: {
          phase: 'active',
          stepIndex: 0,
          interactions: freshInteractions(lesson.transfer.steps),
        },
      };
    if (state.transfer?.phase === 'active' && 'stepId' in action) {
      const applied = applyStepAction(
        {
          steps: lesson.transfer.steps,
          interactions: state.transfer.interactions,
          independent: true,
        },
        state.transfer.stepIndex,
        action,
      );
      return applied
        ? {
            ...state,
            transfer: {
              phase: applied.finished ? 'completed' : 'active',
              stepIndex: applied.stepIndex,
              interactions: applied.interactions,
            },
          }
        : state;
    }
    return state;
  }
  if (state.phase !== 'active' || !('stepId' in action)) return state;
  const applied = applyStepAction(
    {
      steps: lesson.steps,
      interactions: state.interactions,
      independent: false,
    },
    state.stepIndex,
    action,
  );
  if (!applied) return state;
  return {
    ...state,
    phase: applied.finished ? 'completed' : 'active',
    stepIndex: applied.stepIndex,
    interactions: applied.interactions,
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

// Transparent, session-local reflection signals. No score of any kind.
export function reflectionProgress(state: LearningSession) {
  const groups: StepInteraction[] =
    'interactions' in state
      ? [...state.interactions, ...(state.transfer?.interactions ?? [])]
      : [];
  const states = groups.flatMap((item) =>
    Object.values(item.investigations ?? {}),
  );
  return {
    // Reflection prompts the student answered (not graded, "not sure" counts).
    predictions:
      groups.filter((item) => item.expectation !== undefined).length +
      states.filter((item) => item.prediction !== undefined).length,
    investigationsOpened: states.length,
    // Currently resolved by a fresh deterministic re-check.
    investigationsResolved: states.filter((item) => item.status === 'resolved')
      .length,
  };
}
export function challengeProgress(state: LearningSession, lesson: Lesson) {
  const challenge = lesson.transfer;
  if (!challenge || state.phase !== 'completed' || !state.transfer) return null;
  const { interactions } = state.transfer;
  const checkable = challenge.steps.filter((step) => step.check).length;
  const hints = interactions.reduce((count, item) => count + item.hintLevel, 0);
  const verified = interactions.filter((item) => item.forgeVerified).length;
  const completed = interactions.filter((item) => item.completed).length;
  return {
    total: challenge.steps.length,
    completed,
    checkable,
    forgeVerified: verified,
    hints,
    // The strongest help level; reported, never penalized.
    fullExplanationUsed: interactions.some((item) => item.hintLevel === 3),
    finished: state.transfer.phase === 'completed',
    // Done by the learner, verified by Forge's latest check, and no hints.
    withoutHints:
      state.transfer.phase === 'completed' &&
      verified === checkable &&
      hints === 0,
  };
}
// The investigation to show for a step: an open one first, else a resolved one.
export function activeInvestigation(
  step: LessonStep,
  interaction: StepInteraction,
): { authored: Investigation; state: InvestigationState } | null {
  const entries = (step.investigations ?? []).flatMap((authored) => {
    const state = interaction.investigations?.[authored.id];
    return state ? [{ authored, state }] : [];
  });
  return (
    entries.find((entry) => entry.state.status === 'open') ??
    entries.at(-1) ??
    null
  );
}
