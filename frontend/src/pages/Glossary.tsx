import {
  familyLabels,
  familyColor,
  kindLabels,
  kindColor,
} from "../lib/diagnostics.ts";
import { D } from "../lib/descriptions.ts";
import { Panel } from "../ui/Panel.tsx";

/** Every view description in one place, for reading start to finish. */
export function Glossary() {
  return (
    <Panel
      title="Glossary: what each view shows, what it determines, why it is recorded"
      span={4}
    >
      <p className="note">
        The same text is behind every “?” control. Nothing here is an evaluation
        of the traffic; it describes the measurement.
      </p>
      <section id="probe-colors" aria-labelledby="probe-colors-title">
        <h2 id="probe-colors-title">Request & probe color key</h2>
        <p className="note">
          Colors are stable category labels, not a severity scale or evidence of
          a successful exploit. Request diagnostics describe the broad request
          type; probe families describe the matched path or payload pattern. The
          same family keeps its color in Overview, Probes & misses, and the
          event log, even when the order or time window changes.
        </p>
        <h3>Request diagnostics</h3>
        <div className="legend diagnostic-color-key">
          {Object.entries(kindLabels).map(([key, label]) => (
            <span key={key}>
              <i style={{ background: kindColor(key) }} />
              {label}
            </span>
          ))}
        </div>
        <h3>Probe families</h3>
        <div className="legend diagnostic-color-key">
          {Object.entries(familyLabels).map(([key, label]) => (
            <span key={key}>
              <i style={{ background: familyColor(key) }} />
              {label}
            </span>
          ))}
        </div>
        <p className="note">
          All charts retain text labels and counts. The probe / response
          timeline combines all probe families into one series; its overlapping
          counts must not be added together. Family bars show each matched
          family separately. Unknown misses and unclassified requests have been
          processed; those labels mean the retained evidence does not support a
          more specific classification.
        </p>
      </section>
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
