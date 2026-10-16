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
      statement: 'Mass is unavailable; material or density may be missing.',
      status: 'unknown',
    },
  ],
  uncertainties: [
    'Physical units are unverified. No deterministic validation has run.',
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
    'Forge cannot modify CAD in Phase 6. I can explain or propose how the change could be made.\n\nForge performed no CAD writes for this request.\n\nThe captured evidence does not identify a verified width-driving dimension, so I cannot safely identify which parameter to edit.',
  evidence: [
    {
      id: 'write_capability',
      statement:
        'Forge cannot modify CAD in Phase 6. I can explain or propose how the change could be made.',
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
    answer: `The panel reports one ${noun} selected.\n\nOwning part, body and feature: unknown. Dimensions and selection-specific geometry: unknown.\n\nSelection-specific ownership and measurements are not available in Phase 6.`,
    evidence: [
      {
        id: 'selection',
        statement: `The panel reports one ${noun} selected.`,
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
