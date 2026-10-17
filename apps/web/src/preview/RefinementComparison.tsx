import { ForgeMark } from '@forge/design-system';
import { Shell } from '../components/Shell';
import { AnalysisEmpty } from '../ai/Analysis';
import { PromptComposer } from '../components/PromptComposer';
import { sampleContext } from './data';

const candidates = [
  {
    id: 'A',
    name: 'Oblique plane',
    path: 'M4 8 21 3 28 9 11 14Z M4 12 11 17 11 29 4 24Z M13 17 22 14 27 19 13 23Z',
  },
  {
    id: 'B',
    name: 'Open joint',
    path: 'M5 4h22l-5 7H5z M5 13h15l-5 7H5z M5 22h7v7H5z',
  },
  {
    id: 'C',
    name: 'Stepped billet',
    path: 'M4 5h20l5 6H9z M4 13h14l5 6H9z M4 21h7v8H8l-4-5z',
  },
];
function Candidate({ path, size = 24 }: { path: string; size?: number }) {
  return (
    <svg
      className="forge-mark candidate-mark"
      width={size}
      height={size}
      style={{ width: size, height: size }}
      viewBox="0 0 32 32"
      fill="currentColor"
      aria-hidden="true"
    >
      <path d={path} />
    </svg>
  );
}
export default function RefinementComparison({
  logos = false,
}: {
  logos?: boolean;
}) {
  return (
    <div className="refinement-review">
      <h1>{logos ? 'Three planes, one identity' : 'Material comparison'}</h1>
      <p className="muted small">
        Historical development comparison. Synthetic context; no service
        requests. Oblique Plane and the refined material are human-approved.
      </p>
      <div className="refinement-columns">
        {logos
          ? candidates.map((candidate) => (
              <section key={candidate.id} className="candidate-review">
                <h2>
                  {candidate.id} · {candidate.name}
                </h2>
                <div className="candidate-shell">
                  <Shell
                    context={sampleContext}
                    brandMark={<Candidate path={candidate.path} />}
                    onOnboarding={() => undefined}
                    onNotify={() => undefined}
                  >
                    <div className="candidate-empty">
                      <AnalysisEmpty
                        mark={<Candidate path={candidate.path} />}
                      />
                      <div className="candidate-icon-context">
                        <Candidate path={candidate.path} size={16} />
                        <span>16px context</span>
                        <span className="candidate-app-icon">
                          <Candidate path={candidate.path} size={32} />
                        </span>
                      </div>
                    </div>
                  </Shell>
                </div>
                <div
                  className="candidate-scales"
                  aria-label={`${candidate.name} monochrome sizes`}
                >
                  {[16, 20, 24, 32, 64, 128].map((size) => (
                    <div key={size}>
                      <Candidate path={candidate.path} size={size} />
                      <span>{size}px</span>
                    </div>
                  ))}
                </div>
                <div className="candidate-paper">
                  {[16, 20, 24, 32, 64, 128].map((size) => (
                    <Candidate key={size} path={candidate.path} size={size} />
                  ))}
                </div>
              </section>
            ))
          : [
              {
                id: 'original',
                title: 'A · First pass',
                detail: 'Previous dark fill and hairline edge.',
              },
              {
                id: 'refined',
                title: 'B · Refined',
                detail: 'Internal light, refractive edge and optical action.',
              },
              {
                id: 'opaque',
                title: 'C · Opaque',
                detail: 'Equivalent hierarchy with transparency removed.',
              },
            ].map((variant) => (
              <section
                key={variant.id}
                className={`material-comparison material-comparison--${variant.id}`}
                data-transparency={
                  variant.id === 'opaque' ? 'reduced' : undefined
                }
              >
                <h2>{variant.title}</h2>
                <p className="small muted">{variant.detail}</p>
                <div className="comparison-surface">
                  <div className="comparison-mark">
                    <ForgeMark />
                    <span>FORGE</span>
                  </div>
                  <PromptComposer
                    label={`${variant.title} prompt`}
                    placeholder="Ask about this Part Studio…"
                    context="1 face selected"
                    onSubmit={() => undefined}
                    hint="Synthetic comparison"
                  />
                </div>
              </section>
            ))}
      </div>
    </div>
  );
}
