package analytics

import (
	"database/sql"
	"strings"
	"time"

	"github.com/onnwee/www2-observatory/internal/research"
)

type ExperimentStage struct {
	Key     string `json:"key"`
	Label   string `json:"label"`
	Clients int    `json:"clients"`
}
type ExperimentEvidence struct {
	Client  string  `json:"client"`
	Stage   string  `json:"stage"`
	EventID int64   `json:"event_id"`
	Path    string  `json:"path"`
	TS      float64 `json:"ts"`
}
type ExperimentReport struct {
	Hours            int                  `json:"hours"`
	Revision         string               `json:"revision"`
	Attribution      map[string]int       `json:"attribution"`
	Traffic          map[string]int       `json:"traffic"`
	EligibleClients  int                  `json:"eligible_clients"`
	SuccessfulWrites int                  `json:"successful_writes"`
	ReturningClients int                  `json:"returning_clients"`
	CrossSourceReads int                  `json:"cross_source_reads"`
	Stages           []ExperimentStage    `json:"stages"`
	Evidence         []ExperimentEvidence `json:"evidence"`
	Notes            []string             `json:"notes"`
}

func Experiment(conn *sql.DB, hours, gapMinutes int) (ExperimentReport, error) {
	hours = clamp(hours, 1, 24*90)
	report := ExperimentReport{Hours: hours, Revision: "caddy-client-v2", Attribution: map[string]int{}, Traffic: map[string]int{}, Evidence: []ExperimentEvidence{}, Stages: []ExperimentStage{
		{Key: "discovery", Label: "Discovery"}, {Key: "capability", Label: "Capability inspection"}, {Key: "representation", Label: "Structured/text retrieval"}, {Key: "write", Label: "Successful write"}, {Key: "return", Label: "Later object retrieval"},
	}, Notes: []string{
		"Ordered funnel: one client fingerprint must reach each stage in order within this window. A stage cannot be inferred from a skipped step.",
		"Only caddy-client-v2 resource engagement is eligible. Operator-marked, scanner, other, and legacy attribution records are excluded; unmarked operator traffic may remain.",
		"Client = HMAC of validated address plus user agent; source = address HMAC. Neither proves a person, model, or independent agent.",
		"Return requires GET of the last known durable object written by that client after the configured session gap. Collection reads and writes without a Location/object key cannot prove this.",
		"Scan labels are path heuristics, not intent judgments. Operator labels are self-declared. Structured retrieval does not establish deliberate representation discovery.",
	}}
	rows, err := conn.Query(`SELECT id,ts,source_id,client_id,method,path,query,status,content_type,attribution,traffic_class,write_object,successful_write FROM access_events WHERE ts>=? ORDER BY ts,id`, float64(time.Now().Unix())-float64(hours*3600))
	if err != nil {
		return report, err
	}
	defer rows.Close()
	type progress struct {
		stage int
		last  float64
	}
	clients := map[string]*progress{}
	returners := map[string]bool{}
	type write struct {
		client, source string
		ts             float64
		eligible       bool
	}
	objects := map[string]write{}
	for rows.Next() {
		var id int64
		var ts float64
		var source, client, method, path, query, ct, attr, class, object string
		var status, successful int
		if err := rows.Scan(&id, &ts, &source, &client, &method, &path, &query, &status, &ct, &attr, &class, &object, &successful); err != nil {
			return report, err
		}
		report.Attribution[attr]++
		report.Traffic[class]++
		eligible := attr == "caddy-client-v2" && class == "engagement"
		previous, hadWrite := objects[research.ReadObject(path)]
		if object != "" {
			objects[object] = write{client, source, ts, eligible}
		}
		if !eligible {
			continue
		}
		p := clients[client]
		if p == nil {
			p = &progress{}
			clients[client] = p
		}
		if successful != 0 {
			report.SuccessfulWrites++
		}
		returned := method == "GET" && status >= 200 && status < 300 && hadWrite && previous.eligible && previous.client == client && ts-previous.ts >= float64(gapMinutes*60)
		if returned {
			returners[client] = true
		}
		if method == "GET" && status >= 200 && status < 300 && hadWrite && previous.eligible && previous.source != source && ts > previous.ts {
			report.CrossSourceReads++
		}
		entry := (method == "GET" || method == "HEAD") && (path == "/" || path == "/robots.txt" || path == "/sitemap.xml" || path == "/index.txt")
		capability := path == "/help.txt" || path == "/README.TXT" || method == "OPTIONS" && research.IsResource(path)
		representation := method == "GET" && (strings.Contains(ct, "json") || strings.HasPrefix(ct, "text/plain") || strings.Contains(ct, "atom"))
		conditions := []bool{entry, capability, representation, successful != 0, returned}
		if p.stage < len(conditions) && conditions[p.stage] && (p.stage == 0 || ts > p.last) {
			report.Stages[p.stage].Clients++
			if len(report.Evidence) < 100 {
				report.Evidence = append(report.Evidence, ExperimentEvidence{client, report.Stages[p.stage].Key, id, path, ts})
			}
			p.stage++
			p.last = ts
		}
	}
	report.EligibleClients = len(clients)
	report.ReturningClients = len(returners)
	return report, rows.Err()
}
