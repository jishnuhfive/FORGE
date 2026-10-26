import type { Lesson, LessonStep } from './lesson';

// The Ask → Learn → Modify story: one manually built plate, five operations.
// Every dimension below belongs to the authored reference plate. Forge does not
// measure the learner's model, and no step here is deterministically checked.
const evidencePrompts = [
  'What does my current feature tree show?',
  'Is there a fillet in my model right now?',
];

const steps: LessonStep[] = [
  {
    id: 'plate-sketch',
    title: 'Sketch the plate outline',
    objective: 'Draw the flat outline the plate is built from.',
    instruction:
      'In Onshape, start a sketch on the Top plane and draw a corner rectangle (reference plate: 60 × 40 mm). Finish the sketch.',
    why: 'A sketch is a flat 2D drawing. A closed outline, called a profile, says what shape the part has when seen from above. It has no thickness yet.',
    vocabulary: [
      {
        id: 'profile',
        term: 'Profile',
        definition:
          'A closed outline in a sketch. A closed profile can be given depth.',
      },
    ],
    hints: {
      conceptual:
        'What shape do you see if you look straight down at a flat plate?',
      tool: 'Pick the Top plane, choose Sketch, use the Corner rectangle tool, then finish the sketch.',
      explanation:
        'The rectangle is the plate seen from above. The reference plate uses 60 mm by 40 mm; thickness comes from the next step, not from the sketch.',
    },
    expectation: {
      question:
        'Right after you finish the sketch, does the plate have thickness?',
      choices: [
        {
          id: 'solid-already',
          label: 'Yes, the rectangle is already a solid',
          response:
            'Not yet. A sketch is flat: it has an outline but no depth, so the next step has to add it.',
        },
        {
          id: 'flat',
          label: 'No, it is still a flat outline',
          response:
            'That matches how sketches work. The outline is a plan; the next feature turns it into a solid.',
        },
      ],
    },
    completion: 'learner-reported',
    askPrompts: ['What is a profile?', ...evidencePrompts],
  },
  {
    id: 'plate-extrude',
    title: 'Extrude the outline into a plate',
    objective: 'Give the outline thickness so it becomes a solid.',
    instruction:
      'Use Extrude on the sketch region. Choose New and a depth (reference plate: 10 mm).',
    why: 'Extrude pushes a closed profile along one direction. The sketch decides the outline; the Extrude decides how thick the solid is.',
    vocabulary: [
      {
        id: 'extrude',
        term: 'Extrude',
        definition:
          'A feature that gives a closed profile depth, creating a solid body.',
      },
    ],
    hints: {
      conceptual:
        'The outline is flat. What single operation could stretch it into a block?',
      tool: 'Select Extrude, click the rectangle region, pick New, type the depth, and accept.',
      explanation:
        'Extrude turns the 2D rectangle into a solid. Its depth value is the plate thickness (10 mm in the reference plate).',
    },
    expectation: {
      question: 'Why do we extrude a sketch?',
      choices: [
        {
          id: 'depth',
          label: 'To give the flat outline depth, making a solid',
          response:
            'Yes, that is the job of an Extrude: a flat profile in, a solid with thickness out.',
        },
        {
          id: 'copy',
          label: 'To make a copy of the sketch',
          response:
            'Extrude does not copy the sketch. It uses the outline as a template and adds depth to it.',
        },
        {
          id: 'visible',
          label: 'To make the outline visible in 3D',
          response:
            'The sketch is already visible. What changes is that the Extrude creates real material with thickness.',
        },
      ],
    },
    completion: 'learner-reported',
    askPrompts: ['Why not just draw a box?', ...evidencePrompts],
  },
  {
    id: 'plate-hole-sketch',
    title: 'Sketch where the holes go',
    objective: 'Mark the hole positions and size on the plate.',
    instruction:
      'Start a sketch on the plate’s top face and draw two circles (reference plate: 8 mm diameter, centers on the width centerline, 10 mm in from each short end). Finish the sketch.',
    why: 'A second sketch can say where something happens on the solid. Circles here mark the position and size of each hole. Sketching alone does not remove any material.',
    hints: {
      conceptual:
        'Where on the plate should each hole be, and how big? A sketch can record both.',
      tool: 'Sketch on the top face, draw a circle, give it a diameter, and position its center with dimensions from the edges.',
      explanation:
        'The two circles are plans for the holes. In the reference plate each is 8 mm across and 10 mm in from a short end, centered across the width.',
    },
    expectation: {
      question: 'After you draw the circles, is there material missing yet?',
      choices: [
        {
          id: 'holes-now',
          label: 'Yes, the holes are already cut',
          response:
            'Not yet. A sketch only describes a shape. A feature has to act on it before the solid changes.',
        },
        {
          id: 'plan-only',
          label: 'No, they are only a plan',
          response:
            'Correct about sketches: they mark where and how big. The next feature does the cutting.',
        },
      ],
    },
    completion: 'learner-reported',
    askPrompts: ['Why a new sketch for the holes?', ...evidencePrompts],
  },
  {
    id: 'plate-remove',
    title: 'Cut the holes with Extrude Remove',
    objective: 'Remove material through the plate using the circles.',
    instruction:
      'Extrude the circle sketch, choose Remove, and set the end to Through all so the holes pass through the full thickness.',
    why: 'A hole is missing material. Remove cuts the sketch shape out of the existing solid. Add or New would build material instead of taking it away.',
    vocabulary: [
      {
        id: 'remove',
        term: 'Remove',
        definition:
          'An Extrude option that cuts the profile out of existing solid material.',
      },
    ],
    hints: {
      conceptual:
        'Should the circles add material or take it away? What does a hole look like?',
      tool: 'Select Extrude, pick the circle regions, choose Remove, and set the end condition to Through all.',
      explanation:
        'Extrude with Remove subtracts the circular profile from the plate for the chosen depth. Through all makes sure it cuts all the way across.',
    },
    expectation: {
      question: 'Why use Remove instead of Add for holes?',
      choices: [
        {
          id: 'subtract',
          label: 'A hole is material taken away, so it must subtract',
          response:
            'That is the reasoning. Remove cuts the circle out of the plate; Add would put material there instead.',
        },
        {
          id: 'either',
          label: 'Add and Remove give the same result',
          response:
            'They are opposites. Add joins material into the solid; Remove cuts it out, which is what a hole needs.',
        },
        {
          id: 'faster',
          label: 'Remove is just faster',
          response:
            'Speed is not the reason. Remove is the operation that takes material away, and that is what a hole is.',
        },
      ],
    },
    completion: 'learner-reported',
    askPrompts: ['What does Through all mean?', ...evidencePrompts],
  },
  {
    id: 'plate-fillet',
    title: 'Round the top edges with a Fillet',
    objective: 'Soften the sharp outer top edges.',
    instruction:
      'Use Fillet on the outer top edges of the plate (reference plate: 2 mm radius).',
    why: 'A fillet rounds an edge, so corners are less sharp. It is the last feature, so turning it off brings the sharp edges back without changing the plate or its holes.',
    vocabulary: [
      {
        id: 'fillet',
        term: 'Fillet',
        definition: 'A feature that rounds a sharp edge with a chosen radius.',
      },
      {
        id: 'suppress',
        term: 'Suppress',
        definition:
          'Temporarily turn a feature off without deleting it. The feature stays in the tree and can be turned back on.',
      },
    ],
    hints: {
      conceptual:
        'Which edges would feel sharp when you handle the plate? What softens them?',
      tool: 'Select Fillet, click the outer top edges, set the radius, and accept.',
      explanation:
        'The fillet rounds the chosen edges by its radius (2 mm in the reference plate). Because it comes last, suppressing it only removes the rounding.',
    },
    expectation: {
      question: 'What happens to the plate if the Fillet is suppressed?',
      choices: [
        {
          id: 'sharp',
          label: 'The edges go back to sharp; the rest stays',
          response:
            'That is the idea. The fillet only rounds edges, and nothing is built on it, so the plate and holes remain.',
        },
        {
          id: 'plate-gone',
          label: 'The whole plate disappears',
          response:
            'The plate comes from the earlier Extrude, so it stays. Suppression turns off only the feature you choose.',
        },
        {
          id: 'holes-gone',
          label: 'The holes disappear',
          response:
            'The holes come from Extrude Remove, which is earlier in the tree. Suppressing the fillet does not touch it.',
        },
      ],
    },
    completion: 'learner-reported',
    askPrompts: ['What does suppress mean?', ...evidencePrompts],
  },
  {
    id: 'plate-review',
    title: 'Read the feature tree as a story',
    objective: 'See how the five operations build on one another.',
    instruction:
      'Look at your feature tree. The reference order is Sketch 1 → Extrude 1 → Sketch 2 → Extrude 2 → Fillet 1. Compare it with yours.',
    why: 'Each feature uses what came before: a sketch feeds an Extrude, and the last features refine the shape. Knowing the order tells you which feature to edit for a change.',
    hints: {
      conceptual:
        'Which feature is responsible for each thing you can see on the plate?',
      tool: 'Open the feature list and click each feature to see what it controls.',
      explanation:
        'Outline: Sketch 1. Thickness: Extrude 1. Hole positions: Sketch 2. Holes cut: Extrude 2. Rounded edges: Fillet 1.',
    },
    expectation: {
      question: 'Which feature would you edit to change the plate’s thickness?',
      choices: [
        {
          id: 'extrude-one',
          label: 'The first Extrude (its depth)',
          response:
            'Yes, thickness is the depth of that Extrude. Editing it regenerates everything after it.',
        },
        {
          id: 'sketch-one',
          label: 'The first sketch',
          response:
            'The sketch controls the outline (length and width), not the depth. Thickness lives in the Extrude.',
        },
        {
          id: 'fillet',
          label: 'The Fillet',
          response:
            'The Fillet only rounds edges. It does not set how thick the plate is.',
        },
      ],
    },
    completion: 'learner-reported',
    askPrompts: [
      'What does my current feature tree show?',
      'Is the fillet in my model suppressed?',
      'Explain this at an expert level.',
    ],
  },
];

export const mountingPlate: Lesson = {
  id: 'mounting-plate',
  title: 'Mounting plate',
  summary:
    'Follow one plate from sketch to fillet and see how each CAD operation builds on the last. You model in Onshape; Forge explains why.',
  learningObjectives: [
    'Explain how a sketch defines a profile.',
    'Explain why Extrude creates thickness.',
    'Explain why Remove cuts holes.',
    'Explain what a Fillet does and what suppressing it changes.',
  ],
  experienceRange: ['beginner', 'some-experience', 'comfortable'],
  prerequisites: [
    'The dimensions in this lesson belong to a reference plate. Forge does not measure your model.',
    'Forge reads your open Part Studio only when you ask the tutor about it.',
  ],
  progressNote:
    'Forge does not check your model in this lesson. “Mark step done” records your own progress. Ask Forge what it can read in your Part Studio.',
  completionMessage:
    'You followed one plate from outline to rounded edges and saw what each operation does. Sizes in this lesson were reference values that Forge did not measure.',
  followUpChallenge: {
    title: 'A question to take with you',
    prompt:
      'If the plate needed to be thicker, which one feature would you change, and what would stay the same?',
  },
  steps,
};
