import { Button, Dialog } from '@forge/design-system';

const steps = [
  ['Start with the function', 'Describe what the design must accomplish.'],
  [
    'Define the requirements',
    'Forge will convert the goal into engineering requirements.',
  ],
  [
    'Review before building',
    'Review the proposed design plan and its assumptions.',
  ],
  [
    'Build inside your workspace',
    'Forge will eventually build directly inside Onshape.',
  ],
  [
    'Know what is verified',
    'Supported constraints will be checked, with anything else reported as UNVERIFIED.',
  ],
];
export function Onboarding({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  return (
    <Dialog
      open={open}
      onOpenChange={(value) => {
        if (!value) onClose();
      }}
      title="Welcome to Forge"
      description="AI engineering inside Onshape. A deliberate workflow, from requirements to evidence."
    >
      <ol className="onboarding-steps">
        {steps.map(([title, description], i) => (
          <li key={title}>
            <span className="step-number" aria-hidden="true">
              {i + 1}
            </span>
            <div>
              <strong>{title}</strong>
              <p>{description}</p>
            </div>
          </li>
        ))}
      </ol>
      <div className="notice">
        Phase 2 connects your Onshape account. Engineering workflows remain
        interface previews; no OpenAI calls run and no CAD is modified.
      </div>
      <div className="action-bar">
        <Button variant="primary" onClick={onClose}>
          Open workspace
        </Button>
        <Button variant="ghost" onClick={onClose}>
          Skip introduction
        </Button>
      </div>
    </Dialog>
  );
}
