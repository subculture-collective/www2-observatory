export const kindLabels: Record<string, string> = {
  "exploit-probe": "exploit probe",
  "secret-probe": "sensitive-file probe",
  "platform-probe": "platform probe",
  "discovery-miss": "discovery miss",
  "resource-miss": "resource miss",
  "asset-miss": "asset miss",
  "unknown-miss": "unknown miss",
  resource: "public resource",
  operator: "operator-marked",
  unclassified: "unclassified",
};
export const familyLabels: Record<string, string> = {
  "path-traversal": "traversal / local files",
  injection: "injection patterns",
  "sensitive-files": "secrets / configuration",
  wordpress: "WordPress",
  "php-cgi": "PHP / CGI tooling",
  framework: "framework internals",
  "react-server-components": "React component probes",
  "admin-discovery": "admin / device discovery",
};
export const kindColor = (kind: string) =>
  kind.includes("probe")
    ? "var(--orange)"
    : kind.includes("miss")
      ? "var(--yellow)"
      : kind === "resource"
        ? "var(--cyan)"
        : kind === "operator"
          ? "var(--magenta)"
          : "var(--fg-dim)";
