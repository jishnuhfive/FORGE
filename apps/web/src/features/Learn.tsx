import { Badge, Button, Card, Panel, StatusBadge } from '@forge/design-system';
import { ArrowRight, BookOpen, Check, Eye, Lightbulb } from 'lucide-react';
import { useState } from 'react';

const lesson = [
  {
    title: 'Create the base sketch',
    instruction:
      'On the Top plane, sketch a centered rectangle for the mounting plate. Constrain it to the origin and add width and depth dimensions.',
    why: 'The sketch defines the primary mounting plate geometry and keeps the design parametric.',
    concept: 'Design intent',
    explanation:
      'Dimensions and constraints encode why geometry has its shape. A centered sketch preserves symmetry as the plate size changes.',
    action: 'Create and fully constrain one rectangular sketch.',
    hint: 'In Onshape: select Top → Sketch → Center point rectangle. Place its center at the origin, then add two dimensions.',
  },
  {
    title: 'Give the plate thickness',
    instruction:
      'Extrude the closed sketch into a solid mounting plate. Use a named thickness parameter rather than an unexplained fixed value.',
    why: 'A clear thickness parameter makes later manufacturing adjustments predictable.',
    concept: 'Parametric modeling',
    explanation:
      'A parameter is a deliberate control of the model. Naming it makes design changes easier to review.',
    action: 'Create one solid extrusion from the base sketch.',
    hint: 'Select the closed sketch region → Extrude → Solid. Set the depth to the plate thickness you intend to evaluate.',
  },
  {
    title: 'Locate the mounting holes',
    instruction:
      'Add a centered hole pattern. Confirm the hole spacing and sizes against the motor manufacturer’s drawing.',
    why: 'An accurately constrained pattern aligns the motor and limits avoidable assembly errors.',
    concept: 'Interface geometry',
    explanation:
      'Mating geometry must be based on verified component specifications. A motor family name alone is insufficient evidence.',
    action: 'Sketch and dimension a mounting-hole pattern.',
    hint: 'Create a sketch on the plate face. Use construction geometry for symmetry, then dimension the hole centers from a verified drawing.',
  },
  {
    title: 'Review the design',
    instruction:
      'Inspect dimensions, printer fit and the hardware interfaces. Record any check that lacks evidence as UNVERIFIED.',
    why: 'A model that looks plausible can still violate a requirement.',
    concept: 'Evidence-based validation',
    explanation:
      'Separate measured geometry from assumptions. Each result needs inputs, units and evidence before it can support a PASS.',
    action: 'Review the model and list unresolved checks.',
    hint: 'Measure the plate envelope and hole positions. Compare them to the manufacturing profile and motor drawing.',
  },
];
export function Learn() {
  const [step, setStep] = useState(0);
  const [show, setShow] = useState(false);
  const [explain, setExplain] = useState(false);
  const [check, setCheck] = useState(false);
  const [finished, setFinished] = useState(false);
  const current = lesson[step] ?? lesson[0];
  if (!current) return null;
  return (
    <div className="feature">
      <div className="section-kicker">
        <span>LEARN WORKSPACE</span>
        <Badge>Local lesson</Badge>
      </div>
      <div className="feature-heading">
        <span className="eyebrow">CAD / FOUNDATIONS</span>
        <h1>NEMA 17 Motor Mount</h1>
        <p>
          Build understanding alongside your model, one deliberate step at a
          time.
        </p>
      </div>
      <div className="lesson-progress">
        <BookOpen size={16} aria-hidden="true" />
        <span>
          Reading progress · Step {step + 1} of {lesson.length}
        </span>
        <span className="mono muted">
          {Math.round(((step + 1) / lesson.length) * 100)}%
        </span>
      </div>
      <progress
        aria-label="Lesson reading progress"
        max={lesson.length}
        value={step + 1}
      />
      <Card className="lesson-card">
        <span className="eyebrow">STEP 0{step + 1}</span>
        <h2>{current.title}</h2>
        <p>{current.instruction}</p>
        <div className="lesson-why">
          <Lightbulb size={18} aria-hidden="true" />
          <div>
            <h3>Why this matters</h3>
            <p>{current.why}</p>
          </div>
        </div>
        <div className="chip-list">
          <Badge>{current.concept}</Badge>
        </div>
      </Card>
      <Panel title="Expected CAD action">
        <p>{current.action}</p>
      </Panel>
      <div className="action-bar">
        <Button onClick={() => setShow(!show)} aria-expanded={show}>
          <Eye size={14} aria-hidden="true" />
          Show me
        </Button>
        <Button onClick={() => setExplain(!explain)} aria-expanded={explain}>
          Explain why
        </Button>
        <Button onClick={() => setCheck(true)}>
          <Check size={14} aria-hidden="true" />
          Check my work
        </Button>
      </div>
      {show && (
        <Panel title="Action guide">
          <p>{current.hint}</p>
        </Panel>
      )}
      {explain && (
        <Panel title={current.concept}>
          <p>{current.explanation}</p>
        </Panel>
      )}
      {check && (
        <div className="notice" role="status">
          <StatusBadge status="unverified" />
          <p>No CAD inspection is available. Your work has not been checked.</p>
        </div>
      )}
      <div className="action-bar lesson-next">
        {step > 0 && (
          <Button
            onClick={() => {
              setStep(step - 1);
              setShow(false);
              setExplain(false);
              setCheck(false);
              setFinished(false);
            }}
          >
            Previous step
          </Button>
        )}
        <Button
          variant="primary"
          disabled={finished}
          onClick={() => {
            if (step < lesson.length - 1) setStep(step + 1);
            else setFinished(true);
            setShow(false);
            setExplain(false);
            setCheck(false);
          }}
        >
          {step === lesson.length - 1 ? 'Finish reading' : 'Next step'}
          <ArrowRight size={14} aria-hidden="true" />
        </Button>
      </div>
      {finished && (
        <p className="notice" role="status">
          Lesson reading complete. CAD work remains unverified.
        </p>
      )}
      <p className="local-notice">
        Authored lesson preview. No AI tutoring, CAD actions or automatic work
        checks run.
      </p>
    </div>
  );
}
