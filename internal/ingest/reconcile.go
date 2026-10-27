package ingest

import (
	"bufio"
	"compress/gzip"
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"io"
	"os"
	"strings"
	"time"

	"github.com/onnwee/www2-observatory/internal/db"
	"github.com/onnwee/www2-observatory/internal/parsers"
	"github.com/onnwee/www2-observatory/internal/privacy"
	"github.com/onnwee/www2-observatory/internal/research"
)

// ReconcileAccess is an explicit, offline migration. It only updates exact raw-log
// hash matches; original IDs and unrecoverable records remain available for audit.
func (i *Ingestor) ReconcileAccess() (map[string]int, error) {
	if !i.cfg.TrustCaddyClientIP {
		return nil, fmt.Errorf("reconciliation requires verified OBS_TRUST_CADDY_CLIENT_IP=true")
	}
	conn, err := db.Connect(i.cfg.DBPath)
	if err != nil {
		return nil, err
	}
	defer conn.Close()
	tx, err := conn.Begin()
	if err != nil {
		return nil, err
	}
	defer tx.Rollback()
	matched := map[string]bool{}
	for _, path := range logFiles(i.cfg.CaddyLog) {
		f, err := os.Open(path)
		if err != nil {
			return nil, err
		}
		var reader io.Reader = f
		var gz *gzip.Reader
		if strings.HasSuffix(path, ".gz") {
			gz, err = gzip.NewReader(f)
			if err != nil {
				f.Close()
				return nil, err
			}
			reader = gz
		}
		br := bufio.NewReader(reader)
		for {
			raw, readErr := br.ReadBytes('\n')
			if readErr != nil {
				if readErr != io.EOF {
					f.Close()
					return nil, readErr
				}
				break
			}
			rec, parseErr := parsers.ParseCaddyLineWithPolicy(string(raw), true)
			if parseErr != nil || !i.allowedHosts[rec.Host] {
				continue
			}
			hash := sha256.Sum256(raw)
			key := hex.EncodeToString(hash[:])
			source, client := i.ids(rec.RemoteIP, rec.UserAgent)
			class, reason := research.Classify(rec)
			result, err := tx.Exec(`UPDATE access_events SET
    original_source_id=CASE WHEN original_source_id='' THEN source_id ELSE original_source_id END,
    original_client_id=CASE WHEN original_client_id='' THEN client_id ELSE original_client_id END,
    original_session_id=CASE WHEN original_session_id='' THEN session_id ELSE original_session_id END,
    source_id=?,client_id=?,attribution=?,traffic_class=?,classification_reason=?,write_object=?,successful_write=?,link_write=?
    WHERE event_key=?`, source, client, rec.Attribution, class, reason, research.WriteObject(rec), research.SuccessfulWrite(rec), research.LinkWriteParam(rec), key)
			if err != nil {
				f.Close()
				return nil, err
			}
			n, _ := result.RowsAffected()
			if n > 0 {
				matched[key] = true
			}
		}
		if gz != nil {
			gz.Close()
		}
		f.Close()
	}
	rows, err := tx.Query("SELECT id,ts,client_id,event_key FROM access_events WHERE attribution='caddy-client-v2' ORDER BY client_id,ts,id")
	if err != nil {
		return nil, err
	}
	type event struct {
		id          int64
		ts          float64
		client, key string
	}
	var events []event
	for rows.Next() {
		var e event
		if err := rows.Scan(&e.id, &e.ts, &e.client, &e.key); err != nil {
			rows.Close()
			return nil, err
		}
		events = append(events, e)
	}
	if err := rows.Err(); err != nil {
		rows.Close()
		return nil, err
	}
	rows.Close()
	// Stable session IDs make replay idempotent and preserve chronological gaps.
	lastClient, session := "", ""
	lastTS := float64(0)
	for _, e := range events {
		if e.client != lastClient || e.ts-lastTS > float64(i.cfg.SessionMinutes*60) {
			session = privacy.Pseudonym(i.key, e.client+"\x00"+e.key, "ses")
		}
		if _, err := tx.Exec("UPDATE access_events SET session_id=? WHERE id=?", session, e.id); err != nil {
			return nil, err
		}
		lastClient, lastTS = e.client, e.ts
	}
	var total int
	if err := tx.QueryRow("SELECT COUNT(*) FROM access_events").Scan(&total); err != nil {
		return nil, err
	}
	if _, err := tx.Exec("INSERT INTO measurement_runs(completed_at,revision,matched_records) VALUES(?,?,?)", float64(time.Now().Unix()), "caddy-client-v2", len(matched)); err != nil {
		return nil, err
	}
	if err := tx.Commit(); err != nil {
		return nil, err
	}
	return map[string]int{"matched": len(matched), "total": total, "unmatched": total - len(matched)}, nil
}
