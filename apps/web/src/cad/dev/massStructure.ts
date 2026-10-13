// Fixed vocabulary reviewed against the public v17 mass and vector schemas.
const fields = [
  'response',
  'microversionId',
  'bodies',
  'bodyRecord',
  'mass',
  'volume',
  'periphery',
  'centroid',
  'inertia',
  'hasMass',
  'massMissingCount',
  'principalInertia',
  'principalAxes',
  'principalAxes.item',
  'principalAxes.x',
  'principalAxes.y',
  'principalAxes.z',
  'principalAxes.btType',
] as const;
const categories = [
  'null',
  'boolean',
  'number',
  'nonfinite_number',
  'string',
  'array',
  'object',
] as const;
const reasons = [
  'type_mismatch',
  'length_limit',
  'nonfinite_number',
  'invalid_bounds',
  'numeric_bound',
  'schema_invalid',
] as const;
const predicates = ['negative_nominal', 'bounds_order'] as const;
const comparisonKeys = [
  'position0_vs_position1',
  'position0_vs_position2',
  'position1_vs_position2',
];

export function parseMassStructure(text: string): string | null {
  if (!import.meta.env.DEV || text.length > 4096) return null;
  const object = (value: unknown): value is Record<string, unknown> =>
    value !== null && typeof value === 'object' && !Array.isArray(value);
  const exact = (
    value: Record<string, unknown>,
    required: string[],
    optional: string[] = [],
  ) =>
    required.every((key) => key in value) &&
    Object.keys(value).every((key) => [...required, ...optional].includes(key));
  const member = (value: unknown, list: readonly string[]) =>
    typeof value === 'string' && list.includes(value);
  try {
    const report: unknown = JSON.parse(text);
    if (
      !object(report) ||
      !exact(
        report,
        ['diagnostic', 'reason', 'recordKind', 'fields', 'validation'],
        ['massSigns', 'hasMass', 'massMissingCountCategory'],
      ) ||
      report.diagnostic !== 'forge-mass-structure-v1' ||
      !member(report.reason, [
        'schema_validation',
        'invalid_json_or_normalization',
        'transport_metadata',
        'diagnostic_limit',
      ]) ||
      !member(report.recordKind, ['aggregate', 'body', 'none']) ||
      !Array.isArray(report.fields) ||
      report.fields.length > 18 ||
      !Array.isArray(report.validation) ||
      report.validation.length > 8
    )
      return null;
    if (
      ('hasMass' in report && typeof report.hasMass !== 'boolean') ||
      ('massMissingCountCategory' in report &&
        !member(report.massMissingCountCategory, ['zero', 'positive']))
    )
      return null;
    if ('massSigns' in report) {
      if (
        !object(report.massSigns) ||
        !exact(report.massSigns, ['position0', 'position1', 'position2']) ||
        !Object.values(report.massSigns).every((value) =>
          member(value, ['negative', 'zero', 'positive']),
        )
      )
        return null;
    }
    for (const field of report.fields as unknown[]) {
      if (
        !object(field) ||
        !exact(field, ['field', 'type'], ['length', 'items']) ||
        !member(field.field, fields) ||
        !member(field.type, [...categories, 'absent'])
      )
        return null;
      if (field.type === 'array') {
        if (
          typeof field.length !== 'number' ||
          !Number.isSafeInteger(field.length) ||
          field.length < 0 ||
          field.length > 100000 ||
          !Array.isArray(field.items) ||
          field.items.length > categories.length ||
          !field.items.every((item: unknown) => member(item, categories))
        )
          return null;
      } else if ('length' in field || 'items' in field) return null;
    }
    for (const failure of report.validation as unknown[]) {
      if (
        !object(failure) ||
        !exact(
          failure,
          ['field', 'reason'],
          ['failedPredicates', 'comparisons'],
        ) ||
        !member(failure.field, fields) ||
        !member(failure.reason, reasons)
      )
        return null;
      if ('failedPredicates' in failure || 'comparisons' in failure) {
        if (
          !member(failure.field, ['mass', 'volume', 'periphery']) ||
          failure.reason !== 'invalid_bounds' ||
          !Array.isArray(failure.failedPredicates) ||
          failure.failedPredicates.length !== 1 ||
          !failure.failedPredicates.every((item: unknown) =>
            member(item, predicates),
          )
        )
          return null;
        if ('comparisons' in failure) {
          if (
            !object(failure.comparisons) ||
            !exact(failure.comparisons, comparisonKeys) ||
            !Object.values(failure.comparisons).every((value) =>
              member(value, ['greater', 'equal', 'less']),
            )
          )
            return null;
        }
      }
    }
    if (
      ['massSigns', 'hasMass', 'massMissingCountCategory'].some(
        (key) => key in report,
      ) &&
      !report.validation.some(
        (failure: Record<string, unknown>) =>
          failure.field === 'mass' && failure.reason === 'invalid_bounds',
      )
    )
      return null;
    const output = JSON.stringify(report, null, 2);
    return output.length <= 8192 ? output : null;
  } catch {
    return null;
  }
}
