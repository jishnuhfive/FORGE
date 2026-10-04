import type { ProgressStatus, ValidationStatus } from '@forge/design-system';

export type Mode = 'design' | 'modify' | 'learn';
export type Theme = 'system' | 'light' | 'dark';
export type SelectionState =
  'none' | 'face' | 'edges' | 'ambiguous' | 'unsupported' | 'stale';
export type CadContext =
  | { kind: 'disconnected' }
  | { kind: 'no-document' }
  | {
      kind: 'preview';
      document: string;
      workspace: string;
      element: string;
      selection: string;
    };
export interface BriefSection {
  title: string;
  values: {
    label: string;
    value: string;
    source: 'confirmed' | 'assumed' | 'missing';
  }[];
}
export interface RunStep {
  id: string;
  title: string;
  status: ProgressStatus;
  description?: string;
}
export interface ValidationCheck {
  id: string;
  category: string;
  title: string;
  required: string;
  measured: string;
  status: ValidationStatus;
  detail?: string;
}
export interface HistoryEntry {
  id: string;
  kind:
    | 'project'
    | 'conversation'
    | 'run'
    | 'operation'
    | 'validation'
    | 'activity';
  title: string;
  detail: string;
  time: string;
}
export type ErrorCode =
  | 'disconnected'
  | 'no-document'
  | 'permission'
  | 'network'
  | 'timeout'
  | 'ai-unavailable'
  | 'cad-failed'
  | 'rate-limited'
  | 'cancelled'
  | 'unexpected';
export interface Preferences {
  theme: Theme;
  units: 'metric' | 'imperial';
  onboarded: boolean;
  printer: string;
  width: number;
  depth: number;
  height: number;
  materials: string;
}
