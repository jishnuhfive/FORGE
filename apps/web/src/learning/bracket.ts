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
  transfer: {
    id: 'single-profile-bracket',
    title: 'Transfer challenge: one profile, one extrusion',
    summary:
      'You built the bracket from a base and a separate leg. Now build an L-shaped bracket a different way, with less guidance. Forge still only checks what it can read.',
    constraints: [
      'Start from one closed L-shaped outline in a single sketch.',
      'Use exactly one extrusion to turn it into a solid.',
      'Any plane, size and feature names are fine.',
      'Leave out fillets and chamfers for now, so Forge can read the result clearly.',
    ],
    completionMessage:
      'You built the same kind of part a second way, using one profile and one extrusion. Forge verified what it could read; sizes, fit and strength are still yours to confirm.',
    steps: [
      {
        id: 'transfer-single-profile',
        check: 'deterministic',
        title: 'Build the L from one profile',
        objective: 'Make an L-shaped solid from one profile and one extrusion.',
        instruction:
          'Draw one closed L-shaped outline in a single sketch, then extrude it once as a new solid. Press Check my step when you are ready.',
        why: 'Choosing between one profile and several extrusions is a design decision. One profile keeps the whole shape in a single sketch you can edit later, at the cost of a more complex outline.',
        vocabulary: [
          {
            id: 'profile',
            term: 'Profile',
            definition:
              'The outline of a shape in a sketch. A closed profile can be given depth.',
          },
        ],
        hints: {
          conceptual:
            'Which single outline, if given thickness, would already have both the base and the upright?',
          tool: 'Sketch the L with the Line tool so its ends connect, finish the sketch, then use Extrude once with the New option.',
          explanation:
            'Draw an L as one closed outline: six connected sides. Finish the sketch and extrude it once as a new solid. Forge expects exactly one active extrusion and a body with more faces than a plain block; it cannot see your dimensions.',
        },
        completion: 'learner-reported',
        investigations: [
          {
            id: 'extra-extrusion',
            family: 'constraint',
            trigger: {
              requirementId: 'transfer.one_extrusion',
              statuses: ['FAIL'],
              reasons: ['constraint_not_met'],
            },
            prediction: {
              question:
                'Which approach keeps the whole shape to one extrusion?',
              choices: [
                {
                  id: 'one-outline',
                  label: 'Draw the whole L as one closed outline',
                  response:
                    'That is one possibility. Compare it with what Forge can actually observe below.',
                },
                {
                  id: 'base-and-leg',
                  label: 'Extrude the base, then extrude a leg',
                  response:
                    'That is one possibility. Compare it with what Forge can actually observe below.',
                },
              ],
            },
            possibleExplanation:
              'One possibility is that part of the shape was built with a separate extrusion. This challenge asks for the whole L from a single profile.',
            tryNext:
              'Look for a second active extrusion. Could that portion have been part of the original outline instead?',
            shortTryNext:
              'Look for a second active extrusion that the outline could absorb.',
          },
          {
            id: 'no-single-extrusion',
            family: 'missing-feature',
            trigger: {
              requirementId: 'transfer.one_extrusion',
              statuses: ['FAIL'],
              reasons: ['missing', 'suppressed'],
            },
            prediction: {
              question: 'What do you think the next feature should do?',
              choices: [
                {
                  id: 'make-3d',
                  label: 'Turn the closed outline into a 3D feature',
                  response:
                    'That is one possibility. Compare it with what Forge can actually observe below.',
                },
                {
                  id: 'more-sketch',
                  label: 'Add more sketch geometry',
                  response:
                    'That is one possibility. Compare it with what Forge can actually observe below.',
                },
              ],
            },
            possibleExplanation:
              'One possibility is that the outline has not been extruded yet, or that its extrusion is suppressed.',
            tryNext:
              'Look for an active Extrude after your sketch and check whether it is suppressed.',
            shortTryNext: 'Check for one active Extrude after the sketch.',
          },
          {
            id: 'plain-block',
            family: 'missing-feature',
            trigger: {
              requirementId: 'transfer.l_profile',
              statuses: ['FAIL'],
              reasons: ['missing'],
            },
            prediction: {
              question:
                'What would a plain rectangle extruded once look like to Forge compared with an L?',
              choices: [
                {
                  id: 'fewer-faces',
                  label: 'It would show fewer faces than an L',
                  response:
                    'That is one possibility. Compare it with what Forge can actually observe below.',
                },
                {
                  id: 'same-faces',
                  label: 'It would show the same faces',
                  response:
                    'That is one possibility. Compare it with what Forge can actually observe below.',
                },
              ],
            },
            possibleExplanation:
              'One possibility is that the outline is still a plain rectangle. Forge only sees face counts, not the outline’s shape.',
            tryNext:
              'Think about what outline would give the body more faces than a block while still being one profile.',
            shortTryNext:
              'Think about an outline with more sides than a rectangle.',
          },
          {
            id: 'edge-treatment',
            family: 'ambiguous-evidence',
            trigger: {
              requirementId: 'transfer.l_profile',
              statuses: ['WARNING'],
              reasons: ['ambiguous_signal'],
            },
            prediction: {
              question:
                'Would the added faces still prove the outline is an L?',
              choices: [
                {
                  id: 'yes',
                  label: 'Yes, more faces always means an L outline',
                  response:
                    'That is one possibility. Compare it with what Forge can actually observe: a fillet or chamfer also adds faces.',
                },
                {
                  id: 'no',
                  label: 'No, a fillet or chamfer can add faces too',
                  response:
                    'That is one possibility, and it matches the ambiguity Forge sees here.',
                },
              ],
            },
            possibleExplanation:
              'Face count alone cannot separate an L-shaped outline from the faces that a fillet or chamfer adds.',
            tryNext:
              'Consider suppressing the fillet or chamfer, then check again.',
            shortTryNext:
              'Try suppressing the fillet or chamfer, then check again.',
          },
        ],
      },
    ],
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
      expectation: {
        question:
          'If you extrude the closed sketch as a new solid, what should Forge be able to see afterward?',
        choices: [
          {
            id: 'feature-and-body',
            label: 'An active extrude feature and a solid body',
            response:
              'That is one possibility, and it is what this step looks for. Press Check my step afterward to compare it with what Forge can actually observe.',
          },
          {
            id: 'sketch-only',
            label: 'Only the sketch, as before',
            response:
              'That is one possibility. An extrude adds its own feature to the list, so compare it with what Forge observes after you check.',
          },
          {
            id: 'renamed-sketch',
            label: 'The sketch, now with a different name',
            response:
              'That is one possibility. Forge never uses names as evidence, so compare it with what Forge observes after you check.',
          },
        ],
      },
      investigations: [
        {
          id: 'no-extrusion',
          family: 'missing-feature',
          trigger: {
            requirementId: 'extrude.exists',
            statuses: ['FAIL'],
            reasons: ['missing', 'suppressed'],
          },
          prediction: {
            question: 'What do you think the next feature should do?',
            choices: [
              {
                id: 'make-3d',
                label: 'Turn the closed sketch into a 3D feature',
                response:
                  'That is one possibility. Compare it with what Forge can actually observe below.',
              },
              {
                id: 'rename',
                label: 'Rename the sketch so Forge recognizes it',
                response:
                  'That is one possibility. Forge never uses names as evidence, so compare it with what Forge observes.',
              },
              {
                id: 'fillet',
                label: 'Round the sketch’s corners with a fillet',
                response:
                  'That is one possibility. A fillet acts on an existing shape, so compare it with what Forge observes.',
              },
            ],
          },
          possibleExplanation:
            'One possibility is that the sketch has not been turned into a 3D feature yet. This can also happen when an Extrude exists but is suppressed, which greys it out in the feature list.',
          tryNext:
            'Look in your feature list for an active Extrude after your sketch, and check whether it is suppressed.',
          shortTryNext: 'Check for an active Extrude after the sketch.',
        },
        {
          id: 'no-solid-body',
          family: 'missing-feature',
          trigger: {
            requirementId: 'body.solid',
            statuses: ['FAIL'],
            reasons: ['missing'],
          },
          prediction: {
            question:
              'Which of these could leave a model with a sketch but no solid body?',
            choices: [
              {
                id: 'never-extruded',
                label: 'An extrusion that was never created',
                response:
                  'That is one possibility. Compare it with what Forge can actually observe below.',
              },
              {
                id: 'suppressed',
                label: 'An extrusion that is suppressed',
                response:
                  'That is one possibility. Compare it with what Forge can actually observe below.',
              },
              {
                id: 'surface',
                label: 'An extrusion set to make a surface instead of a solid',
                response:
                  'That is one possibility. Compare it with what Forge can actually observe below.',
              },
            ],
          },
          possibleExplanation:
            'This can happen when no extrusion has created a solid yet, when an extrusion is suppressed, or when an extrusion was set to make a surface instead of a solid.',
          tryNext:
            'Check that your extrusion is active and that its type creates a new solid.',
          shortTryNext: 'Check that the extrusion is active and makes a solid.',
        },
      ],
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
      investigations: [
        {
          id: 'no-second-portion',
          family: 'missing-feature',
          trigger: {
            requirementId: 'bracket.second_portion',
            statuses: ['FAIL'],
            reasons: ['missing'],
          },
          prediction: {
            question:
              'What could add a second portion to the bracket while keeping one solid body?',
            choices: [
              {
                id: 'second-extrusion',
                label: 'A second extrusion that adds to the base',
                response:
                  'That is one possibility. Compare it with what Forge can actually observe below.',
              },
              {
                id: 'l-profile',
                label: 'One L-shaped profile extruded once',
                response:
                  'That is one possibility. Compare it with what Forge can actually observe below.',
              },
              {
                id: 'sketch-only',
                label: 'A new sketch with no extrusion',
                response:
                  'That is one possibility. A sketch alone adds no material, so compare it with what Forge can observe.',
              },
            ],
          },
          possibleExplanation:
            'One possibility is that the model is still a plain block so far. Forge reads feature types and face counts, not the bracket’s actual shape, so it cannot say how the geometry is arranged.',
          tryNext:
            'Think about what feature or profile would add a second portion while keeping one solid body.',
          shortTryNext:
            'Think about what would add a second portion to one solid body.',
        },
        {
          id: 'ambiguous-faces',
          family: 'ambiguous-evidence',
          trigger: {
            requirementId: 'bracket.second_portion',
            statuses: ['WARNING'],
            reasons: ['ambiguous_signal'],
          },
          prediction: {
            question:
              'Would the added faces still prove the bracket has a second portion?',
            choices: [
              {
                id: 'yes',
                label: 'Yes, more faces always means a second portion',
                response:
                  'That is one possibility. Compare it with what Forge can actually observe: a fillet or chamfer also adds faces.',
              },
              {
                id: 'no',
                label: 'No, a fillet or chamfer can add faces too',
                response:
                  'That is one possibility, and it matches the ambiguity Forge sees here: edge treatments also raise the face count.',
              },
            ],
          },
          possibleExplanation:
            'Face count alone cannot separate a second portion from the faces that a fillet or chamfer adds. While one is active, Forge cannot fully verify this step from the face count.',
          tryNext:
            'Consider suppressing the fillet or chamfer for now, then check again. You can turn it back on afterward.',
          shortTryNext:
            'Try suppressing the fillet or chamfer, then check again.',
        },
      ],
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
      investigations: [
        {
          id: 'few-mounting-faces',
          family: 'missing-feature',
          trigger: {
            requirementId: 'bracket.mounting_faces',
            statuses: ['FAIL'],
            reasons: ['missing'],
          },
          prediction: {
            question:
              'What would adding two simple through holes change about the body Forge reads?',
            choices: [
              {
                id: 'adds-faces',
                label: 'It adds faces to the body',
                response:
                  'That is one possibility, and it is the signal this step uses. Compare it with what Forge observes below.',
              },
              {
                id: 'nothing',
                label: 'It changes nothing Forge can read',
                response:
                  'That is one possibility. Compare it with what Forge can actually observe below.',
              },
              {
                id: 'new-body',
                label: 'It adds a new body',
                response:
                  'That is one possibility. Compare it with what Forge can actually observe below.',
              },
            ],
          },
          possibleExplanation:
            'One possibility is that the holes have not been cut yet, or that they are only sketched and not removed from the solid. Forge sees added faces only; it cannot see the holes themselves.',
          tryNext:
            'Check that the holes are cut through the bracket, not only sketched.',
          shortTryNext: 'Check that the holes are actually cut through.',
        },
      ],
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
