package db

import (
	"database/sql"
	"github.com/onnwee/www2-observatory/internal/parsers"
	"github.com/onnwee/www2-observatory/internal/research"
)

// RefreshDiagnostics backfills additive reporting fields from stored request
// metadata. Identity, research class, raw evidence, and funnel facts are retained.
func RefreshDiagnostics(conn *sql.DB) error {
	tx, err := conn.Begin()
	if err != nil {
		return err
	}
	defer tx.Rollback()
	rows, err := tx.Query(`SELECT id,method,path,query,status,user_agent,accept_header FROM access_events WHERE diagnostic_revision<>?`, research.DiagnosticRevision)
	if err != nil {
		return err
	}
	type update struct {
		id int64
		d  research.Diagnostic
	}
	updates := []update{}
	for rows.Next() {
		var id int64
		var r parsers.AccessRecord
		if err := rows.Scan(&id, &r.Method, &r.Path, &r.Query, &r.Status, &r.UserAgent, &r.Accept); err != nil {
			rows.Close()
			return err
		}
		updates = append(updates, update{id, research.Diagnose(&r)})
	}
	err = rows.Err()
	rows.Close()
	if err != nil {
		return err
	}
	for _, u := range updates {
		if _, err := tx.Exec(`UPDATE access_events SET request_kind=?,probe_family=?,diagnostic_reason=?,diagnostic_revision=? WHERE id=?`, u.d.Kind, u.d.Family, u.d.Reason, research.DiagnosticRevision, u.id); err != nil {
			return err
		}
	}
	return tx.Commit()
}
