import {
  Badge,
  EmptyState,
  StatusBadge,
  ValidationRow,
} from '@forge/design-system';
import { ShieldCheck } from 'lucide-react';
import type { ValidationStatus } from '@forge/design-system';
import type { ValidationCheck } from '../lib/types';

export function ValidationReport({ checks }: { checks: ValidationCheck[] }) {
  const statuses: ValidationStatus[] = [
    'pass',
    'warning',
    'fail',
    'unverified',
  ];
  return (
    <div className="feature">
      <div className="section-kicker">
        <span>04 / VALIDATION</span>
        <Badge tone="accent">Synthetic report</Badge>
      </div>
      <div className="feature-heading">
        <h1>Evidence, with limits.</h1>
        <p>
          Every supported constraint gets a result. Missing evidence stays
          unverified.
        </p>
      </div>
      {checks.length === 0 ? (
        <EmptyState
          title="No validation results"
          description="Results will appear after supported checks run against real CAD evidence."
          icon={<ShieldCheck />}
        />
      ) : (
        <>
          <div className="validation-summary">
            {statuses.map((status) => (
              <StatusBadge
                key={status}
                status={status}
                label={`${checks.filter((check) => check.status === status).length} ${status === 'pass' ? 'Pass' : status === 'warning' ? 'Warning' : status === 'fail' ? 'Fail' : 'Unverified'}`}
              />
            ))}
          </div>
          <div className="notice">
            Mock evidence only. These values do not validate a real design.
          </div>
          <div className="validation-list">
            {checks.map((check) => (
              <ValidationRow key={check.id} {...check} />
            ))}
          </div>
          <p className="local-notice">
            UNVERIFIED means no applicable check or sufficient evidence. It does
            not mean a constraint passed. Strength and load safety have not been
            evaluated.
          </p>
        </>
      )}
    </div>
  );
}
