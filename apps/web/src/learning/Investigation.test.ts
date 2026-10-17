import { describe, expect, it } from 'vitest';
import { mountingBracket } from './bracket';
import { notSure } from './lesson';
import { sketchToSolid } from './sample';
import {
  activeInvestigation,
  challengeProgress,
  initialSession,
  reduceSession,
  reflectionProgress,
  sessionProgress,
} from './session';
import type { CheckFinding, LearningAction, LearningSession } from './session';

const lesson = mountingBracket;
const run = (
  actions: LearningAction[],
  from: LearningSession = initialSession(),
  using = lesson,
) =>
  actions.reduce<LearningSession>(
    (state, action) => reduceSession(using, state, action),
    from,
  );
const begin: LearningAction[] = [
  { type: 'experience', value: 'beginner' },
  { type: 'goal', value: 'guided-project' },
  { type: 'review' },
  { type: 'start' },
];
const finish = (id: string): LearningAction[] => [
  { type: 'mark-done', stepId: id },
  { type: 'advance', stepId: id },
];
// Reach a given guided step by learner-completing the ones before it.
const toStep = (id: string): LearningAction[] => [
  ...begin,
  ...lesson.steps
    .slice(
      0,
      lesson.steps.findIndex((step) => step.id === id),
    )
    .flatMap((step) => finish(step.id)),
];
const finishGuided: LearningAction[] = [
  ...begin,
  ...lesson.steps.flatMap((step) => finish(step.id)),
];

const f = (
  requirementId: string,
  status: CheckFinding['status'],
  reason: string,
  finding: string,
  blocking = true,
): CheckFinding => ({ requirementId, status, reason, finding, blocking });
const noExtrusion = [
  f(
    'extrude.exists',
    'FAIL',
    'missing',
    'Forge sees no active extrude feature yet.',
  ),
  f('body.solid', 'FAIL', 'missing', 'Forge sees no solid body yet.'),
  f(
    'extrude.depth',
    'UNVERIFIED',
    'not_observable',
    'Cannot read thickness.',
    false,
  ),
];
const extrudeOnlyOk = [
  f('extrude.exists', 'PASS', 'met', 'Forge sees an active extrude feature.'),
  f('body.solid', 'FAIL', 'missing', 'Forge sees no solid body yet.'),
  f(
    'extrude.depth',
    'UNVERIFIED',
    'not_observable',
    'Cannot read thickness.',
    false,
  ),
];
const allOk = [
  f('extrude.exists', 'PASS', 'met', 'Forge sees an active extrude feature.'),
  f('body.solid', 'PASS', 'met', 'Forge sees a solid body.'),
  f(
    'extrude.depth',
    'UNVERIFIED',
    'not_observable',
    'Cannot read thickness.',
    false,
  ),
];
const result = (
  stepId: string,
  findings: CheckFinding[],
  outcome: 'verified' | 'not_met' | 'unverified' = 'not_met',
): LearningAction => ({ type: 'check-result', stepId, outcome, findings });
const step2 = (...more: LearningAction[]) =>
  run([...toStep('base-solid'), ...more]);
const inv = (state: LearningSession, id: string, index = 1) =>
  'interactions' in state
    ? state.interactions[index]?.investigations?.[id]
    : undefined;

describe('investigation triggers', () => {
  it('starts with no investigation state at all', () => {
    const state = step2();
    expect(
      'interactions' in state &&
        state.interactions.every((i) => !i.investigations),
    ).toBe(true);
  });
  it('a blocking FAIL opens the authored investigation with the server finding as Observed', () => {
    const state = step2(result('base-solid', noExtrusion));
    expect(inv(state, 'no-extrusion')).toEqual({
      status: 'open',
      guidance: 'full',
      observed: 'Forge sees no active extrude feature yet.',
      latest: 'Forge sees no active extrude feature yet.',
    });
  });
  it('opens only one investigation at a time even when two requirements fail', () => {
    const state = step2(result('base-solid', noExtrusion));
    expect(inv(state, 'no-solid-body')).toBeUndefined();
  });
  it('PASS never opens an investigation', () => {
    const state = step2(result('base-solid', allOk, 'verified'));
    expect(inv(state, 'no-extrusion')).toBeUndefined();
    expect(inv(state, 'no-solid-body')).toBeUndefined();
  });
  it('a nonblocking UNVERIFIED result never opens one', () => {
    const state = step2(
      result('base-solid', [
        extrudeOnlyOk[0]!,
        f('body.solid', 'PASS', 'met', 'ok'),
        extrudeOnlyOk[2]!,
      ]),
    );
    expect(
      'interactions' in state && state.interactions[1]?.investigations,
    ).toBeUndefined();
  });
  it('an unreadable-evidence UNVERIFIED on a blocking requirement does not open one', () => {
    const state = step2(
      result('base-solid', [
        f(
          'extrude.exists',
          'UNVERIFIED',
          'evidence_unavailable',
          'Cannot read.',
        ),
        f('body.solid', 'UNVERIFIED', 'evidence_unavailable', 'Cannot read.'),
      ]),
    );
    expect(
      'interactions' in state && state.interactions[1]?.investigations,
    ).toBeUndefined();
  });
  it('a non-blocking FAIL never opens one', () => {
    const state = step2(
      result('base-solid', [
        f('extrude.exists', 'FAIL', 'missing', 'x', false),
      ]),
    );
    expect(inv(state, 'no-extrusion')).toBeUndefined();
  });
  it('a result without findings changes nothing about investigations', () => {
    const state = step2({
      type: 'check-result',
      stepId: 'base-solid',
      outcome: 'not_met',
    });
    expect(
      'interactions' in state && state.interactions[1]?.investigations,
    ).toBeUndefined();
  });
  it('step 3 FAIL, step 3 fillet WARNING and step 4 face proxy open their own cases', () => {
    const second = run([
      ...toStep('second-portion'),
      result('second-portion', [
        f('bracket.second_portion', 'FAIL', 'missing', 'Plain block.'),
      ]),
    ]);
    expect(inv(second, 'no-second-portion', 2)?.status).toBe('open');
    const warn = run([
      ...toStep('second-portion'),
      result(
        'second-portion',
        [
          f(
            'bracket.second_portion',
            'WARNING',
            'ambiguous_signal',
            'Ambiguous.',
          ),
        ],
        'unverified',
      ),
    ]);
    expect(inv(warn, 'ambiguous-faces', 2)?.status).toBe('open');
    const holes = run([
      ...toStep('mounting-holes'),
      result('mounting-holes', [
        f('bracket.mounting_faces', 'FAIL', 'missing', 'Few faces.'),
      ]),
    ]);
    expect(inv(holes, 'few-mounting-faces', 3)?.status).toBe('open');
  });
  it('the sample lesson and steps without authored cases are unaffected', () => {
    const state = run(
      [...begin, result('sketch', [f('x', 'FAIL', 'missing', 'x')])],
      initialSession(),
      sketchToSolid,
    );
    expect('interactions' in state && state.interactions[0]).not.toHaveProperty(
      'investigations',
    );
  });
});

describe('prediction and reveal', () => {
  const open = () => step2(result('base-solid', noExtrusion));
  const predict = (choice: string): LearningAction => ({
    type: 'investigation-predict',
    stepId: 'base-solid',
    investigationId: 'no-extrusion',
    choice,
  });
  const reveal = (part: 'hypothesis' | 'recommendation'): LearningAction => ({
    type: 'investigation-reveal',
    stepId: 'base-solid',
    investigationId: 'no-extrusion',
    part,
  });
  it('records an authored choice and accepts "I\'m not sure"', () => {
    expect(
      inv(run([predict('make-3d')], open()), 'no-extrusion')?.prediction,
    ).toBe('make-3d');
    expect(
      inv(run([predict(notSure)], open()), 'no-extrusion')?.prediction,
    ).toBe(notSure);
  });
  it('rejects unknown choices and unknown investigations', () => {
    const state = open();
    expect(run([predict('made-up')], state)).toBe(state);
    expect(
      run(
        [
          {
            type: 'investigation-predict',
            stepId: 'base-solid',
            investigationId: 'nope',
            choice: 'make-3d',
          },
        ],
        state,
      ),
    ).toBe(state);
  });
  it('reveals nothing before the student has thought first', () => {
    const state = open();
    expect(run([reveal('hypothesis')], state)).toBe(state);
    expect(run([reveal('recommendation')], state)).toBe(state);
  });
  it('any answer, including not sure, unlocks the possible explanation', () => {
    const state = run([predict(notSure), reveal('hypothesis')], open());
    expect(inv(state, 'no-extrusion')?.hypothesis).toBe(true);
  });
  it('full guidance needs the explanation before the next-step suggestion', () => {
    const answered = run([predict('make-3d')], open());
    expect(run([reveal('recommendation')], answered)).toBe(answered);
    const both = run(
      [reveal('hypothesis'), reveal('recommendation')],
      answered,
    );
    expect(inv(both, 'no-extrusion')).toMatchObject({
      hypothesis: true,
      recommendation: true,
    });
  });
  it('an expectation is recorded only for authored choices on the step that has one', () => {
    const state = step2({
      type: 'expectation',
      stepId: 'base-solid',
      choice: 'feature-and-body',
    });
    expect('interactions' in state && state.interactions[1]?.expectation).toBe(
      'feature-and-body',
    );
    const ignored = step2({
      type: 'expectation',
      stepId: 'base-solid',
      choice: 'bogus',
    });
    expect(
      'interactions' in ignored && ignored.interactions[1]?.expectation,
    ).toBeUndefined();
    const notSureState = step2({
      type: 'expectation',
      stepId: 'base-solid',
      choice: notSure,
    });
    expect(
      'interactions' in notSureState &&
        notSureState.interactions[1]?.expectation,
    ).toBe(notSure);
    const other = run([
      ...begin,
      { type: 'expectation', stepId: 'base-sketch', choice: notSure },
    ]);
    expect(
      'interactions' in other && other.interactions[0]?.expectation,
    ).toBeUndefined();
  });
  it('never touches the deterministic verified flag, hints or completion', () => {
    const before = open();
    const after = run([predict('make-3d'), reveal('hypothesis')], before);
    const a = 'interactions' in before ? before.interactions[1]! : null;
    const b = 'interactions' in after ? after.interactions[1]! : null;
    expect([b?.hintLevel, b?.completed, b?.forgeVerified]).toEqual([
      a?.hintLevel,
      a?.completed,
      a?.forgeVerified,
    ]);
    expect(sessionProgress(after, lesson)).toEqual(
      sessionProgress(before, lesson),
    );
  });
});

describe('recheck linkage and stale results', () => {
  const opened = () => step2(result('base-solid', noExtrusion));
  it('a re-check PASS resolves the investigation with the fresh finding', () => {
    const state = run([result('base-solid', allOk, 'verified')], opened());
    expect(inv(state, 'no-extrusion')).toMatchObject({
      status: 'resolved',
      rechecked: true,
      observed: 'Forge sees no active extrude feature yet.',
      latest: 'Forge sees an active extrude feature.',
    });
  });
  it('a re-check that still fails stays open and says so', () => {
    const state = run([result('base-solid', noExtrusion)], opened());
    expect(inv(state, 'no-extrusion')).toMatchObject({
      status: 'open',
      rechecked: true,
    });
  });
  it('the case that resolved moves on to the next failing requirement', () => {
    const state = run([result('base-solid', extrudeOnlyOk)], opened());
    expect(inv(state, 'no-extrusion')?.status).toBe('resolved');
    expect(inv(state, 'no-solid-body')).toMatchObject({ status: 'open' });
    expect(
      activeInvestigation(
        lesson.steps[1]!,
        'interactions' in state ? state.interactions[1]! : (null as never),
      )?.authored.id,
    ).toBe('no-solid-body');
  });
  it('PASS then a later FAIL revokes the resolved state', () => {
    const state = run(
      [
        result('base-solid', allOk, 'verified'),
        result('base-solid', noExtrusion),
      ],
      opened(),
    );
    expect(inv(state, 'no-extrusion')?.status).toBe('open');
    expect(inv(state, 'no-extrusion')?.latest).toBe(
      'Forge sees no active extrude feature yet.',
    );
  });
  it('PASS then an unverifiable result does not keep claiming it is resolved', () => {
    const state = run(
      [
        result('base-solid', allOk, 'verified'),
        result(
          'base-solid',
          [
            f(
              'extrude.exists',
              'UNVERIFIED',
              'evidence_stale',
              'Could not confirm.',
            ),
            f(
              'body.solid',
              'UNVERIFIED',
              'evidence_stale',
              'Could not confirm.',
            ),
          ],
          'unverified',
        ),
      ],
      opened(),
    );
    expect(inv(state, 'no-extrusion')?.status).toBe('open');
  });
  it('a resolved investigation can resolve again after a later PASS', () => {
    const state = run(
      [
        result('base-solid', allOk, 'verified'),
        result('base-solid', noExtrusion),
        result('base-solid', allOk, 'verified'),
      ],
      opened(),
    );
    expect(inv(state, 'no-extrusion')?.status).toBe('resolved');
  });
  it('a late result for another step cannot change this step or its investigation', () => {
    const state = opened();
    expect(run([result('base-sketch', allOk, 'verified')], state)).toBe(state);
    expect(run([result('second-portion', allOk, 'verified')], state)).toBe(
      state,
    );
  });
  it('a prediction aimed at another step is ignored', () => {
    const state = opened();
    expect(
      run(
        [
          {
            type: 'investigation-predict',
            stepId: 'second-portion',
            investigationId: 'no-extrusion',
            choice: 'make-3d',
          },
        ],
        state,
      ),
    ).toBe(state);
  });
  it('a prediction made on an earlier step does not carry into the next one', () => {
    const answered = run(
      [
        {
          type: 'investigation-predict',
          stepId: 'base-solid',
          investigationId: 'no-extrusion',
          choice: 'make-3d',
        },
        ...finish('base-solid'),
      ],
      opened(),
    );
    const now =
      'interactions' in answered ? answered.interactions[2] : undefined;
    expect(now?.investigations).toBeUndefined();
  });
  it('learner completion and the verified count are independent of the investigation', () => {
    const state = run(
      [
        { type: 'mark-done', stepId: 'base-solid' },
        result('base-solid', allOk, 'verified'),
      ],
      opened(),
    );
    expect(sessionProgress(state, lesson)).toMatchObject({
      completed: 2,
      forgeVerified: 1,
    });
  });
  it('survives unrelated navigation: state is plain session data', () => {
    const state = opened();
    // Design -> Learn only unmounts views; nothing in the reducer is touched.
    expect(JSON.parse(JSON.stringify(state))).toEqual(state);
  });
  it('reset clears every investigation and prediction', () => {
    const state = run([{ type: 'reset' }], opened());
    expect(state).toEqual(initialSession());
  });
});

describe('guidance fading', () => {
  it('the first mistake gets the full supported path', () => {
    const state = step2(result('base-solid', noExtrusion));
    expect(inv(state, 'no-extrusion')?.guidance).toBe('full');
  });
  it('a similar issue after a resolved one gets reduced guidance, explainably', () => {
    const state = run([
      ...toStep('base-solid'),
      result('base-solid', noExtrusion),
      result('base-solid', allOk, 'verified'),
      ...finish('base-solid'),
      result('second-portion', [
        f('bracket.second_portion', 'FAIL', 'missing', 'Plain block.'),
      ]),
    ]);
    expect(inv(state, 'no-second-portion', 2)?.guidance).toBe('reduced');
  });
  it('an unresolved earlier issue does not reduce guidance', () => {
    const state = run([
      ...toStep('base-solid'),
      result('base-solid', noExtrusion),
      ...finish('base-solid'),
      result('second-portion', [
        f('bracket.second_portion', 'FAIL', 'missing', 'Plain block.'),
      ]),
    ]);
    expect(inv(state, 'no-second-portion', 2)?.guidance).toBe('full');
  });
  it('a different kind of issue is not treated as similar', () => {
    const state = run([
      ...toStep('base-solid'),
      result('base-solid', noExtrusion),
      result('base-solid', allOk, 'verified'),
      ...finish('base-solid'),
      result(
        'second-portion',
        [
          f(
            'bracket.second_portion',
            'WARNING',
            'ambiguous_signal',
            'Ambiguous.',
          ),
        ],
        'unverified',
      ),
    ]);
    expect(inv(state, 'ambiguous-faces', 2)?.guidance).toBe('full');
  });
  it('reduced guidance can go straight to the short next step, and explanation stays available', () => {
    let state = run([
      ...toStep('base-solid'),
      result('base-solid', noExtrusion),
      result('base-solid', allOk, 'verified'),
      ...finish('base-solid'),
      result('second-portion', [
        f('bracket.second_portion', 'FAIL', 'missing', 'Plain block.'),
      ]),
    ]);
    const base = {
      stepId: 'second-portion',
      investigationId: 'no-second-portion',
    } as const;
    state = run(
      [{ ...base, type: 'investigation-predict', choice: notSure }],
      state,
    );
    state = run(
      [{ ...base, type: 'investigation-reveal', part: 'recommendation' }],
      state,
    );
    expect(inv(state, 'no-second-portion', 2)?.recommendation).toBe(true);
    state = run(
      [{ ...base, type: 'investigation-reveal', part: 'hypothesis' }],
      state,
    );
    expect(inv(state, 'no-second-portion', 2)?.hypothesis).toBe(true);
  });
  it('fading never hides what Forge observed or removes the prediction prompt', () => {
    const state = run([
      ...toStep('base-solid'),
      result('base-solid', noExtrusion),
      result('base-solid', allOk, 'verified'),
      ...finish('base-solid'),
      result('second-portion', [
        f('bracket.second_portion', 'FAIL', 'missing', 'Plain block.'),
      ]),
    ]);
    expect(inv(state, 'no-second-portion', 2)?.observed).toBe('Plain block.');
    expect(inv(state, 'no-second-portion', 2)?.prediction).toBeUndefined();
  });
  it('keeps no hidden score: progress selectors expose only plain counts', () => {
    const state = step2(result('base-solid', noExtrusion));
    const keys = [
      ...Object.keys(sessionProgress(state, lesson)),
      ...Object.keys(reflectionProgress(state)),
    ];
    expect(keys.join(' ')).not.toMatch(
      /mastery|score|grade|level|rank|percent|streak/i,
    );
    expect(JSON.stringify(state)).not.toMatch(/mastery|score|grade|streak/i);
  });
});

describe('reflection progress', () => {
  it('counts answered predictions and currently resolved investigations', () => {
    const base = {
      stepId: 'base-solid',
      investigationId: 'no-extrusion',
    } as const;
    const state = step2(
      { type: 'expectation', stepId: 'base-solid', choice: notSure },
      result('base-solid', noExtrusion),
      { ...base, type: 'investigation-predict', choice: 'make-3d' },
    );
    expect(reflectionProgress(state)).toEqual({
      predictions: 2,
      investigationsOpened: 1,
      investigationsResolved: 0,
    });
    const resolved = run([result('base-solid', allOk, 'verified')], state);
    expect(reflectionProgress(resolved).investigationsResolved).toBe(1);
    const revoked = run([result('base-solid', noExtrusion)], resolved);
    expect(reflectionProgress(revoked).investigationsResolved).toBe(0);
  });
});

describe('transfer challenge', () => {
  const challenge = lesson.transfer!;
  const stepId = challenge.steps[0]!.id;
  const start: LearningAction[] = [...finishGuided, { type: 'transfer-start' }];
  const inTransfer = (state: LearningSession) =>
    'transfer' in state ? state.transfer : undefined;
  const tfind = (
    requirementId: string,
    status: CheckFinding['status'],
    reason: string,
    finding: string,
  ) => f(requirementId, status, reason, finding);
  const tOk = [
    tfind('transfer.sketch', 'PASS', 'met', 'Forge sees an active sketch.'),
    tfind(
      'transfer.one_extrusion',
      'PASS',
      'met',
      'Forge sees exactly one active extrusion.',
    ),
    tfind('transfer.solid_body', 'PASS', 'met', 'Forge sees a solid body.'),
    tfind(
      'transfer.l_profile',
      'PASS',
      'met',
      'Forge sees a body with more faces.',
    ),
    f(
      'transfer.dimensions',
      'UNVERIFIED',
      'not_observable',
      'Cannot read.',
      false,
    ),
  ];
  const tTwo = [
    tfind('transfer.sketch', 'PASS', 'met', 'Forge sees an active sketch.'),
    tfind(
      'transfer.one_extrusion',
      'FAIL',
      'constraint_not_met',
      'Forge sees 2 active extrusions; this challenge asks for exactly one.',
    ),
    tfind('transfer.solid_body', 'PASS', 'met', 'Forge sees a solid body.'),
    tfind(
      'transfer.l_profile',
      'PASS',
      'met',
      'Forge sees a body with more faces.',
    ),
  ];

  it('cannot start before the guided lesson is complete, nor in a lesson without one', () => {
    const early = run([...toStep('base-solid'), { type: 'transfer-start' }]);
    expect(inTransfer(early)).toBeUndefined();
    const sample = run(
      [{ type: 'transfer-start' }],
      initialSession(),
      sketchToSolid,
    );
    expect(sample).toEqual(initialSession());
  });
  it('starts with its own fresh, separate progress', () => {
    const state = run(start);
    expect(inTransfer(state)).toMatchObject({ phase: 'active', stepIndex: 0 });
    expect(inTransfer(state)?.interactions).toHaveLength(1);
    expect(sessionProgress(state, lesson).completed).toBe(5);
    expect(challengeProgress(state, lesson)).toMatchObject({
      forgeVerified: 0,
      hints: 0,
      finished: false,
    });
  });
  it('a supported model verifies it; the guided count is untouched', () => {
    const state = run([...start, result(stepId, tOk, 'verified')]);
    expect(challengeProgress(state, lesson)?.forgeVerified).toBe(1);
    expect(sessionProgress(state, lesson).forgeVerified).toBe(0);
  });
  it('an incomplete model opens an independent investigation using Forge observation', () => {
    const state = run([...start, result(stepId, tTwo)]);
    const t =
      inTransfer(state)?.interactions[0]?.investigations?.['extra-extrusion'];
    expect(t).toMatchObject({
      status: 'open',
      guidance: 'independent',
      observed:
        'Forge sees 2 active extrusions; this challenge asks for exactly one.',
    });
    expect(challengeProgress(state, lesson)?.forgeVerified).toBe(0);
  });
  it('removing the extra extrusion and re-checking resolves it; going back revokes it', () => {
    const resolved = run([
      ...start,
      result(stepId, tTwo),
      result(stepId, tOk, 'verified'),
    ]);
    expect(
      inTransfer(resolved)?.interactions[0]?.investigations?.['extra-extrusion']
        ?.status,
    ).toBe('resolved');
    const back = run([result(stepId, tTwo)], resolved);
    expect(
      inTransfer(back)?.interactions[0]?.investigations?.['extra-extrusion']
        ?.status,
    ).toBe('open');
  });
  it('always uses independent guidance, even if a similar issue was resolved earlier', () => {
    const state = run([
      ...begin,
      ...finish('base-sketch'),
      result('base-solid', noExtrusion),
      result('base-solid', allOk, 'verified'),
      ...['base-solid', 'second-portion', 'mounting-holes', 'review'].flatMap(
        finish,
      ),
      { type: 'transfer-start' },
      result(stepId, [
        tfind(
          'transfer.one_extrusion',
          'FAIL',
          'missing',
          'Forge sees no active extrusion yet.',
        ),
      ]),
    ]);
    expect(
      inTransfer(state)?.interactions[0]?.investigations?.[
        'no-single-extrusion'
      ]?.guidance,
    ).toBe('independent');
  });
  it('the hint ladder is the same Phase 7 ladder, one deliberate level at a time', () => {
    const base = { stepId } as const;
    let state = run(start);
    state = run([{ ...base, type: 'hint', level: 3 }], state);
    expect(challengeProgress(state, lesson)?.hints).toBe(0); // no skipping
    state = run(
      [
        { ...base, type: 'hint', level: 1 },
        { ...base, type: 'hint', level: 2 },
        { ...base, type: 'hint', level: 3 },
      ],
      state,
    );
    expect(challengeProgress(state, lesson)).toMatchObject({
      hints: 3,
      fullExplanationUsed: true,
    });
  });
  it("completion is the learner's own mark plus Forge's latest verification, reported plainly", () => {
    const state = run([
      ...start,
      result(stepId, tOk, 'verified'),
      ...finish(stepId),
    ]);
    expect(inTransfer(state)?.phase).toBe('completed');
    expect(challengeProgress(state, lesson)).toEqual({
      total: 1,
      completed: 1,
      checkable: 1,
      forgeVerified: 1,
      hints: 0,
      fullExplanationUsed: false,
      finished: true,
      withoutHints: true,
    });
  });
  it('help used means it is not reported as completed without hints', () => {
    const state = run([
      ...start,
      { type: 'hint', stepId, level: 1 },
      result(stepId, tOk, 'verified'),
      ...finish(stepId),
    ]);
    expect(challengeProgress(state, lesson)).toMatchObject({
      withoutHints: false,
      hints: 1,
      fullExplanationUsed: false,
    });
  });
  it('a challenge the learner marks done is not independent if Forge no longer verifies it', () => {
    const state = run([
      ...start,
      result(stepId, tOk, 'verified'),
      result(stepId, tTwo),
      ...finish(stepId),
    ]);
    expect(challengeProgress(state, lesson)).toMatchObject({
      forgeVerified: 0,
      withoutHints: false,
    });
  });
  it('a late guided-step event cannot change the challenge, and vice versa', () => {
    const state = run(start);
    expect(run([result('base-solid', allOk, 'verified')], state)).toBe(state);
    expect(run([{ type: 'mark-done', stepId: 'base-sketch' }], state)).toBe(
      state,
    );
  });
  it('restarting the challenge keeps the guided lesson; a full reset clears everything', () => {
    const state = run([
      ...start,
      result(stepId, tOk, 'verified'),
      { type: 'transfer-restart' },
    ]);
    expect(challengeProgress(state, lesson)).toMatchObject({
      forgeVerified: 0,
      hints: 0,
    });
    expect(sessionProgress(state, lesson).completed).toBe(5);
    expect(run([{ type: 'reset' }], state)).toEqual(initialSession());
  });
  it('makes no whole-design or mastery claim in any selector', () => {
    const state = run([
      ...start,
      result(stepId, tOk, 'verified'),
      ...finish(stepId),
    ]);
    const text = JSON.stringify(challengeProgress(state, lesson));
    expect(text).not.toMatch(/mastery|score|grade|skill|ready|certif/i);
  });
});
