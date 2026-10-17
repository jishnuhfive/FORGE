import type { Lesson } from './lesson';

// Authored for what Forge can actually verify (see docs/PHASE_8_LESSON_SPEC.md).
// Step ids are shared with the backend requirement sets; the server owns them.
export const mountingBracket: Lesson = {
  id: 'mounting-bracket',
  title: 'Mounting bracket',
  summary:
    'Build a simple L-shaped bracket yourself in Onshape. Forge explains why each operation fits and can check what it is able to read from your model.',
  learningObjectives: [
    'Build a solid part from a sketched profile.',
    'Explain why extrusion fits a constant cross-section.',
    'Add a second portion and mounting holes to a bracket.',
    'Tell what a model check can and cannot prove.',
  ],
  experienceRange: ['beginner', 'some-experience', 'comfortable'],
  prerequisites: [
    'Open a Part Studio in Onshape. You do the modeling; Forge only reads the model when you ask it to check a step.',
    'You should be able to start a sketch and draw a rectangle.',
  ],
  completionMessage:
    'You built a bracket by choosing each operation for a reason. Forge verified the steps it could read, and told you which things it could not check.',
  followUpChallenge: {
    title: 'A question to take with you',
    prompt:
      'Forge could see that your bracket had a solid body and added faces, but not its dimensions. What would you measure yourself before printing it?',
  },
  steps: [
    {
      id: 'base-sketch',
      check: 'deterministic',
      title: 'Draw the base profile',
      objective: 'Sketch the outline of the bracket’s foot.',
      instruction:
        'In your Part Studio, start a sketch on a plane and draw a closed rectangle for the base of the bracket. Finish the sketch.',
      why: 'A sketch describes the 2D outline of a shape. Starting from a profile is the simplest way to describe a part whose cross-section stays the same through its thickness.',
      vocabulary: [
        {
          id: 'sketch',
          term: 'Sketch',
          definition: 'A 2D profile used as the basis for many 3D features.',
        },
        {
          id: 'closed-profile',
          term: 'Closed profile',
          definition:
            'An outline whose ends all connect, so it encloses a region that can be given depth.',
        },
      ],
      hints: {
        conceptual:
          'What flat outline would the foot of your bracket have if you looked straight down on it?',
        tool: 'Choose a plane, select Sketch, then use the Corner rectangle tool and finish the sketch.',
        explanation:
          'Pick any reference plane and start a sketch. Draw one rectangle with four connected sides, then finish the sketch. Forge can see that a sketch exists. It cannot see the sketch’s shape, size or plane.',
      },
      completion: 'learner-reported',
    },
    {
      id: 'base-solid',
      check: 'deterministic',
      title: 'Turn the profile into a solid',
      objective: 'Give the profile thickness.',
      instruction:
        'Extrude the closed sketch region into a new solid. Choose a thickness you think suits a small bracket.',
      why: 'An extrusion is appropriate because this portion of the bracket keeps the same cross-section through its thickness. The sketch controls the outline and the extrusion controls the depth.',
      vocabulary: [
        {
          id: 'extrude',
          term: 'Extrude',
          definition:
            'Extends a sketch region through a distance to create or change 3D geometry.',
        },
        {
          id: 'solid-body',
          term: 'Solid body',
          definition:
            'A closed 3D shape with volume, as opposed to a sketch or a surface.',
        },
      ],
      hints: {
        conceptual: 'Which feature turns a closed 2D profile into a 3D solid?',
        tool: 'Select the sketch region, choose Extrude, set the type to New, and enter a depth.',
        explanation:
          'Select the closed rectangle, open Extrude, choose a New solid and set a depth. Forge can see an extrude feature and a solid body. It cannot read your thickness value or its units.',
      },
      completion: 'learner-reported',
    },
    {
      id: 'second-portion',
      check: 'deterministic',
      title: 'Add the bracket’s leg',
      objective: 'Make the bracket L-shaped.',
      instruction:
        'Add a vertical leg to one edge of the base. You can sketch the leg on a face and extrude it as an add, or you can start over with one L-shaped profile and extrude it once.',
      why: 'The leg also keeps one cross-section along its width, so a second extrusion (or one L-shaped profile) fits. A plain block cannot mount against a second surface.',
      vocabulary: [
        {
          id: 'add',
          term: 'Add',
          definition:
            'An extrude option that merges new material into an existing solid.',
        },
      ],
      hints: {
        conceptual:
          'Which surface will the bracket mount against, and what shape of material do you need beside the base?',
        tool: 'Sketch a rectangle on an end face of the base, then use Extrude with the Add option. Or draw one L-shaped outline in a single sketch.',
        explanation:
          'Either approach is fine. Two extrusions build the base and leg separately. One L-shaped profile builds both at once. Forge accepts either when it can see a second extrusion or a body with more faces than a plain block. It cannot see the leg’s size or direction.',
      },
      completion: 'learner-reported',
    },
    {
      id: 'mounting-holes',
      check: 'deterministic',
      title: 'Add two mounting holes',
      objective: 'Give the bracket two places to attach.',
      instruction:
        'Add two simple through holes in the mounting face, either with the Hole tool or by sketching circles and using Extrude with Remove.',
      why: 'A hole is material removed through a constant depth, so a remove-extrude or a Hole feature both fit. Holes are what let the bracket attach to something.',
      vocabulary: [
        {
          id: 'remove',
          term: 'Remove',
          definition:
            'An extrude option that cuts material away from an existing solid.',
        },
      ],
      hints: {
        conceptual:
          'Where will the fasteners go, and how far through the material must the holes reach?',
        tool: 'Sketch two circles on the mounting face, then Extrude with Remove through all, or use the Hole tool.',
        explanation:
          'Add exactly two simple through holes. Forge only sees that the body gained faces beyond a plain L; it cannot tell holes from other features, or see their size or position.',
      },
      completion: 'learner-reported',
    },
    {
      id: 'review',
      title: 'Review what is and is not known',
      objective:
        'Separate what Forge verified from what you still need to check.',
      instruction:
        'Look at your bracket and list what you would still measure or test: sizes, fit, strength and how you will make it.',
      why: 'A model can have the right kinds of features and still be the wrong size. Separating checked facts from assumptions is part of engineering.',
      hints: {
        conceptual:
          'Which of your design decisions has nothing yet confirming it?',
        tool: 'Use Onshape’s Measure tool and a hardware drawing to compare sizes with your plan.',
        explanation:
          'Forge could not read dimensions, units, hole positions, mass, fit or strength. Those remain yours to confirm.',
      },
      completion: 'learner-reported',
    },
  ],
};
