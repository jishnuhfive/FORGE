import type { Answer } from '../api';

// Invented evidence only; never imported by production components.
export const syntheticAnswer: Answer = {
  answer:
    'This Part Studio contains 2 active features: "Sketch 1", followed by "Extrude 1".\n\n1 solid part is reported: "Part 1". 1 solid body is reported. Forge received 6 face entries for the captured body. Edge and vertex counts remain unverified.',
  evidence: [
    {
      id: 'feature_1',
      statement: 'Sketch 1 is first in the returned feature list.',
      status: 'verified',
    },
    {
      id: 'feature_2',
      statement: 'Extrude 1 is second in the returned feature list.',
      status: 'verified',
    },
    {
      id: 'parts',
      statement: 'One part is reported in the captured Part Studio.',
      status: 'verified',
    },
    {
      id: 'body_1',
      statement:
        'One solid body is reported, with six returned face entries; edges and vertices are unknown.',
      status: 'verified',
    },
    {
      id: 'mass',
      statement:
        "Mass isn't available because material or density information may be missing.",
      status: 'unknown',
    },
  ],
  uncertainties: [
    'Physical units haven’t been independently verified. Forge hasn’t run deterministic engineering validation on this design.',
  ],
  discussion: '',
  assumptions: [],
  follow_up_questions: [],
  capability_state: 'read_only',
  captured_at: '2026-10-14T12:00:00+00:00',
};
export function resultStream(result = syntheticAnswer) {
  return (
    JSON.stringify({ type: 'progress', stage: 'inspecting' }) +
    '\n' +
    JSON.stringify({ type: 'result', result }) +
    '\n'
  );
}

export const syntheticWriteAnswer: Answer = {
  ...syntheticAnswer,
  answer:
    "Forge is currently read-only and can't modify CAD yet. I can inspect the current model and explain or propose how a change could be made.\n\nForge performed no CAD writes for this request.\n\nThe captured evidence does not identify a verified width-driving dimension, so I cannot safely identify which parameter to edit.",
  evidence: [
    {
      id: 'write_capability',
      statement:
        "Forge is currently read-only and can't modify CAD yet. I can inspect the current model and explain or propose how a change could be made.",
      status: 'verified',
    },
    {
      id: 'no_cad_writes',
      statement: 'Forge performed no CAD writes for this request.',
      status: 'verified',
    },
    {
      id: 'write_target_unknown',
      statement:
        'The captured evidence does not identify a verified width-driving dimension, so I cannot safely identify which parameter to edit.',
      status: 'unknown',
    },
  ],
};

export function syntheticSelectionAnswer(kind: 'FACE' | 'EDGE'): Answer {
  const noun = kind.toLowerCase();
  return {
    ...syntheticAnswer,
    answer: `One ${noun} is selected.\n\nOwning part, body, feature, dimensions and selection-specific geometry are currently unknown.\n\nForge can confirm the selection type, but selection-specific ownership and measurements aren't available yet.`,
    evidence: [
      {
        id: 'selection',
        statement: `One ${noun} is selected.`,
        status: 'verified',
      },
      {
        id: 'selection_body',
        statement: `The selected ${noun}'s owning body is unknown.`,
        status: 'unknown',
      },
      {
        id: 'selection_part',
        statement: `The selected ${noun}'s owning part is unknown.`,
        status: 'unknown',
      },
      {
        id: 'selection_feature',
        statement: `The selected ${noun}'s owning feature is unknown.`,
        status: 'unknown',
      },
      {
        id: 'selection_geometry',
        statement:
          kind === 'FACE'
            ? 'Selected-face area, normal direction and surface type are unknown.'
            : 'Adjacent faces and edge-specific geometry are unknown.',
        status: 'unknown',
      },
    ],
    discussion: '',
    assumptions: [],
    follow_up_questions: [],
  };
}

// Exact current server-owned statement grammar, using invented CAD only.
export const syntheticOverview: Answer = {
  ...syntheticAnswer,
  evidence: [
    {
      id: 'features',
      status: 'verified',
      statement: 'The captured Part Studio contains 2 features.',
    },
    {
      id: 'feature_1',
      status: 'verified',
      statement:
        'The first captured feature is named "Sketch 1" (sketch; active).',
    },
    {
      id: 'feature_2',
      status: 'verified',
      statement:
        'The second captured feature is named "Extrude 1" (extrude; active).',
    },
    {
      id: 'parts',
      status: 'verified',
      statement: 'The captured Part Studio contains 1 part.',
    },
    {
      id: 'part_1',
      status: 'verified',
      statement: 'Part 1: name "Part 1", reported body type "SOLID".',
    },
    {
      id: 'bodies',
      status: 'verified',
      statement: 'The captured Part Studio contains 1 body.',
    },
    {
      id: 'body_1',
      status: 'verified',
      statement:
        'Body 1: reported type "SOLID"; returned topology counts — face: 6, edge: unknown, vertex: unknown.',
    },
    {
      id: 'mass',
      status: 'unknown',
      statement:
        "Mass isn't available because material or density information may be missing. No exact mass can be verified.",
    },
  ],
};

// Invented general guidance; the server sends it with no evidence.
export const syntheticGuide: NonNullable<Answer['guide']> = {
  kind: 'guide',
  safety: 'safe',
  title: 'Rectangular mounting plate',
  summary: 'A 60 × 40 × 10 mm plate with two 8 mm holes.',
  key_dimensions: ['60 mm long', '40 mm wide', '10 mm thick', '8 mm holes'],
  assumptions: ['Hole positions were not given; assumed 10 mm from each end.'],
  questions: [],
  steps: [
    {
      title: 'Sketch the outline',
      action: 'Create a sketch on the Top plane and draw a rectangle.',
      controls: ['Sketch tool', 'Top plane', 'Corner rectangle'],
      parameters: ['60 mm', '40 mm'],
      check: 'The sketch is fully dimensioned and shows no blue lines.',
      why: 'Full constraints keep later edits predictable.',
    },
    {
      title: 'Cut the holes',
      action: 'Extrude the two circles with Remove.',
      controls: ['Extrude', 'Operation: Remove', 'End type: Through all'],
      parameters: ['8 mm diameter'],
      check: 'Two holes are visible in the feature tree preview.',
      why: 'Remove subtracts material from the plate instead of adding a pin.',
    },
  ],
  explanation: '',
  mistakes: ['Extruding the holes with Add instead of Remove.'],
  checklist: ['Two 8 mm holes pass through the plate.'],
  follow_ups: ['Should the plate have rounded corners?'],
};
export const syntheticGuideAnswer: Answer = {
  answer: 'Modeling guide: Rectangular mounting plate\n1. Sketch the outline',
  evidence: [],
  uncertainties: [
    'General Onshape guidance. Forge did not read your Part Studio for this and made no CAD changes. Follow the steps yourself in Onshape.',
  ],
  discussion: '',
  assumptions: [],
  follow_up_questions: [],
  capability_state: 'read_only',
  captured_at: null,
  explanation: '',
  guide: syntheticGuide,
};
