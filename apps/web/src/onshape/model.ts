/** Browser references only. These never establish CAD access or ownership. */
export interface OnshapeClientContext {
  documentId: string;
  elementId: string;
  server: string;
  revision:
    | { kind: 'workspace'; workspaceId: string }
    | { kind: 'version'; versionId: string };
  microversionId?: string;
  // No legitimate name/type source exists in the current launch contract.
  elementType?: 'partStudio' | 'assembly' | 'drawing' | 'blob';
}
export type EmbeddedStatus =
  | 'STANDALONE'
  | 'EMBEDDED_INITIALIZING'
  | 'EMBEDDED_CONNECTED'
  | 'EMBEDDED_CONTEXT_ERROR'
  | 'UNTRUSTED_ORIGIN';

export interface SelectionEntity {
  type: 'face' | 'edge' | 'vertex' | 'body' | 'entity';
  reference?: string;
}
export interface SelectionContext {
  status: 'waiting' | 'available' | 'stale' | 'unavailable';
  entities: readonly SelectionEntity[];
  sourceElementId?: string;
}
export interface ClientState {
  status: EmbeddedStatus;
  context: OnshapeClientContext | null;
  selection: SelectionContext;
  issue?:
    | 'invalid-context'
    | 'untrusted-server'
    | 'untrusted-parent'
    | 'selection-contract';
}
export const standaloneState: ClientState = {
  status: 'STANDALONE',
  context: null,
  selection: { status: 'waiting', entities: [] },
};
export function selectionLabel(selection: SelectionContext): string {
  if (selection.status === 'waiting') return 'Waiting for selection context';
  if (selection.status === 'stale') return 'Selection needs refresh';
  if (selection.status === 'unavailable')
    return 'Selection details unavailable';
  const count = selection.entities.length;
  if (!count) return 'No selection';
  const first = selection.entities[0]?.type;
  const type =
    first && selection.entities.every((entity) => entity.type === first)
      ? first
      : 'entity';
  const plural = type === 'entity' ? 'entities' : `${type}s`;
  return `${count} ${count === 1 ? type : plural} selected`;
}
export function revisionId(context: OnshapeClientContext): string {
  return context.revision.kind === 'workspace'
    ? context.revision.workspaceId
    : context.revision.versionId;
}
