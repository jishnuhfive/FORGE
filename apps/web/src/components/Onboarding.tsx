import { Button, Dialog } from '@forge/design-system';

const steps = [
  [
    'Ask about the model',
    'Understand features, parts and the evidence Forge can inspect.',
  ],
  [
    'Review what is known',
    'Open Evidence for observations. Unknowns and unverified guidance stay explicit.',
  ],
  [
    'Stay in control',
    'Analysis starts only when you send. Sending shares your question, recent conversation and bounded CAD evidence with the configured AI service. Your CAD remains unchanged.',
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
      description="AI engineering inside Onshape. Understand your model with evidence you can review."
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
        Forge reads CAD and offers guidance. CAD changes and engineering
        validation are unavailable.
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
