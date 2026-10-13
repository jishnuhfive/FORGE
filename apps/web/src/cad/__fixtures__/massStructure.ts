// Invented structure metadata, with no provider values or private keys.
export const syntheticMassStructure = {
  diagnostic: 'forge-mass-structure-v1',
  reason: 'schema_validation',
  recordKind: 'aggregate',
  fields: [
    { field: 'response', type: 'object' },
    { field: 'bodies', type: 'object' },
    { field: 'mass', type: 'array', length: 3, items: ['number'] },
    { field: 'principalAxes', type: 'absent' },
  ],
  massSigns: {
    position0: 'negative',
    position1: 'negative',
    position2: 'positive',
  },
  hasMass: false,
  massMissingCountCategory: 'positive',
  validation: [
    {
      field: 'mass',
      reason: 'invalid_bounds',
      failedPredicates: ['negative_nominal'],
      comparisons: {
        position0_vs_position1: 'greater',
        position0_vs_position2: 'less',
        position1_vs_position2: 'less',
      },
    },
  ],
};
