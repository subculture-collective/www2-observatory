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
// Fixed semantic palettes: filtering and sorting must never change a label's color.
export const kindColors: Record<string, string> = {
  "exploit-probe": "#ff8296",
  "secret-probe": "#ffc56e",
  "platform-probe": "#c4a1ff",
  "discovery-miss": "#b9dc75",
  "resource-miss": "#83b7ff",
  "asset-miss": "#71ddbb",
  "unknown-miss": "#d4c68b",
  resource: "#59d8ee",
  operator: "#ef9fdd",
  unclassified: "#a9b2c3",
};
export const familyColors: Record<string, string> = {
  "path-traversal": "#ff8296",
  injection: "#f694d2",
  "sensitive-files": "#ffc56e",
  wordpress: "#83b7ff",
  "php-cgi": "#b9dc75",
  framework: "#c4a1ff",
  "react-server-components": "#59d8ee",
  "admin-discovery": "#71ddbb",
};
export const kindColor = (kind: string) => kindColors[kind] ?? "#a9b2c3";
export const familyColor = (family: string) =>
  familyColors[family] ?? "#a9b2c3";
