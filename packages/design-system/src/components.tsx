import { useRef } from 'react';
import type { CSSProperties } from 'react';
import { GlassSurface } from './glass';
import type {
  ButtonHTMLAttributes,
  ComponentPropsWithRef,
  HTMLAttributes,
  InputHTMLAttributes,
  ReactNode,
} from 'react';
import * as DialogPrimitive from '@radix-ui/react-dialog';
import * as TabsPrimitive from '@radix-ui/react-tabs';
import * as TooltipPrimitive from '@radix-ui/react-tooltip';
import * as DropdownPrimitive from '@radix-ui/react-dropdown-menu';
import * as ToastPrimitive from '@radix-ui/react-toast';

export function Button({
  variant = 'secondary',
  className = '',
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
}) {
  return (
    <button
      type="button"
      className={`button button--${variant} ${className}`}
      {...props}
    />
  );
}

export function Tooltip({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <TooltipPrimitive.Root>
      <TooltipPrimitive.Trigger asChild>{children}</TooltipPrimitive.Trigger>
      <TooltipPrimitive.Portal>
        <TooltipPrimitive.Content className="tooltip" sideOffset={6}>
          {label}
          <TooltipPrimitive.Arrow className="tooltip-arrow" />
        </TooltipPrimitive.Content>
      </TooltipPrimitive.Portal>
    </TooltipPrimitive.Root>
  );
}
export const TooltipProvider = TooltipPrimitive.Provider;

export function IconButton({
  label,
  children,
  ...props
}: Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'aria-label'> & {
  label: string;
}) {
  return (
    <Tooltip label={label}>
      <button
        type="button"
        className="icon-button"
        aria-label={label}
        {...props}
      >
        {children}
      </button>
    </Tooltip>
  );
}

export function Input({
  className = '',
  ...props
}: InputHTMLAttributes<HTMLInputElement>) {
  return <input className={`input ${className}`} {...props} />;
}
export function Textarea({
  className = '',
  ...props
}: ComponentPropsWithRef<'textarea'>) {
  return <textarea className={`textarea ${className}`} {...props} />;
}
export function Card({
  className = '',
  ...props
}: HTMLAttributes<HTMLDivElement>) {
  return <div className={`card ${className}`} {...props} />;
}
export function Panel({
  title,
  children,
  action,
}: {
  title: string;
  children: ReactNode;
  action?: ReactNode;
}) {
  return (
    <section className="panel">
      <div className="panel-heading">
        <h3>{title}</h3>
        {action}
      </div>
      {children}
    </section>
  );
}
export function Badge({
  children,
  tone = 'neutral',
}: {
  children: ReactNode;
  tone?: 'neutral' | 'accent';
}) {
  return <span className={`badge badge--${tone}`}>{children}</span>;
}

export type ValidationStatus = 'pass' | 'warning' | 'fail' | 'unverified';
export type ProgressStatus =
  'pending' | 'active' | 'complete' | 'warning' | 'failed' | 'cancelled';
const statusSymbols = {
  pass: '✓',
  warning: '!',
  fail: '×',
  unverified: '?',
  pending: '○',
  active: '◉',
  complete: '✓',
  failed: '×',
  cancelled: '−',
};
export function StatusBadge({
  status,
  label,
}: {
  status: ValidationStatus | ProgressStatus;
  label?: string;
}) {
  return (
    <span className={`status-badge status--${status}`}>
      <span aria-hidden="true" className="status-symbol">
        {statusSymbols[status]}
      </span>
      {label ?? status.toUpperCase()}
    </span>
  );
}

export function Tabs({
  label,
  value,
  onValueChange,
  items,
}: {
  label: string;
  value: string;
  onValueChange: (value: string) => void;
  items: { id: string; label: string; icon?: ReactNode; content: ReactNode }[];
}) {
  return (
    <TabsPrimitive.Root
      value={value}
      onValueChange={onValueChange}
      className="tabs-root"
    >
      <TabsPrimitive.List asChild aria-label={label}>
        <GlassSurface
          className="tabs-list"
          style={
            {
              '--selected-index': Math.max(
                0,
                items.findIndex((item) => item.id === value),
              ),
            } as CSSProperties
          }
        >
          <span className="tabs-indicator" aria-hidden="true" />
          {items.map((item) => (
            <TabsPrimitive.Trigger
              className="tab"
              key={item.id}
              value={item.id}
            >
              {item.icon}
              {item.label}
            </TabsPrimitive.Trigger>
          ))}
        </GlassSurface>
      </TabsPrimitive.List>
      {items.map((item) => (
        <TabsPrimitive.Content
          className="tab-content"
          key={item.id}
          value={item.id}
        >
          {item.content}
        </TabsPrimitive.Content>
      ))}
    </TabsPrimitive.Root>
  );
}

export function Dialog({
  open,
  onOpenChange,
  title,
  description,
  children,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: string;
  children: ReactNode;
}) {
  const opener = useRef<HTMLElement | null>(null);
  return (
    <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="dialog-overlay" />
        <DialogPrimitive.Content
          className="dialog-content"
          onOpenAutoFocus={() => {
            if (document.activeElement instanceof HTMLElement)
              opener.current = document.activeElement;
          }}
          onCloseAutoFocus={(event) => {
            event.preventDefault();
            if (opener.current?.isConnected) opener.current.focus();
          }}
        >
          <div className="dialog-heading">
            <DialogPrimitive.Title>{title}</DialogPrimitive.Title>
            <DialogPrimitive.Close
              className="icon-button"
              aria-label="Close dialog"
            >
              ×
            </DialogPrimitive.Close>
          </div>
          <DialogPrimitive.Description className="dialog-description">
            {description}
          </DialogPrimitive.Description>
          {children}
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}

export function Dropdown({
  label,
  children,
  items,
}: {
  label: string;
  children: ReactNode;
  items: { label: string; onSelect: () => void; disabled?: boolean }[];
}) {
  const trigger = useRef<HTMLButtonElement>(null);
  const pendingAction = useRef<(() => void) | null>(null);
  return (
    <DropdownPrimitive.Root>
      <DropdownPrimitive.Trigger asChild>
        <button
          ref={trigger}
          type="button"
          className="icon-button"
          aria-label={label}
        >
          {children}
        </button>
      </DropdownPrimitive.Trigger>
      <DropdownPrimitive.Portal>
        <DropdownPrimitive.Content
          className="dropdown glass"
          sideOffset={6}
          align="end"
          onCloseAutoFocus={(event) => {
            event.preventDefault();
            trigger.current?.focus();
            // A dialog must open after menu focus is restored, so its opener survives.
            const action = pendingAction.current;
            pendingAction.current = null;
            action?.();
          }}
        >
          {items.map((item) => (
            <DropdownPrimitive.Item
              key={item.label}
              className="dropdown-item"
              onSelect={() => {
                pendingAction.current = item.onSelect;
              }}
              disabled={item.disabled}
            >
              {item.label}
            </DropdownPrimitive.Item>
          ))}
        </DropdownPrimitive.Content>
      </DropdownPrimitive.Portal>
    </DropdownPrimitive.Root>
  );
}

export function Skeleton({
  label = 'Loading',
  rows = 3,
}: {
  label?: string;
  rows?: number;
}) {
  return (
    <div role="status" className="skeleton-group">
      <span className="sr-only">{label}</span>
      {Array.from({ length: rows }, (_, i) => (
        <div aria-hidden="true" key={i} className="skeleton" />
      ))}
    </div>
  );
}
export function Toast({
  message,
  open,
  onOpenChange,
}: {
  message: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  return (
    <ToastPrimitive.Provider duration={4500}>
      <ToastPrimitive.Root
        className="toast"
        open={open}
        onOpenChange={onOpenChange}
      >
        <ToastPrimitive.Title>{message}</ToastPrimitive.Title>
        <ToastPrimitive.Close
          className="icon-button"
          aria-label="Dismiss notification"
        >
          ×
        </ToastPrimitive.Close>
      </ToastPrimitive.Root>
      <ToastPrimitive.Viewport className="toast-viewport" />
    </ToastPrimitive.Provider>
  );
}
export function EmptyState({
  title,
  description,
  icon,
  children,
}: {
  title: string;
  description: string;
  icon?: ReactNode;
  children?: ReactNode;
}) {
  return (
    <div className="empty-state">
      {icon && (
        <div className="empty-icon" aria-hidden="true">
          {icon}
        </div>
      )}
      <h3>{title}</h3>
      <p>{description}</p>
      {children}
    </div>
  );
}
export function ErrorState({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children?: ReactNode;
}) {
  return (
    <div className="error-state" role="alert">
      <span className="error-marker" aria-hidden="true">
        !
      </span>
      <div>
        <h3>{title}</h3>
        <p>{description}</p>
        {children}
      </div>
    </div>
  );
}
export function ProgressStep({
  title,
  description,
  status,
  number,
}: {
  title: string;
  description?: string;
  status: ProgressStatus;
  number: number;
}) {
  return (
    <li className={`progress-step progress-step--${status}`}>
      <span className="step-number" aria-hidden="true">
        {status === 'complete' ? '✓' : number}
      </span>
      <div>
        <strong>{title}</strong>
        {description && <p>{description}</p>}
      </div>
      <StatusBadge status={status} />
    </li>
  );
}
export function ValidationRow({
  category,
  title,
  required,
  measured,
  status,
  detail,
}: {
  category: string;
  title: string;
  required: string;
  measured: string;
  status: ValidationStatus;
  detail?: string;
}) {
  return (
    <article className="validation-row">
      <div className="row-between">
        <div>
          <span className="eyebrow">{category}</span>
          <h3>{title}</h3>
        </div>
        <StatusBadge status={status} />
      </div>
      <dl className="value-pair">
        <div>
          <dt>Required</dt>
          <dd>{required}</dd>
        </div>
        <div>
          <dt>Measured</dt>
          <dd>{measured}</dd>
        </div>
      </dl>
      {detail && <p className="muted small">{detail}</p>}
    </article>
  );
}
