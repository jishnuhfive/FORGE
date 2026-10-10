import type { SelectionEntity } from './model';

// Resource limits, not claims about the format of Onshape topology identifiers.
const MAX_REFERENCE_LENGTH = 1024;
function own(value: object, name: string): unknown {
  const field = Object.getOwnPropertyDescriptor(value, name);
  return field && 'value' in field ? field.value : undefined;
}
function record(value: unknown): value is object {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

/** Part Studio single-entity/clear contract only. Unknown fields are discarded.
 * References stay opaque: they establish neither topology identity nor access.
 * null means unsupported/malformed, never an empty selection.
 */
export function parseSelection(
  data: unknown,
): readonly SelectionEntity[] | null {
  if (!record(data) || own(data, 'messageName') !== 'SELECTION') return null;
  const selections = own(data, 'selections');
  if (!Array.isArray(selections) || selections.length > 1) return null;
  if (selections.length === 0) return [];
  const entity = own(selections, '0');
  if (!record(entity) || own(entity, 'selectionType') !== 'ENTITY') return null;
  const type = own(entity, 'entityType');
  const reference = own(entity, 'selectionId');
  const occurrence = Object.getOwnPropertyDescriptor(entity, 'occurrencePath');
  if (
    (type !== 'FACE' && type !== 'EDGE') ||
    typeof reference !== 'string' ||
    !reference.length ||
    reference.length > MAX_REFERENCE_LENGTH ||
    Array.from(reference).some(
      (character) =>
        character.charCodeAt(0) < 32 || character.charCodeAt(0) === 127,
    ) ||
    (occurrence && (!('value' in occurrence) || occurrence.value !== undefined))
  )
    return null;
  return [{ type: type === 'FACE' ? 'face' : 'edge', reference }];
}
