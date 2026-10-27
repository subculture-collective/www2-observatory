import { D } from "../lib/descriptions.ts";
import { Panel } from "../ui/Panel.tsx";

/** Every view description in one place, for reading start to finish. */
export function Glossary() {
  return (
    <Panel title="Glossary: what each view shows, what it determines, why it is recorded" span={4}>
      <p className="note">The same text is behind every “?” control. Nothing here is an evaluation of the traffic; it describes the measurement.</p>
      <dl className="glossary">
        {Object.entries(D).map(([key, d]) => (
          <div key={key} id={`g-${key}`}>
            <dt>{d.title}</dt>
            <dd>
              <p>
                <b>shows</b> {d.what}
              </p>
              <p>
                <b>determines</b> {d.determines}
              </p>
              <p>
                <b>why</b> {d.why}
              </p>
              <ul>
                {d.caveats.map((c) => (
                  <li key={c}>{c}</li>
                ))}
              </ul>
              <p className="dim">
                <code>{d.source}</code>
              </p>
            </dd>
          </div>
        ))}
      </dl>
    </Panel>
  );
}
