/** DEV-only structure inspection, deliberately NOT an Onshape payload decoder. */
const safeNames = new Set([
  'messageName',
  'messageId',
  'type',
  'data',
  'payload',
  'result',
  'results',
  'selection',
  'selections',
  'selected',
  'items',
  'entities',
  'entity',
  'entityType',
  'selectionType',
  'bodyType',
  'geometryType',
  'category',
  'id',
  'ids',
  'entityId',
  'entityIds',
  'selectionId',
  'selectionIds',
  'idTag',
  'reference',
  'references',
  'documentId',
  'workspaceId',
  'versionId',
  'elementId',
  'microversionId',
  'documentMicroversionId',
  'elementMicroversionId',
  'partId',
  'partIds',
  'featureId',
  'sourceElementId',
  'occurrencePath',
  'count',
  'selectionCount',
  'status',
  'statusCode',
  'context',
  'elementType',
  'name',
  'documentName',
  'elementName',
  'partName',
  'configuration',
  'timestamp',
  'time',
  'isSelected',
  'isValid',
  'isCleared',
  'clear',
  'access_token',
  'refresh_token',
  'token',
  'accessToken',
  'refreshToken',
  'clientSecret',
  'client_secret',
  'authorization',
  'Authorization',
  'cookie',
  'cookies',
  'code',
  'state',
  'csrf_token',
  'secret',
  'password',
]);
const secretNames =
  /token|secret|authorization|cookie|password|^code$|^state$/i;
const categoryKeys = new Set([
  'type',
  'entityType',
  'selectionType',
  'bodyType',
  'geometryType',
  'category',
]);
const categories = new Set([
  'FACE',
  'EDGE',
  'VERTEX',
  'BODY',
  'ENTITY',
  'GEOMETRY',
  'DEGENERATE_EDGE',
  'SOLID',
  'SHEET',
  'WIRE',
  'POINT',
  'MATE_CONNECTOR',
  'COMPOSITE',
  'UNKNOWN',
  'LINE',
  'CIRCLE',
  'ARC',
  'PLANE',
  'CYLINDER',
  'CONE',
  'SPHERE',
  'TORUS',
  'SPLINE',
  'ELLIPSE',
  'MESH',
]);
export const STRUCTURE_LIMITS = {
  depth: 6,
  nodes: 160,
  fields: 24,
  arrayItems: 3,
  reportedArrayLength: 10_000,
  outputCharacters: 24_000,
} as const;
type Node = {
  kind: string;
  value?: '<redacted>';
  category?: string;
  length?: number;
  lengthCapped?: boolean;
  fields?: { name: string; structure: Node }[];
  items?: Node[];
  truncated?: boolean;
};

/** Output contains only fixed literals, allowlisted labels, types and capped counts.
 * No untrusted string (including unknown PROPERTY NAMES) is interpolated.
 * No JSON.stringify/toJSON is ever invoked on the input or its descendants.
 */
export function sanitizedSelectionStructure(input: unknown): string | null {
  if (!input || typeof input !== 'object' || Array.isArray(input)) return null;
  try {
    const message = Object.getOwnPropertyDescriptor(input, 'messageName');
    if (!message || !('value' in message) || message.value !== 'SELECTION')
      return null;
    let remaining = STRUCTURE_LIMITS.nodes as number;
    let truncated = false;
    const seen = new WeakSet<object>();
    const truncate = (): Node => {
      truncated = true;
      return { kind: 'truncated' };
    };
    const visit = (value: unknown, depth: number, field = ''): Node => {
      if (--remaining < 0 || depth > STRUCTURE_LIMITS.depth) return truncate();
      if (field.length > 128 || secretNames.test(field))
        return { kind: 'redacted', value: '<redacted>' };
      if (value === null) return { kind: 'null' };
      if (typeof value === 'string') {
        if (
          categoryKeys.has(field) &&
          value.length <= 32 &&
          categories.has(value)
        )
          return { kind: 'string', category: value };
        return { kind: 'string', value: '<redacted>' };
      }
      if (typeof value !== 'object') return { kind: typeof value };
      if (seen.has(value)) return { kind: 'reference', value: '<redacted>' };
      seen.add(value);
      if (Array.isArray(value)) {
        const items: Node[] = [];
        const count = Math.min(value.length, STRUCTURE_LIMITS.arrayItems);
        for (let index = 0; index < count && remaining > 0; ++index) {
          const descriptor = Object.getOwnPropertyDescriptor(value, index);
          items.push(
            descriptor && 'value' in descriptor
              ? visit(descriptor.value, depth + 1)
              : { kind: 'omitted' },
          );
        }
        const omitted = items.length < value.length;
        if (omitted) truncated = true;
        return {
          kind: 'array',
          length: Math.min(value.length, STRUCTURE_LIMITS.reportedArrayLength),
          lengthCapped: value.length > STRUCTURE_LIMITS.reportedArrayLength,
          items,
          truncated: omitted,
        };
      }
      const prototype: unknown = Object.getPrototypeOf(value);
      if (prototype !== Object.prototype && prototype !== null)
        return { kind: 'opaque-object' };
      const fields: { name: string; structure: Node }[] = [];
      let omitted = false;
      // Stop enumeration early. Never allocate Object.entries for a huge payload.
      for (const name in value) {
        if (!Object.hasOwn(value, name)) continue;
        if (fields.length >= STRUCTURE_LIMITS.fields || remaining <= 0) {
          omitted = true;
          truncated = true;
          break;
        }
        const descriptor = Object.getOwnPropertyDescriptor(value, name);
        fields.push({
          name:
            name.length <= 64 && safeNames.has(name)
              ? name
              : `<redacted-key-${fields.length + 1}>`,
          structure:
            descriptor && 'value' in descriptor
              ? visit(descriptor.value, depth + 1, name)
              : { kind: 'accessor-omitted' },
        });
      }
      return { kind: 'object', fields, truncated: omitted };
    };
    const structure = visit(input, 0);
    const output = JSON.stringify(
      {
        format: 'forge-selection-structure-v1',
        messageName: 'SELECTION',
        structure,
        truncated,
      },
      null,
      2,
    );
    return output.length <= STRUCTURE_LIMITS.outputCharacters
      ? output
      : JSON.stringify({
          format: 'forge-selection-structure-v1',
          messageName: 'SELECTION',
          structure: { kind: 'truncated' },
          truncated: true,
        });
  } catch {
    // Never reflect an exception, property name, prototype or constructor name.
    return null;
  }
}
