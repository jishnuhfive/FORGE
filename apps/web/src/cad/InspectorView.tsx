import { useId, useState } from 'react';
import type { ReactNode } from 'react';
import { Badge } from '@forge/design-system';
import type {
  Body,
  EvidenceList,
  Feature,
  Inspector,
  Parameter,
  Part,
} from './inspector';
import type { Section, SectionName } from './api';
import { messages } from './messages';

const types: Record<Feature['feature_type'], string> = {
  sketch: 'Sketch',
  extrude: 'Extrude',
  fillet: 'Fillet',
  chamfer: 'Chamfer',
  unknown: 'Custom or unknown feature',
};
const suppression: Record<Feature['suppression'], string> = {
  active: 'Active',
  suppressed: 'Suppressed',
  unverified: 'Suppression unverified',
};
function ParameterValue({ item }: { item: Parameter }) {
  if (item.state !== 'available')
    return (
      <span className="muted">
        {item.state === 'unsupported'
          ? 'Unsupported parameter type'
          : item.state === 'omitted'
            ? 'Value omitted: display limit'
            : 'Value not supplied or incompatible'}
      </span>
    );
  if (item.kind === 'boolean')
    return <span>{item.boolean ? 'True' : 'False'}</span>;
  if (item.kind === 'query_count')
    return <span>{item.count} query entries · entity count unverified</span>;
  return (
    <span>
      {item.text === '' ? '(empty string)' : item.text}
      {item.kind === 'expression' && (
        <span className="muted"> · expression, not evaluated</span>
      )}
    </span>
  );
}
function ListSection<T>({
  title,
  evidence,
  section,
  children,
}: {
  title: string;
  evidence: EvidenceList<T>;
  section: Section;
  children: ReactNode;
}) {
  return (
    <details className="inspector-section" open>
      <summary>
        {title}
        <span className="muted">
          {section.status === 'success'
            ? (section.count ?? 'Count unverified')
            : 'Unavailable'}
        </span>
      </summary>
      <div className="inspector-section-content">
        {section.status !== 'success' ? (
          <p className="small">{messages[section.code]}</p>
        ) : (
          <>
            {evidence.completeness !== 'complete' && (
              <p className="small muted">
                Summary {evidence.completeness}: some information is missing,
                unsupported or outside display limits.
              </p>
            )}
            {evidence.omitted_count > 0 && (
              <p className="small">
                Showing the first {evidence.items.length} of{' '}
                {evidence.returned_count} returned items.{' '}
                {evidence.omitted_count} omitted by the display limit.
              </p>
            )}
            {evidence.items.length === 0 ? (
              <p className="small">No {title.toLowerCase()} returned.</p>
            ) : (
              children
            )}
          </>
        )}
      </div>
    </details>
  );
}
function FeatureList({ items }: { items: Feature[] }) {
  const id = useId();
  const [search, setSearch] = useState('');
  const filtered = items.filter((f) =>
    `${f.name} ${types[f.feature_type]}`
      .toLocaleLowerCase()
      .includes(search.toLocaleLowerCase()),
  );
  return (
    <>
      <label className="field-label" htmlFor={id}>
        Search features
      </label>
      <input
        id={id}
        className="input"
        type="search"
        maxLength={256}
        value={search}
        onChange={(e) => setSearch(e.target.value)}
      />
      {filtered.length === 0 && (
        <p className="small" role="status">
          No matching features.
        </p>
      )}
      <ol className="inspector-items" aria-label="Feature order">
        {filtered.map((f) => (
          <li key={f.index} value={f.index}>
            <details className="inspector-item">
              <summary>
                <span className="inspector-index" aria-hidden="true">
                  {f.index}
                </span>
                <span>
                  <strong>{f.name}</strong>
                  <span className="small muted inspector-subtitle">
                    {types[f.feature_type]} · {suppression[f.suppression]}
                  </span>
                </span>
              </summary>
              <div className="inspector-item-content">
                {f.feature_type === 'unknown' && (
                  <p className="small">Type not yet interpreted by Forge.</p>
                )}
                {f.completeness !== 'complete' && (
                  <p className="small muted">
                    Feature summary {f.completeness}. Only supported parameter
                    evidence is shown.
                  </p>
                )}
                {f.parameters.length === 0 && (
                  <p className="small muted">
                    No parameter summaries available.
                  </p>
                )}
                <dl className="inspector-fields">
                  {f.parameters.map((p, i) => (
                    <div key={i}>
                      <dt>{p.label}</dt>
                      <dd>
                        <ParameterValue item={p} />
                      </dd>
                    </div>
                  ))}
                </dl>
                {f.omitted_parameters > 0 && (
                  <p className="small">
                    {f.omitted_parameters} parameters omitted by the display
                    limit.
                  </p>
                )}
                <p className="small muted">
                  Reported parameters may include inactive options. Expressions
                  are not evaluated; units are not inferred.
                </p>
              </div>
            </details>
          </li>
        ))}
      </ol>
    </>
  );
}
function PartList({ items }: { items: Part[] }) {
  const id = useId();
  const [search, setSearch] = useState('');
  const filtered = items.filter((p) =>
    `${p.name} ${p.part_number ?? ''}`
      .toLocaleLowerCase()
      .includes(search.toLocaleLowerCase()),
  );
  return (
    <>
      <label className="field-label" htmlFor={id}>
        Search parts
      </label>
      <input
        id={id}
        className="input"
        type="search"
        maxLength={256}
        value={search}
        onChange={(e) => setSearch(e.target.value)}
      />
      {filtered.length === 0 && (
        <p className="small" role="status">
          No matching parts.
        </p>
      )}
      {filtered.map((p) => (
        <details className="inspector-item" key={p.index}>
          <summary>{p.name}</summary>
          <div className="inspector-item-content">
            <dl className="inspector-fields">
              {Object.entries({
                Description: p.description,
                'Part number': p.part_number,
                'Body type': p.body_type,
                State: p.state,
                Mesh: p.is_mesh === null ? null : p.is_mesh ? 'Yes' : 'No',
                Mass: 'Per-part mass unverified; aggregate read only',
              }).map(([key, value]) => (
                <div key={key}>
                  <dt>{key}</dt>
                  <dd>{value ?? 'Not supplied'}</dd>
                </div>
              ))}
            </dl>
            {p.completeness !== 'complete' && (
              <p className="small muted">
                Some metadata is missing or outside display limits.
              </p>
            )}
          </div>
        </details>
      ))}
    </>
  );
}
function BodyList({ items }: { items: Body[] }) {
  return (
    <>
      {items.map((b) => (
        <details className="inspector-item" key={b.index}>
          <summary>
            Body {b.index} · {b.body_type ?? 'Type unverified'}
          </summary>
          <dl className="inspector-fields inspector-item-content">
            {Object.entries({
              Faces: b.face_count,
              Edges: b.edge_count,
              Vertices: b.vertex_count,
            }).map(([name, count]) => (
              <div key={name}>
                <dt>{name}</dt>
                <dd>{count ?? 'Unknown'}</dd>
              </div>
            ))}
          </dl>
          <p className="small muted inspector-item-content">
            Counts describe returned topology entries. Missing or empty
            collections are unverified.
          </p>
        </details>
      ))}
    </>
  );
}
export function InspectorView({ result }: { result: Inspector }) {
  const { source, physical } = result;
  const count = (name: SectionName, singular: string) =>
    source[name].status !== 'success'
      ? `${singular} unavailable`
      : source[name].count === null
        ? `${singular} count unverified`
        : `${source[name].count} ${source[name].count === 1 ? singular : name}`;
  const massLabel =
    source.mass.status !== 'success'
      ? 'Mass read unavailable'
      : source.mass.count === 0
        ? 'No mass-property bodies returned'
        : physical.mass === 'available'
          ? 'Mass properties available'
          : physical.mass === 'unavailable'
            ? 'Mass unavailable; material/density may be missing'
            : physical.mass === 'partial'
              ? 'Mass partially available; some contributions are missing'
              : 'Mass data read; assigned mass is unavailable or unverified';
  return (
    <div className="cad-inspector">
      <h3>Part Studio overview</h3>
      {source.features.status === 'success' &&
        source.parts.status === 'success' && (
          <Badge tone="accent">Onshape data connected</Badge>
        )}
      <ul className="cad-read-summary small" aria-label="Part Studio counts">
        <li>{count('features', 'feature')}</li>
        <li>{count('parts', 'part')}</li>
        <li>{count('bodies', 'body')}</li>
        <li>{massLabel}</li>
      </ul>
      <p className="small muted">
        Read at{' '}
        <time dateTime={source.captured_at}>
          {new Date(source.captured_at).toLocaleTimeString()}
        </time>
        .{' '}
        {source.consistency === 'mismatch'
          ? 'CAD changed during this read. Evidence is stale; refresh before using it.'
          : 'Separate reads; a single consistent CAD version is unverified.'}
      </p>
      <p className="small muted">
        {result.freshness === 'stale'
          ? 'Freshness: stale.'
          : 'Freshness: captured, currentness unverified.'}{' '}
        Changes after this read are not monitored. Default configuration · end
        of the feature list.
      </p>
      <ListSection
        title="Features"
        evidence={result.features}
        section={source.features}
      >
        <FeatureList items={result.features.items} />
      </ListSection>
      <ListSection title="Parts" evidence={result.parts} section={source.parts}>
        <PartList items={result.parts.items} />
      </ListSection>
      <ListSection
        title="Bodies"
        evidence={result.bodies}
        section={source.bodies}
      >
        <BodyList items={result.bodies.items} />
      </ListSection>
      <details
        className="inspector-section"
        open={source.mass.status !== 'success'}
      >
        <summary>Physical properties</summary>
        <div className="inspector-section-content">
          {source.mass.status !== 'success' ? (
            <p className="small">{messages[source.mass.code]}</p>
          ) : (
            <>
              <dl className="inspector-fields">
                <div>
                  <dt>Mass evidence</dt>
                  <dd>{physical.mass}</dd>
                </div>
                <div>
                  <dt>Missing mass contributions</dt>
                  <dd>
                    {physical.missing_mass === null
                      ? 'Unverified'
                      : physical.missing_mass
                        ? 'Reported; material/density may be missing'
                        : 'None reported'}
                  </dd>
                </div>
                <div>
                  <dt>Volume estimate</dt>
                  <dd>{physical.volume}</dd>
                </div>
                <div>
                  <dt>Scope</dt>
                  <dd>Aggregate; individual part association unverified</dd>
                </div>
                <div>
                  <dt>Units</dt>
                  <dd>
                    Physical units haven’t been independently verified. Numeric
                    mass and volume aren’t supplied.
                  </dd>
                </div>
              </dl>
            </>
          )}
        </div>
      </details>
    </div>
  );
}
