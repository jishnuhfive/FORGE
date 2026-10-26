import { Button, Dialog } from '@forge/design-system';

const steps = [
  [
    'Design it',
    'Ask how to model something and get clear, step-by-step Onshape instructions you follow yourself.',
  ],
  [
    'Modify it',
    'Describe a supported change to your model. Review the exact plan, approve it, and Forge verifies the result.',
  ],
  [
    'Understand it',
    'Learn with guided lessons, predictions and hints, and ask Forge when you are stuck.',
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
      description="Design it. Modify it. Understand it."
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
        Forge only changes your CAD after you approve an exact plan, and checks
        the result afterwards. Engineering validation is not a certification.
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
