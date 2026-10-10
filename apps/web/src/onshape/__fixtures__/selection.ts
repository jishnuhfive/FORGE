// Synthetic values matching the live EDGE, corrected FACE and clear structures.
// The human corrected the mislabeled FACE capture on 2026-10-10; no raw IDs supplied.
// The unknown fifth key is invented; neither its name nor value is interpreted.
export const edgeSelection = {
  messageName: 'SELECTION',
  selections: [
    {
      selectionType: 'ENTITY',
      selectionId: 'synthetic-edge-reference',
      entityType: 'EDGE',
      occurrencePath: undefined,
      syntheticUnknownField: 'synthetic-discarded-value',
    },
  ],
};
export const faceSelection = {
  messageName: 'SELECTION',
  selections: [
    {
      ...edgeSelection.selections[0],
      entityType: 'FACE',
      selectionId: 'synthetic-face-reference',
    },
  ],
};
export const clearedSelection = { messageName: 'SELECTION', selections: [] };
