import type { Answer } from '../api';

// Synthetic transport fixtures using the unchanged server-owned canonical grammar.
export const fullLimits = [
  'Forge inspected the default configuration at the end of the feature list. Data comes from separate reads; currentness and snapshot consistency remain unverified.',
  "Physical units haven't been independently verified. Exact mass and volume aren't supplied.",
  "Forge hasn't run deterministic engineering validation on this design. Validation remains unverified.",
  "Forge's feature ordering evidence describes returned feature-list order only. That ordering does not establish dependency, ownership, or parent-child relationships. Selection references do not establish ownership. Missing relationships prove nothing about CAD. A terminal feature is known only when complete feature-list and end-of-list rollback evidence establish one.",
];
type Fact = Answer['evidence'][number];
export const capturedFeatures: Fact[] = [
  {
    id: 'feature_1',
    status: 'verified',
    statement:
      'The first captured feature is named "Sketch Gate" (sketch; active).',
  },
  {
    id: 'feature_2',
    status: 'verified',
    statement:
      'The second captured feature is named "Extrude 1" (extrude; active).',
  },
  {
    id: 'feature_3',
    status: 'verified',
    statement:
      'The third captured feature is named "Fillet 1" (fillet; active).',
  },
];
export const orderFacts: Fact[] = [
  {
    id: 'order_1_2',
    status: 'verified',
    statement:
      'The first captured modeled feature, "Sketch Gate", appears before the second captured modeled feature, "Extrude 1", in the returned feature order.',
  },
  {
    id: 'order_2_3',
    status: 'verified',
    statement:
      'The second captured modeled feature, "Extrude 1", appears before the third captured modeled feature, "Fillet 1", in the returned feature order.',
  },
];
export function canonicalAnswer(
  evidence: Fact[],
  changes: Partial<Answer> = {},
): Answer {
  return structuredClone({
    answer: evidence.map((item) => item.statement).join('\n\n'),
    evidence,
    uncertainties: fullLimits,
    discussion: '',
    assumptions: [],
    follow_up_questions: [],
    capability_state: 'read_only',
    captured_at: '2026-10-23T12:00:00+00:00',
    ...changes,
  });
}
const inventory = canonicalAnswer([
  {
    id: 'features',
    status: 'verified',
    statement: 'The captured Part Studio contains 3 features.',
  },
  ...capturedFeatures,
  {
    id: 'parts',
    status: 'verified',
    statement: 'The captured Part Studio contains 1 part.',
  },
  {
    id: 'bodies',
    status: 'verified',
    statement: 'The captured Part Studio contains 1 body.',
  },
]);
const selection = canonicalAnswer(
  [
    { id: 'selection', status: 'verified', statement: 'One face is selected.' },
    {
      id: 'selection_ownership',
      status: 'unknown',
      statement: 'Selection ownership by a part, body or feature is unknown.',
    },
    {
      id: 'selection_part',
      status: 'unknown',
      statement: "The selected face's owning part is unknown.",
    },
    {
      id: 'selection_body',
      status: 'unknown',
      statement: "The selected face's owning body is unknown.",
    },
    {
      id: 'selection_feature',
      status: 'unknown',
      statement: "The selected face's owning feature is unknown.",
    },
    {
      id: 'selection_dimensions',
      status: 'unknown',
      statement: "The selected face's dimensions are unknown.",
    },
    {
      id: 'selection_type',
      status: 'unknown',
      statement: "The selected face's surface type is unknown.",
    },
    {
      id: 'selection_geometry',
      status: 'unknown',
      statement:
        'Selected-face geometry, including area and normal direction, is unknown.',
    },
    {
      id: 'selection_capability',
      status: 'verified',
      statement:
        "Forge can confirm the selection type, but selection-specific ownership and measurements aren't available yet.",
    },
  ],
  {
    answer:
      "One face is selected.\n\nOwning part, body, feature, dimensions, surface type and face-specific geometry (including area and normal direction) are currently unknown.\n\nForge can confirm the selection type, but selection-specific ownership and measurements aren't available yet.",
  },
);
const write = canonicalAnswer([
  {
    id: 'write_capability',
    status: 'verified',
    statement:
      "Forge is currently read-only and can't modify CAD yet. I can inspect the current model and explain or propose how a change could be made.",
  },
  {
    id: 'no_cad_writes',
    status: 'verified',
    statement: 'Forge performed no CAD writes for this request.',
  },
  {
    id: 'write_target_unknown',
    status: 'unknown',
    statement:
      'The captured evidence does not identify a verified width-driving dimension, so I cannot safely identify which parameter to edit.',
  },
  ...capturedFeatures.slice(0, 2),
]);
const empty = canonicalAnswer(
  [
    ...(['features', 'parts', 'bodies'] as const).map((id): Fact => ({
      id,
      status: 'verified',
      statement: `The captured Part Studio contains 0 ${id}.`,
    })),
    {
      id: 'features_completeness',
      status: 'unverified',
      statement: 'Features evidence is complete; 0 entries omitted.',
    },
  ],
  {
    discussion:
      'Compare proposed dimensions against clearance and loading requirements before making changes.',
    assumptions: [
      'For a hypothetical comparison only, assume static loading; actual loads have not been verified.',
    ],
    follow_up_questions: [
      'What loads and clearances should the design accommodate?',
    ],
  },
);

export const polishCases = {
  inventory: {
    prompt: 'What features are in my model and in what order?',
    result: inventory,
    paragraphs: ['Your model has 3 features:'],
  },
  terminal: {
    prompt: 'What is the final feature?',
    result: canonicalAnswer([
      {
        id: 'terminal_feature',
        status: 'verified',
        statement:
          'The terminal feature in the complete captured feature list is the third feature, "Fillet 1".',
      },
    ]),
    paragraphs: ['Fillet 1 is the final feature.'],
  },
  order: {
    prompt: 'What comes before the final fillet?',
    result: canonicalAnswer([orderFacts[1]!]),
    paragraphs: ['Extrude 1 comes before Fillet 1.'],
  },
  state: {
    prompt: 'Is Fillet 1 active or suppressed?',
    result: canonicalAnswer([capturedFeatures[2]!]),
    paragraphs: ['Fillet 1 is active.'],
  },
  dependency: {
    prompt: 'Does Extrude 1 depend on Sketch Gate?',
    result: canonicalAnswer([orderFacts[0]!]),
    paragraphs: [
      "I can't confirm that Extrude 1 depends on Sketch Gate.",
      'I can verify that Sketch Gate comes before Extrude 1 in the feature order.',
    ],
  },
  selection: {
    prompt: 'What feature owns this face?',
    result: selection,
    paragraphs: [
      "I can see that one face is selected, but its owning feature isn't known yet.",
    ],
  },
  write: {
    prompt: 'Make Extrude 1 wider.',
    result: write,
    paragraphs: [
      "Forge is read-only here, so I can't change the model.",
      "I also can't verify which parameter controls the width from the current evidence.",
    ],
  },
  empty: {
    prompt: 'What features are in this model?',
    result: empty,
    paragraphs: ['This Part Studio has no modeled features.'],
  },
};
