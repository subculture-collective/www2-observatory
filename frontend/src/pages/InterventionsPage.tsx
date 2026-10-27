import { api } from "../api/client.ts";
import { Panel, ErrorNote } from "../ui/Panel.tsx";
import { useData } from "../lib/settings.tsx";

const SCOPE_TONE: Record<string, string> = {
  "public intervention": "c-engagement",
  "private measurement": "c-operator",
  "public distribution intervention": "c-scanner",
};

export function InterventionsPage() {
  const { data, error } = useData(() => api.interventions());
  if (!data) return <p className="empty">loading…</p>;
  const changes = [...data.changes].sort((a, b) => b.date.localeCompare(a.date));
  return (
    <>
      <ErrorNote error={error} />
      <Panel id="interventions" span={4} chip={`${changes.length} entries · ledger v${data.version} · dates in ${data.timezone}`}>
        <ol className="ledger">
          {changes.map((c) => (
            <li key={c.id}>
              <div className="ledger-when">
                <b>{c.date}</b>
                <span className={`tag ${SCOPE_TONE[c.scope] ?? ""}`}>{c.scope}</span>
              </div>
              <div className="ledger-body">
                <h3>
                  <code>{c.id}</code>
                </h3>
                <p>{c.description}</p>
                {c.resources && c.resources.length > 0 && (
                  <details>
                    <summary>{c.resources.length} resource hashes</summary>
                    <table className="data">
                      <tbody>
                        {c.resources.map((r) => (
                          <tr key={r.path}>
                            <td>
                              <code>{r.path}</code>
                            </td>
                            <td className="mono dim">{r.sha256}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </details>
                )}
              </div>
            </li>
          ))}
        </ol>
        <p className="note">
          Public interventions change what visitors can see. Private measurement changes how the same logs are counted. Distribution interventions announce the site somewhere and induce traffic that is not ambient discovery. The ledger is copied from the relay repository at build time.
        </p>
      </Panel>
    </>
  );
}
