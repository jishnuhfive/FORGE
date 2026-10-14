// Fixed first-body topology structure only. No provider values or dynamic keys.
export function parseBodyStructure(text: string): string | null {
  if (!import.meta.env.DEV || text.length > 512) return null;
  const object = (value: unknown): value is Record<string, unknown> =>
    value !== null && typeof value === 'object' && !Array.isArray(value);
  const exact = (value: Record<string, unknown>, keys: string[]) =>
    Object.keys(value).length === keys.length &&
    keys.every((key) => Object.hasOwn(value, key));
  try {
    const report: unknown = JSON.parse(text);
    if (
      !object(report) ||
      !exact(report, ['bodyDetails']) ||
      !object(report.bodyDetails) ||
      !exact(report.bodyDetails, ['faces', 'edges', 'vertices'])
    )
      return null;
    for (const field of Object.values(report.bodyDetails)) {
      if (
        !object(field) ||
        !exact(field, ['present', 'type', 'length']) ||
        typeof field.present !== 'boolean'
      )
        return null;
      if (field.type === 'array') {
        if (
          !field.present ||
          typeof field.length !== 'number' ||
          !Number.isSafeInteger(field.length) ||
          field.length < 0 ||
          field.length > 20000
        )
          return null;
      } else if (field.type !== 'missing' || field.length !== null) return null;
    }
    const output = JSON.stringify(report, null, 2);
    return output.length <= 1024 ? output : null;
  } catch {
    return null;
  }
}
