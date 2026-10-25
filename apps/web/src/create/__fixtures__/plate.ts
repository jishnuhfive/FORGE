// Synthetic server responses shaped like cad_create's PlanReady + explain_plan.
const rect = {
  operation: 'CREATE_SKETCH_RECT',
  target: { kind: 'base_plane', plane: 'TOP' },
  center_x_um: 0,
  center_y_um: 0,
  width_um: 60000,
  height_um: 40000,
};
const circle = {
  operation: 'CREATE_SKETCH_CIRCLE',
  target: { kind: 'step_face', step: 's02', face: 'end_cap' },
  center_x_um: 0,
  center_y_um: 0,
  diameter_um: 8000,
};
const intents = [
  'define_base_profile',
  'form_base_body',
  'define_cut_profile',
  'remove_material',
] as const;
const text: Record<(typeof intents)[number], string> = {
  define_base_profile:
    'Sketch the outline that gives the part its basic shape.',
  form_base_body:
    'Extrude the outline into a solid so there is material to cut.',
  define_cut_profile:
    'Sketch the shape of material to remove on an existing face.',
  remove_material: 'Cut the sketched shape out of the solid.',
};
const ops = [
  rect,
  {
    operation: 'EXTRUDE_NEW',
    profile: 's01',
    extent: { kind: 'blind', depth_um: 10000 },
  },
  circle,
  {
    operation: 'EXTRUDE_REMOVE',
    profile: 's03',
    target_body: 's02',
    extent: { kind: 'through_all' },
  },
];
const deps = [[], ['s01'], ['s02'], ['s02', 's03']];
export const proposalId = 'p'.repeat(43);
export function ready(overrides: Record<string, unknown> = {}) {
  return {
    status: 'ready',
    proposal_id: proposalId,
    expires_at: Math.floor(Date.now() / 1000) + 600,
    brief: {
      kind: 'rect_plate_with_through_holes',
      width: { value: 60, unit: 'mm' },
      length: { value: 40, unit: 'mm' },
      thickness: { value: 10, unit: 'mm' },
      holes: [
        {
          diameter: { value: 8, unit: 'mm' },
          center_x: { value: 0, unit: 'mm' },
          center_y: { value: 0, unit: 'mm' },
        },
      ],
    },
    plan: {
      capability: 'rect_plate_with_through_holes',
      digest: 'a'.repeat(64),
      steps: intents.map((intent, i) => ({
        id: `s0${i + 1}`,
        intent,
        depends_on: deps[i],
        op: ops[i],
      })),
    },
    explanations: intents.map((intent, i) => ({
      step_id: `s0${i + 1}`,
      intent,
      rationale_key: `creation.rationale.${intent}`,
      text: text[intent],
      authority: 'none',
    })),
    ...overrides,
  };
}
export const verified = {
  state: 'verified_success',
  steps: Array(4).fill('verified_success'),
};
