import { describe, expect, it } from 'vitest';
import { isLesson } from './lesson';
import { sketchToSolid as lesson } from './sample';
import { loadLesson } from './catalog';
import { initialSession, reduceSession, sessionProgress } from './session';
import type { LearningAction, LearningSession } from './session';

function transition(state: LearningSession, action: LearningAction) {
  return reduceSession(lesson, state, action);
}
function start() {
  let state = initialSession();
  for (const action of [
    { type: 'experience', value: 'beginner' },
    { type: 'goal', value: 'fundamentals' },
    { type: 'review' },
    { type: 'start' },
  ] satisfies LearningAction[])
    state = transition(state, action);
  return state;
}
function changed(mutator: (copy: Record<string, unknown>) => void) {
  const copy = JSON.parse(JSON.stringify(lesson)) as Record<string, unknown>;
  mutator(copy);
  return copy;
}
describe('authored lesson boundary', () => {
  it('validates the sample and its serializable round trip', () => {
    expect(isLesson(lesson)).toBe(true);
    expect(isLesson(JSON.parse(JSON.stringify(lesson)))).toBe(true);
  });
  for (const [name, value] of [
    ['null', null],
    ['array', []],
    ['empty', {}],
    ['extra field', { ...lesson, execute: 'write' }],
    ['invalid id', { ...lesson, id: '../cad' }],
    ['empty objective', { ...lesson, learningObjectives: [' '] }],
    ['empty steps', { ...lesson, steps: [] }],
    [
      'duplicate steps',
      { ...lesson, steps: [lesson.steps[0], lesson.steps[0]] },
    ],
    ['unsupported experience', { ...lesson, experienceRange: ['expert'] }],
    [
      'duplicate experience',
      { ...lesson, experienceRange: ['beginner', 'beginner'] },
    ],
    ['oversized string', { ...lesson, title: 'a'.repeat(2401) }],
    [
      'missing hint',
      changed((v) => {
        (v.steps as { hints: object }[])[0]!.hints = { conceptual: 'Think' };
      }),
    ],
    [
      'invalid completion',
      changed((v) => {
        (v.steps as { completion: string }[])[0]!.completion = 'verified';
      }),
    ],
    [
      'invalid vocabulary',
      changed((v) => {
        (v.steps as { vocabulary: unknown }[])[0]!.vocabulary = [
          { id: 'term', term: 'Test', definition: '' },
        ];
      }),
    ],
    [
      'duplicate vocabulary',
      changed((v) => {
        const s = (v.steps as { vocabulary: unknown[] }[])[0]!;
        s.vocabulary = [s.vocabulary[0], s.vocabulary[0]];
      }),
    ],
    ['React node', { ...lesson, summary: { type: 'p', props: {} } }],
    [
      'unknown checker',
      changed((v) => {
        (v.steps as { future: unknown }[])[0]!.future = {
          requirements: [{ kind: 'execute-code' }],
        };
      }),
    ],
    [
      'invalid future prompt',
      changed((v) => {
        (v.steps as { future: unknown }[])[0]!.future = {
          reducedGuidance: { prompt: '', html: '<p>' },
        };
      }),
    ],
    [
      'extra requirement field',
      changed((v) => {
        (v.steps as { future: unknown }[])[0]!.future = {
          requirements: [{ kind: 'solid-body-exists', pass: true }],
        };
      }),
    ],
  ])
    it(`rejects ${name}`, () => expect(isLesson(value)).toBe(false));
  it('accepts bounded future metadata without evaluating it', () => {
    const copy = changed((v) => {
      (v.steps as { future: unknown }[])[0]!.future = {
        requirements: [
          { kind: 'feature-exists', featureType: 'sketch' },
          { kind: 'feature-active', featureType: 'extrude' },
          { kind: 'solid-body-exists' },
          { kind: 'operation-present', operation: 'extrude' },
        ],
        mistakeInvestigation: { prompt: 'Revisit the profile.' },
        reducedGuidance: { prompt: 'Choose an operation.' },
      };
    });
    expect(isLesson(copy)).toBe(true);
  });
  it('distinguishes no selection, unavailable, load failure and invalid content', () => {
    expect(loadLesson(null).status).toBe('empty');
    expect(loadLesson('unknown').status).toBe('unavailable');
    expect(
      loadLesson(lesson.id, () => {
        throw new Error('private internals');
      }).status,
    ).toBe('load-error');
    expect(loadLesson(lesson.id, () => ({})).status).toBe('invalid');
    expect(loadLesson(lesson.id).status).toBe('ready');
  });
});
describe('learning session transitions', () => {
  it('initializes with no student profile or progress', () => {
    expect(initialSession()).toEqual({
      phase: 'setup',
      experience: null,
      goal: null,
    });
    expect(sessionProgress(initialSession(), lesson)).toEqual({
      total: 3,
      completed: 0,
      hints: 0,
      vocabulary: 0,
      withoutHints: 0,
      forgeVerified: 0,
      checkable: 0,
    });
  });
  it('requires both learner choices before introduction and explicit start', () => {
    let state = initialSession();
    expect(transition(state, { type: 'review' })).toBe(state);
    expect(transition(state, { type: 'start' })).toBe(state);
    state = transition(state, { type: 'experience', value: 'comfortable' });
    expect(transition(state, { type: 'review' })).toBe(state);
    state = transition(state, { type: 'goal', value: 'design-reasoning' });
    state = transition(state, { type: 'review' });
    expect(state).toEqual({
      phase: 'introduction',
      profile: { experience: 'comfortable', goal: 'design-reasoning' },
    });
    expect(transition(state, { type: 'edit-setup' })).toEqual({
      phase: 'setup',
      experience: 'comfortable',
      goal: 'design-reasoning',
    });
    expect(transition(state, { type: 'start' }).phase).toBe('active');
  });
  it('rejects invalid runtime profile values', () => {
    for (const action of [
      { type: 'experience', value: 'expert' },
      { type: 'goal', value: 'grade' },
    ]) {
      const state = initialSession();
      expect(transition(state, action as LearningAction)).toBe(state);
    }
  });
  it('starts on the first step with no revealed hints', () => {
    const state = start();
    expect(state.phase).toBe('active');
    if (!('interactions' in state)) throw new Error('Not active');
    expect(state.stepIndex).toBe(0);
    expect(
      state.interactions.every(
        (item) => item.hintLevel === 0 && !item.completed,
      ),
    ).toBe(true);
  });
  it('rejects advancement without learner completion', () => {
    const state = start();
    expect(transition(state, { type: 'advance', stepId: 'sketch' })).toBe(
      state,
    );
    expect(transition(state, { type: 'advance', stepId: 'solid' })).toBe(state);
  });
  for (const level of [1, 2, 3] as const)
    it(`reveals hint level ${level} only after its predecessor`, () => {
      let state = start();
      for (let n = 1; n <= level; n++)
        state = transition(state, {
          type: 'hint',
          stepId: 'sketch',
          level: n as 1 | 2 | 3,
        });
      expect(sessionProgress(state, lesson).hints).toBe(level);
      expect('interactions' in state && state.interactions[0]?.hintLevel).toBe(
        level,
      );
      expect(transition(state, { type: 'hint', stepId: 'sketch', level })).toBe(
        state,
      );
    });
  it('cannot skip, decrement or exceed the hint ladder', () => {
    let state = start();
    expect(
      transition(state, { type: 'hint', stepId: 'sketch', level: 2 }),
    ).toBe(state);
    for (const level of [1, 2, 3] as const)
      state = transition(state, { type: 'hint', stepId: 'sketch', level });
    expect(
      transition(state, { type: 'hint', stepId: 'sketch', level: 1 }),
    ).toBe(state);
    expect(
      transition(state, {
        type: 'hint',
        stepId: 'sketch',
        level: 4,
      } as unknown as LearningAction),
    ).toBe(state);
    expect(sessionProgress(state, lesson).hints).toBe(3);
  });
  it('records vocabulary uniquely even after close and reopen', () => {
    let state = start();
    for (let i = 0; i < 3; i++)
      state = transition(state, {
        type: 'vocabulary',
        stepId: 'sketch',
        termId: 'plane',
      });
    expect(sessionProgress(state, lesson).vocabulary).toBe(1);
    expect(
      'interactions' in state && state.interactions[0]?.vocabularyVisible,
    ).toEqual(['plane']);
    expect(
      transition(state, {
        type: 'vocabulary',
        stepId: 'sketch',
        termId: 'unknown',
      }),
    ).toBe(state);
  });
  it('toggles Why without changing progress', () => {
    const state = start();
    const open = transition(state, { type: 'why', stepId: 'sketch' });
    expect('interactions' in open && open.interactions[0]?.whyOpen).toBe(true);
    expect(transition(open, { type: 'why', stepId: 'sketch' })).toEqual(state);
    expect(sessionProgress(open, lesson)).toEqual(
      sessionProgress(state, lesson),
    );
  });
  it('marks learner completion once, then advances without counting a hint-free future step', () => {
    let state = start();
    state = transition(state, { type: 'mark-done', stepId: 'sketch' });
    expect(sessionProgress(state, lesson)).toMatchObject({
      completed: 1,
      withoutHints: 1,
      forgeVerified: 0,
      checkable: 0,
    });
    expect(transition(state, { type: 'mark-done', stepId: 'sketch' })).toBe(
      state,
    );
    expect(
      transition(state, { type: 'hint', stepId: 'sketch', level: 1 }),
    ).toBe(state);
    state = transition(state, { type: 'advance', stepId: 'sketch' });
    expect('stepIndex' in state && state.stepIndex).toBe(1);
    expect(transition(state, { type: 'advance', stepId: 'sketch' })).toBe(
      state,
    );
  });
  it('completes only after every required step is learner-marked and preserves observed totals', () => {
    let state = start();
    state = transition(state, { type: 'hint', stepId: 'sketch', level: 1 });
    for (const step of lesson.steps) {
      state = transition(state, { type: 'mark-done', stepId: step.id });
      expect(state.phase).toBe('active');
      state = transition(state, { type: 'advance', stepId: step.id });
    }
    expect(state.phase).toBe('completed');
    expect(sessionProgress(state, lesson)).toEqual({
      completed: 3,
      total: 3,
      hints: 1,
      vocabulary: 0,
      withoutHints: 2,
      forgeVerified: 0,
      checkable: 0,
    });
    expect(transition(state, { type: 'hint', stepId: 'solid', level: 1 })).toBe(
      state,
    );
  });
  it('rejects final completion when a required interaction is missing', () => {
    const initial = start();
    if (!('interactions' in initial)) throw new Error('Not active');
    const state: LearningSession = {
      ...initial,
      stepIndex: 2,
      interactions: initial.interactions.map((item, i) => ({
        ...item,
        completed: i === 2,
      })),
    };
    expect(transition(state, { type: 'advance', stepId: 'solid' })).toBe(state);
  });
  it('reset clears profile, hint history and progress at every stage', () => {
    let state = start();
    state = transition(state, { type: 'hint', stepId: 'sketch', level: 1 });
    expect(transition(state, { type: 'reset' })).toEqual(initialSession());
    expect(transition(initialSession(), { type: 'reset' })).toEqual(
      initialSession(),
    );
  });
  it('leaves inputs immutable', () => {
    const state = start();
    const before = JSON.stringify(state);
    transition(state, { type: 'hint', stepId: 'sketch', level: 1 });
    expect(JSON.stringify(state)).toBe(before);
  });
});
