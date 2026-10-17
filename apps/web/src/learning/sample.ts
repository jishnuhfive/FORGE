import type { Lesson } from './lesson';

export const sketchToSolid: Lesson = {
  id: 'sketch-to-solid',
  title: 'Sketch to solid',
  summary:
    'Explore how a flat profile becomes a solid part, and why each operation belongs in the process.',
  learningObjectives: [
    'Explain what a sketch contributes to a model.',
    'Recognize when an extrusion is a useful choice.',
    'Distinguish a feature from the solid body it creates.',
  ],
  experienceRange: ['beginner', 'some-experience', 'comfortable'],
  prerequisites: [
    'No model is required. You can think through the example or try the tools in your own practice Part Studio.',
  ],
  completionMessage:
    'You worked through the connection between a 2D profile, an extrusion and a solid body. Use that sequence to explain your next modeling choice.',
  followUpChallenge: {
    title: 'A question to take with you',
    prompt:
      'Imagine a part whose cross-section changes along its length. Why might one straight extrusion be insufficient?',
  },
  steps: [
    {
      id: 'sketch',
      title: 'Begin with a profile',
      objective: 'Understand the role of a 2D sketch.',
      instruction:
        'Imagine a simple rectangular block. Choose a plane on which you could sketch its rectangular profile. If you are practicing in Onshape, create a closed rectangle on that plane.',
      why: 'A sketch describes a 2D profile. Choosing a clear view of the profile makes it easier to control the shape before adding depth.',
      vocabulary: [
        {
          id: 'sketch',
          term: 'Sketch',
          definition: 'A 2D profile used as the basis for many 3D features.',
        },
        {
          id: 'plane',
          term: 'Plane',
          definition:
            'A flat reference surface on which you can draw a sketch.',
        },
        {
          id: 'constraint',
          term: 'Constraint',
          definition:
            'A rule that controls sketch geometry or relationships, such as keeping two lines perpendicular.',
        },
      ],
      hints: {
        conceptual:
          'Which flat view shows the outline of the block most clearly? Think about the shape before adding depth.',
        tool: 'Use Sketch on a reference plane, then the Rectangle tool to describe the profile.',
        explanation:
          'For this example, choose the Top plane and start a sketch. Draw one rectangle with four connected sides. Its enclosed region describes the block’s cross-section; depth will come from a later operation. Dimensions and constraints can control the profile as a design develops.',
      },
      completion: 'learner-reported',
    },
    {
      id: 'extrude',
      title: 'Turn the profile into depth',
      objective: 'Connect a constant cross-section to an extrusion.',
      instruction:
        'Picture the same rectangle extending straight through a distance. If you are practicing, finish the sketch and use Extrude with a closed sketch region to create a new solid. Choose your own practice depth.',
      why: 'Extrusion is useful when a shape keeps the same cross-section through a distance. The sketch controls the outline and the extrusion controls its depth.',
      vocabulary: [
        {
          id: 'extrude',
          term: 'Extrude',
          definition:
            'Extends a sketch region through a distance to create or modify 3D geometry.',
        },
        {
          id: 'cross-section',
          term: 'Cross-section',
          definition:
            'The flat shape you would see if you sliced through an object.',
        },
      ],
      hints: {
        conceptual:
          'Would the outline change as you move from one end of this block to the other?',
        tool: 'Use Extrude with the closed rectangle region, choosing Solid and New for a separate solid part.',
        explanation:
          'Finish the sketch. In Extrude, choose Solid, select the enclosed rectangular region, and choose New. Set a practice depth and inspect the preview before accepting it yourself. The region supplies the cross-section and the depth supplies the distance. Forge does not choose or check dimensions here.',
      },
      completion: 'learner-reported',
    },
    {
      id: 'solid',
      title: 'Separate the operation from the result',
      objective: 'Distinguish a feature from a solid body.',
      instruction:
        'Explain in your own words what the sketch defined, what Extrude did, and what the resulting solid body represents. If practicing, compare the feature list with the Parts list.',
      why: 'A feature records a modeling operation. A solid body is a volume of geometry produced by those operations. Keeping the two ideas separate helps you reason about later changes.',
      vocabulary: [
        {
          id: 'feature',
          term: 'Feature',
          definition:
            'An operation in the model history that creates or changes geometry.',
        },
        {
          id: 'solid-body',
          term: 'Solid body',
          definition:
            'A closed volume of 3D geometry, rather than just a surface or outline.',
        },
      ],
      hints: {
        conceptual:
          'Which part of the process is an action, and which is the object left behind?',
        tool: 'Compare Sketch and Extrude in the feature list with the resulting part in the Parts list.',
        explanation:
          'The sketch supplies the 2D profile. Extrude is the feature that extends it through a distance. The resulting solid body is the 3D volume. Many features can contribute to one body, so counting features does not tell you how many bodies exist. Reading this example does not establish that your own model is correct.',
      },
      completion: 'learner-reported',
    },
  ],
};
