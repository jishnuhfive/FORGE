import type {
  BriefSection,
  CadContext,
  HistoryEntry,
  RunStep,
  ValidationCheck,
} from '../lib/types';

// Synthetic development fixtures. This module is imported only by the DEV-gated lab.
export const sampleContext: CadContext = {
  kind: 'preview',
  document: 'Camera Slider',
  workspace: 'Main · sample',
  element: 'Carriage Part Studio',
  selection: '1 face',
};
export const sampleBrief: BriefSection[] = [
  {
    title: 'Goal',
    values: [
      {
        label: 'Mechanism',
        value: 'Motorized camera slider',
        source: 'confirmed',
      },
    ],
  },
  {
    title: 'Functional requirements',
    values: [
      {
        label: 'Motion',
        value: 'Smooth, belt-driven linear travel',
        source: 'confirmed',
      },
    ],
  },
  {
    title: 'Dimensions',
    values: [
      { label: 'Travel', value: '≥ 400 mm', source: 'confirmed' },
      { label: 'Rail diameter', value: '8 mm', source: 'confirmed' },
    ],
  },
  {
    title: 'Loads',
    values: [{ label: 'Payload', value: '0.30 kg', source: 'confirmed' }],
  },
  {
    title: 'Available inventory',
    values: [
      {
        label: 'Drive',
        value: 'NEMA 17 · GT2 belt · GT2 pulleys',
        source: 'confirmed',
      },
      {
        label: 'Hardware',
        value: '8 mm rails · bearings · M4 hardware',
        source: 'confirmed',
      },
    ],
  },
  {
    title: 'Manufacturing',
    values: [
      {
        label: 'Printer envelope',
        value: '220 × 220 × 250 mm',
        source: 'confirmed',
      },
      { label: 'Material', value: 'PETG', source: 'confirmed' },
    ],
  },
  {
    title: 'Constraints',
    values: [
      {
        label: 'Fabrication',
        value: 'Printed parts with off-the-shelf hardware',
        source: 'confirmed',
      },
    ],
  },
  {
    title: 'Assumptions',
    values: [
      { label: 'Orientation', value: 'Horizontal use only', source: 'assumed' },
      { label: 'Rail length', value: '500 mm', source: 'assumed' },
    ],
  },
  {
    title: 'Missing information',
    values: [
      {
        label: 'Bearing model',
        value: 'Confirm before creating geometry',
        source: 'missing',
      },
      { label: 'Travel speed', value: 'Not provided', source: 'missing' },
    ],
  },
];
export const sampleSteps: RunStep[] = [
  {
    id: 'requirements',
    title: 'Understanding requirements',
    status: 'complete',
  },
  {
    id: 'inspect',
    title: 'Inspecting CAD',
    status: 'complete',
    description: 'Sample document context only',
  },
  { id: 'plan', title: 'Planning mechanism', status: 'complete' },
  { id: 'carriage', title: 'Creating carriage', status: 'complete' },
  {
    id: 'motor',
    title: 'Creating motor mount',
    status: 'active',
    description: 'Previewing this step; no CAD operation runs',
  },
  { id: 'rails', title: 'Creating rail supports', status: 'pending' },
  { id: 'assembly', title: 'Building assembly', status: 'pending' },
  { id: 'dimensions', title: 'Checking dimensions', status: 'pending' },
  { id: 'validation', title: 'Running validation', status: 'pending' },
];
export const sampleValidation: ValidationCheck[] = [
  {
    id: 'geometry',
    category: 'Geometry',
    title: 'Part geometry',
    required: 'Closed solids',
    measured: '4 sample solids',
    status: 'pass',
  },
  {
    id: 'travel',
    category: 'Dimensions',
    title: 'Travel',
    required: '≥ 400 mm',
    measured: '416 mm',
    status: 'pass',
  },
  {
    id: 'printer',
    category: 'Manufacturing',
    title: 'Printer fit',
    required: '220 × 220 mm bed',
    measured: '124 × 78 mm largest part',
    status: 'pass',
  },
  {
    id: 'inventory',
    category: 'Inventory',
    title: 'Required inventory',
    required: 'Listed drive & hardware',
    measured: 'Matches sample inventory',
    status: 'pass',
  },
  {
    id: 'assembly',
    category: 'Assembly',
    title: 'Assembly completeness',
    required: 'All planned parts',
    measured: '4 of 4 sample parts',
    status: 'pass',
  },
  {
    id: 'motion',
    category: 'Motion',
    title: 'Travel path',
    required: 'Clear linear path',
    measured: 'Clear in sample layout',
    status: 'pass',
    detail: 'Illustrative layout check; dynamic behavior is not evaluated.',
  },
  {
    id: 'clearance',
    category: 'Clearance',
    title: 'Belt clearance',
    required: 'Confirm with belt specification',
    measured: 'Specification not provided',
    status: 'warning',
    detail: 'Confirm the belt profile before manufacturing.',
  },
  {
    id: 'mass',
    category: 'Mass',
    title: 'Mass',
    required: 'Material and geometry evidence',
    measured: 'Not available',
    status: 'unverified',
    detail: 'No mass calculation or real CAD evidence is available.',
  },
];
export const sampleHistory: HistoryEntry[] = [
  {
    id: 'project',
    kind: 'project',
    title: 'Camera Slider',
    detail: 'Belt-driven linear mechanism · sample project',
    time: 'Sample · Oct 3',
  },
  {
    id: 'project2',
    kind: 'project',
    title: 'NEMA 17 Mount',
    detail: 'Parametric mounting bracket · sample project',
    time: 'Sample · Oct 2',
  },
  {
    id: 'conversation',
    kind: 'conversation',
    title: 'Define slider requirements',
    detail: 'Travel, payload and available inventory',
    time: 'Sample · 10:00',
  },
  {
    id: 'run',
    kind: 'run',
    title: 'Camera slider / run 001',
    detail: 'Illustrative run · no agent executed',
    time: 'Sample · 10:05',
  },
  {
    id: 'operation',
    kind: 'operation',
    title: 'Carriage extrusion',
    detail: 'Preview operation record · no CAD was changed',
    time: 'Sample · 10:06',
  },
  {
    id: 'validation',
    kind: 'validation',
    title: 'Slider validation report',
    detail: '6 Pass · 1 Warning · 1 Unverified · synthetic evidence',
    time: 'Sample · 10:08',
  },
  {
    id: 'activity1',
    kind: 'activity',
    title: 'Requirements reviewed',
    detail: 'Sample engineering brief prepared',
    time: 'Sample · 10:02',
  },
  {
    id: 'activity2',
    kind: 'activity',
    title: 'Plan preview opened',
    detail: 'No authorization or CAD write recorded',
    time: 'Sample · 10:04',
  },
];
