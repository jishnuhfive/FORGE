import { useSyncExternalStore } from 'react';
import { Dialog } from '@forge/design-system';
import {
  developerToolsSnapshot,
  setDeveloperToolsOpen,
  subscribeDeveloperTools,
} from '../developerAccess';
import LaunchDiagnostic from './LaunchDiagnostic';
import SelectionDiagnostic from './SelectionDiagnostic';

export default function DeveloperTools() {
  const open = useSyncExternalStore(
    subscribeDeveloperTools,
    developerToolsSnapshot,
  );
  return (
    <Dialog
      open={open}
      onOpenChange={setDeveloperToolsOpen}
      title="Developer tools"
      description="Development-only sanitized diagnostics. No raw CAD or credentials."
    >
      <LaunchDiagnostic />
      <SelectionDiagnostic />
    </Dialog>
  );
}
