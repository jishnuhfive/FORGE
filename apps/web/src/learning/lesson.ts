// Serializable authored content. Checking metadata describes future requirements only.
export const experiences = [
  'beginner',
  'some-experience',
  'comfortable',
] as const;
export type Experience = (typeof experiences)[number];
export const goals = [
  'fundamentals',
  'guided-project',
  'design-reasoning',
] as const;
export type LearningGoal = (typeof goals)[number];
export interface VocabularyTerm {
  id: string;
  term: string;
  definition: string;
}
export type LessonRequirement =
  | {
      kind: 'feature-exists' | 'feature-active';
      featureType: 'sketch' | 'extrude';
    }
  | { kind: 'solid-body-exists' }
  | { kind: 'operation-present'; operation: 'extrude' };
export interface PredictionChoice {
  id: string;
  label: string;
  // Neutral, non-grading feedback shown after the student chooses.
  response: string;
}
export interface PredictionPrompt {
  question: string;
  // "I'm not sure yet" (id `not-sure`) is always offered by the UI; do not author it.
  choices: PredictionChoice[];
}
export const notSure = 'not-sure';
export const investigationFamilies = [
  'missing-feature',
  'ambiguous-evidence',
  'constraint',
] as const;
export type InvestigationFamily = (typeof investigationFamilies)[number];
export interface Investigation {
  id: string;
  // Used only for the explainable guidance-fading rule.
  family: InvestigationFamily;
  // Matches a BLOCKING requirement result from the server. The Observed line is
  // that result's own finding, never authored here.
  trigger: {
    requirementId: string;
    statuses: ('FAIL' | 'WARNING')[];
    reasons?: string[];
  };
  prediction: PredictionPrompt;
  // A possibility, never a fact. Written from evidence limits.
  possibleExplanation: string;
  tryNext: string;
  shortTryNext: string;
}
export interface TransferChallenge {
  id: string;
  title: string;
  summary: string;
  constraints: string[];
  steps: LessonStep[];
  completionMessage: string;
}
export interface LessonStep {
  id: string;
  title: string;
  objective: string;
  instruction: string;
  why: string;
  vocabulary?: VocabularyTerm[];
  hints: { conceptual: string; tool: string; explanation: string };
  completion: 'learner-reported';
  // Server-owned deterministic requirements exist for this step id. Metadata only;
  // it grants no evidence and the backend decides every status.
  check?: 'deterministic';
  // Authored reflection before trying a change. Never graded and never a check.
  expectation?: PredictionPrompt;
  // Authored mistake investigations, opened only by a blocking deterministic result.
  investigations?: Investigation[];
  future?: {
    requirements?: LessonRequirement[];
    mistakeInvestigation?: { prompt: string };
    reducedGuidance?: { prompt: string };
  };
}
export interface Lesson {
  id: string;
  title: string;
  summary: string;
  learningObjectives: string[];
  experienceRange: Experience[];
  prerequisites: string[];
  steps: LessonStep[];
  completionMessage?: string;
  followUpChallenge?: { title: string; prompt: string };
  // A separate, more independent follow-up with its own progress.
  transfer?: TransferChallenge;
}

// Closed, bounded runtime validation; no cast-only trust boundary or rule evaluator.
function record(value: unknown, required: string[], optional: string[] = []) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return false;
  const keys = Object.keys(value);
  return (
    required.every((key) => Object.hasOwn(value, key)) &&
    keys.every((key) => [...required, ...optional].includes(key))
  );
}
function text(value: unknown): value is string {
  return (
    typeof value === 'string' && value.trim().length > 0 && value.length <= 2400
  );
}
function id(value: unknown): value is string {
  return typeof value === 'string' && /^[a-z][a-z0-9-]{0,63}$/.test(value);
}
function list<T>(
  value: unknown,
  check: (item: unknown) => item is T,
  min = 0,
  max = 20,
): value is T[] {
  return (
    Array.isArray(value) &&
    value.length >= min &&
    value.length <= max &&
    value.every(check)
  );
}
function uniqueIds(items: { id: string }[]) {
  return new Set(items.map((item) => item.id)).size === items.length;
}
export function isExperience(value: unknown): value is Experience {
  return experiences.some((item) => item === value);
}
export function isLearningGoal(value: unknown): value is LearningGoal {
  return goals.some((item) => item === value);
}
function isVocabulary(value: unknown): value is VocabularyTerm {
  if (!record(value, ['id', 'term', 'definition'])) return false;
  const v = value as VocabularyTerm;
  return id(v.id) && text(v.term) && text(v.definition);
}
function isRequirement(value: unknown): value is LessonRequirement {
  if (!value || typeof value !== 'object') return false;
  const v = value as LessonRequirement;
  switch (v.kind) {
    case 'feature-exists':
    case 'feature-active':
      return (
        record(v, ['kind', 'featureType']) &&
        ['sketch', 'extrude'].includes(v.featureType)
      );
    case 'solid-body-exists':
      return record(v, ['kind']);
    case 'operation-present':
      return record(v, ['kind', 'operation']) && v.operation === 'extrude';
    default:
      return false;
  }
}
function isChoice(value: unknown): value is PredictionChoice {
  if (!record(value, ['id', 'label', 'response'])) return false;
  const v = value as PredictionChoice;
  return id(v.id) && v.id !== notSure && text(v.label) && text(v.response);
}
function isPredictionPrompt(value: unknown): value is PredictionPrompt {
  if (!record(value, ['question', 'choices'])) return false;
  const v = value as PredictionPrompt;
  return (
    text(v.question) && list(v.choices, isChoice, 2, 5) && uniqueIds(v.choices)
  );
}
const requirementId = /^[a-z][a-z0-9._-]{0,63}$/;
function isInvestigation(value: unknown): value is Investigation {
  if (
    !record(value, [
      'id',
      'family',
      'trigger',
      'prediction',
      'possibleExplanation',
      'tryNext',
      'shortTryNext',
    ])
  )
    return false;
  const v = value as Investigation;
  const t = v.trigger;
  return (
    id(v.id) &&
    (investigationFamilies as readonly unknown[]).includes(v.family) &&
    record(t, ['requirementId', 'statuses'], ['reasons']) &&
    typeof t.requirementId === 'string' &&
    requirementId.test(t.requirementId) &&
    Array.isArray(t.statuses) &&
    t.statuses.length >= 1 &&
    t.statuses.length <= 2 &&
    t.statuses.every((s) => s === 'FAIL' || s === 'WARNING') &&
    (!Object.hasOwn(t, 'reasons') ||
      (Array.isArray(t.reasons) &&
        t.reasons.length <= 6 &&
        t.reasons.every(
          (r) => typeof r === 'string' && id(r.replaceAll('_', '-')),
        ))) &&
    isPredictionPrompt(v.prediction) &&
    text(v.possibleExplanation) &&
    text(v.tryNext) &&
    text(v.shortTryNext)
  );
}
function isPrompt(value: unknown) {
  return (
    record(value, ['prompt']) && text((value as { prompt: unknown }).prompt)
  );
}
function isStep(value: unknown): value is LessonStep {
  if (
    !record(
      value,
      ['id', 'title', 'objective', 'instruction', 'why', 'hints', 'completion'],
      ['vocabulary', 'future', 'check', 'expectation', 'investigations'],
    )
  )
    return false;
  const v = value as LessonStep;
  if (
    !id(v.id) ||
    ![v.title, v.objective, v.instruction, v.why].every(text) ||
    v.completion !== 'learner-reported' ||
    (Object.hasOwn(v, 'check') && v.check !== 'deterministic') ||
    !record(v.hints, ['conceptual', 'tool', 'explanation']) ||
    !Object.values(v.hints).every(text)
  )
    return false;
  if (
    Object.hasOwn(v, 'vocabulary') &&
    (!list(v.vocabulary, isVocabulary) || !uniqueIds(v.vocabulary))
  )
    return false;
  if (Object.hasOwn(v, 'expectation') && !isPredictionPrompt(v.expectation))
    return false;
  if (Object.hasOwn(v, 'investigations')) {
    if (
      !list(v.investigations, isInvestigation, 0, 6) ||
      !uniqueIds(v.investigations)
    )
      return false;
    // Investigations only make sense where a deterministic check exists.
    if (v.investigations.length > 0 && v.check !== 'deterministic')
      return false;
  }
  if (Object.hasOwn(v, 'future')) {
    if (
      !record(
        v.future,
        [],
        ['requirements', 'mistakeInvestigation', 'reducedGuidance'],
      )
    )
      return false;
    const f = v.future!;
    if (
      Object.hasOwn(f, 'requirements') &&
      !list(f.requirements, isRequirement)
    )
      return false;
    if (
      Object.hasOwn(f, 'mistakeInvestigation') &&
      !isPrompt(f.mistakeInvestigation)
    )
      return false;
    if (Object.hasOwn(f, 'reducedGuidance') && !isPrompt(f.reducedGuidance))
      return false;
  }
  return true;
}
function isTransfer(
  value: unknown,
  guided: LessonStep[],
): value is TransferChallenge {
  if (
    !record(value, [
      'id',
      'title',
      'summary',
      'constraints',
      'steps',
      'completionMessage',
    ])
  )
    return false;
  const v = value as TransferChallenge;
  return (
    id(v.id) &&
    text(v.title) &&
    text(v.summary) &&
    text(v.completionMessage) &&
    list(v.constraints, text, 1, 6) &&
    list(v.steps, isStep, 1, 3) &&
    uniqueIds(v.steps) &&
    // Stable step ids must never collide across the guided lesson and challenge.
    v.steps.every((step) => !guided.some((g) => g.id === step.id))
  );
}
export function isLesson(value: unknown): value is Lesson {
  if (
    !record(
      value,
      [
        'id',
        'title',
        'summary',
        'learningObjectives',
        'experienceRange',
        'prerequisites',
        'steps',
      ],
      ['completionMessage', 'followUpChallenge', 'transfer'],
    )
  )
    return false;
  const v = value as Lesson;
  return (
    id(v.id) &&
    text(v.title) &&
    text(v.summary) &&
    list(v.learningObjectives, text, 1) &&
    list(v.experienceRange, isExperience, 1, 3) &&
    new Set(v.experienceRange).size === v.experienceRange.length &&
    list(v.prerequisites, text) &&
    list(v.steps, isStep, 1) &&
    uniqueIds(v.steps) &&
    (!Object.hasOwn(v, 'completionMessage') || text(v.completionMessage)) &&
    (!Object.hasOwn(v, 'transfer') || isTransfer(v.transfer, v.steps)) &&
    (!Object.hasOwn(v, 'followUpChallenge') ||
      (record(v.followUpChallenge, ['title', 'prompt']) &&
        text(v.followUpChallenge?.title) &&
        text(v.followUpChallenge?.prompt)))
  );
}
