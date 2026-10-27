package ingest

import (
	"compress/gzip"
	"context"
	"crypto/rand"
	"crypto/sha256"
	"database/sql"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log/slog"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"syscall"
	"time"

	"github.com/onnwee/www2-observatory/internal/config"
	"github.com/onnwee/www2-observatory/internal/db"
	"github.com/onnwee/www2-observatory/internal/parsers"
	"github.com/onnwee/www2-observatory/internal/privacy"
	"github.com/onnwee/www2-observatory/internal/research"
	"github.com/onnwee/www2-observatory/internal/scoring"
)

type Ingestor struct {
	cfg          config.Config
	key          []byte
	allowedHosts map[string]bool
}

func New(cfg config.Config, key []byte) *Ingestor {
	allowed := map[string]bool{}
	for _, host := range strings.Split(cfg.AllowedHosts, ",") {
		host = strings.TrimSuffix(strings.ToLower(strings.TrimSpace(host)), ".")
		if host != "" {
			allowed[host] = true
		}
	}
	return &Ingestor{cfg: cfg, key: key, allowedHosts: allowed}
}

func (i *Ingestor) Run(ctx context.Context) {
	interval := time.Duration(i.cfg.PollSeconds * float64(time.Second))
	if interval <= 0 {
		interval = time.Second
	}
	ticker := time.NewTicker(interval)
	defer ticker.Stop()
	for {
		if _, err := i.IngestOnce(); err != nil {
			slog.Warn("ingest failed", "error", err)
		}
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
		}
	}
}

func (i *Ingestor) IngestOnce() (map[string]int, error) {
	counts := map[string]int{"access": 0, "relay": 0}
	conn, err := db.Connect(i.cfg.DBPath)
	if err != nil {
		return counts, err
	}
	defer conn.Close()
	if i.cfg.CaddyLog != "" {
		for _, path := range logFiles(i.cfg.CaddyLog) {
			count, err := i.tailFile(conn, path, "access")
			if err != nil {
				return counts, err
			}
			counts["access"] += count
		}
	}
	if i.cfg.RelayLog != "" {
		count, err := i.tailFile(conn, i.cfg.RelayLog, "relay")
		if err != nil {
			return counts, err
		}
		counts["relay"] = count
	}
	if i.cfg.RelayDir != "" {
		for _, ledger := range []string{"guestbook", "wall", "notes", "files", "events"} {
			count, err := i.tailFile(conn, filepath.Join(i.cfg.RelayDir, ledger+".jsonl"), "ledger:"+ledger)
			if err != nil {
				return counts, err
			}
			counts["relay"] += count
		}
	}
	return counts, nil
}

func logFiles(activePath string) []string {
	active := filepath.Clean(activePath)
	dir, name := filepath.Split(active)
	stem := strings.TrimSuffix(name, filepath.Ext(name))
	suffix := filepath.Ext(name)
	seen := map[string]bool{}
	for _, pattern := range []string{filepath.Join(dir, name+"*"), filepath.Join(dir, stem+"-*"+suffix+"*")} {
		matches, _ := filepath.Glob(pattern)
		for _, match := range matches {
			if info, err := os.Stat(match); err == nil && !info.IsDir() {
				seen[match] = true
			}
		}
	}
	paths := make([]string, 0, len(seen))
	for path := range seen {
		paths = append(paths, path)
	}
	sort.Slice(paths, func(a, b int) bool {
		ai, _ := os.Stat(paths[a])
		bi, _ := os.Stat(paths[b])
		if (paths[a] == active) != (paths[b] == active) {
			return paths[a] != active
		}
		if ai.ModTime() != bi.ModTime() {
			return ai.ModTime().Before(bi.ModTime())
		}
		return paths[a] < paths[b]
	})
	return paths
}

func (i *Ingestor) tailFile(conn *sql.DB, path, kind string) (int, error) {
	info, err := os.Stat(path)
	if errors.Is(err, os.ErrNotExist) {
		return 0, nil
	}
	if err != nil {
		return 0, err
	}
	dev, inode := statIDs(info)
	source := fmt.Sprintf("%s:%d:%d", kind, dev, inode)
	_, offset, err := db.State(conn, source)
	if err != nil {
		return 0, err
	}
	if !strings.HasSuffix(path, ".gz") && info.Size() < offset {
		offset = 0
	}

	file, err := os.Open(path)
	if err != nil {
		return 0, err
	}
	defer file.Close()

	var reader io.Reader = file
	if strings.HasSuffix(path, ".gz") {
		gz, err := gzip.NewReader(file)
		if err != nil {
			return 0, err
		}
		defer gz.Close()
		reader = gz
		offset = 0
	} else if _, err := file.Seek(offset, io.SeekStart); err != nil {
		return 0, err
	}

	lineReader := &offsetLineReader{r: reader, offset: offset}
	count := 0
	for {
		lineOffset := lineReader.offset
		raw, complete, err := lineReader.ReadLine()
		if errors.Is(err, io.EOF) {
			break
		}
		if err != nil {
			return count, err
		}
		if !complete {
			lineReader.offset = lineOffset
			break
		}
		line := string(raw)
		if kind == "access" {
			inserted, err := i.ingestAccess(conn, line, raw)
			if err != nil {
				return count, err
			}
			count += inserted
		} else if strings.HasPrefix(kind, "ledger:") {
			inserted, err := i.ingestLedger(conn, strings.TrimPrefix(kind, "ledger:"), line, raw)
			if err != nil {
				return count, err
			}
			count += inserted
		} else {
			inserted, err := i.ingestRelay(conn, line)
			if err != nil {
				return count, err
			}
			count += inserted
		}
	}
	if err := db.SetState(conn, source, inode, lineReader.offset); err != nil {
		return count, err
	}
	return count, nil
}

func (i *Ingestor) ids(remoteIP, userAgent string) (string, string) {
	if remoteIP == "" {
		remoteIP = "unknown"
	}
	sourceID := privacy.Pseudonym(i.key, remoteIP, "src")
	clientID := privacy.Pseudonym(i.key, remoteIP+"\x00"+userAgent, "cli")
	return sourceID, clientID
}

func (i *Ingestor) ingestAccess(conn *sql.DB, line string, raw []byte) (int, error) {
	rec, err := parsers.ParseCaddyLineWithPolicy(line, i.cfg.TrustCaddyClientIP)
	if err != nil || rec == nil || !i.allowedHosts[rec.Host] {
		return 0, nil
	}
	hash := sha256.Sum256(raw)
	eventKey := hex.EncodeToString(hash[:])
	sourceID, clientID := i.ids(rec.RemoteIP, rec.UserAgent)
	sessionID, err := db.LastSession(conn, clientID, rec.TS, i.cfg.SessionMinutes*60)
	if err != nil {
		return 0, err
	}
	if sessionID == "" {
		sessionID = "ses_" + randomHex(8)
	}
	assessment := scoring.Assess(rec.Method, rec.Path, rec.UserAgent, rec.Accept)
	cleanRef, refHost := privacy.SanitizeReferrer(rec.Referer, map[string]bool{"www2.onnwee.me": true, "onnwee.me": true})
	signals, _ := json.Marshal(assessment.Signals)
	trafficClass, reason := research.Classify(rec)
	result, err := conn.Exec(`INSERT OR IGNORE INTO access_events(
                ts,host,event_key,source_id,client_id,session_id,method,path,query,status,user_agent,accept_header,
                referer,referer_host,content_type,response_bytes,automation_score,automation_level,signals_json,attribution,traffic_class,classification_reason,write_object,successful_write,link_write
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)`,
		rec.TS, rec.Host, eventKey, sourceID, clientID, sessionID, strings.ToUpper(rec.Method), truncate(rec.Path, 2048), truncate(rec.Query, 2048),
		rec.Status, truncate(rec.UserAgent, 1024), truncate(rec.Accept, 1024), cleanRef, refHost, truncate(rec.ContentType, 255), rec.Size, assessment.Score, assessment.Level, string(signals), rec.Attribution, trafficClass, reason, research.WriteObject(rec), research.SuccessfulWrite(rec), research.LinkWriteParam(rec),
	)
	if err != nil {
		return 0, err
	}
	rows, _ := result.RowsAffected()
	return int(rows), nil
}

func (i *Ingestor) ingestRelay(conn *sql.DB, line string) (int, error) {
	rec, err := parsers.ParseRelayLine(line)
	if err != nil || rec == nil {
		return 0, nil
	}
	sourceID, clientID := "", ""
	if rec.RemoteIP != "" || rec.UserAgent != "" {
		sourceID, clientID = i.ids(rec.RemoteIP, rec.UserAgent)
	}
	content := privacy.ScrubText(rec.Content, i.cfg.ContentMax)
	digest := ""
	if rec.Content != "" {
		hash := sha256.Sum256([]byte(rec.Content))
		digest = hex.EncodeToString(hash[:])
	}
	metadata, _ := json.Marshal(rec.Metadata)
	_, err = conn.Exec("INSERT INTO relay_events(ts,event,path,source_id,client_id,content,content_hash,metadata_json) VALUES(?,?,?,?,?,?,?,?)",
		rec.TS, truncate(rec.Event, 128), truncate(rec.Path, 2048), sourceID, clientID, content, digest, truncate(string(metadata), 8192))
	if err != nil {
		return 0, err
	}
	return 1, nil
}

// ingestLedger stores one relay ledger line as a relay event. The line hash is
// the event key, so re-syncing or re-reading a file never duplicates rows.
func (i *Ingestor) ingestLedger(conn *sql.DB, ledger, line string, raw []byte) (int, error) {
	rec, err := parsers.ParseRelayLedgerLine(ledger, line)
	if err != nil || rec == nil {
		return 0, nil
	}
	hash := sha256.Sum256(raw)
	key := ledger + ":" + hex.EncodeToString(hash[:])
	content := privacy.ScrubText(rec.Content, i.cfg.ContentMax)
	digest := ""
	if rec.Content != "" {
		h := sha256.Sum256([]byte(rec.Content))
		digest = hex.EncodeToString(h[:])
	}
	metadata, _ := json.Marshal(rec.Metadata)
	result, err := conn.Exec("INSERT OR IGNORE INTO relay_events(ts,event,path,source_id,client_id,content,content_hash,metadata_json,event_key) VALUES(?,?,?,?,?,?,?,?,?)",
		rec.TS, truncate(rec.Event, 128), truncate(rec.Path, 2048), "", "", content, digest, truncate(string(metadata), 8192), key)
	if err != nil {
		return 0, err
	}
	n, _ := result.RowsAffected()
	return int(n), nil
}

func randomHex(n int) string {
	buf := make([]byte, n)
	_, _ = rand.Read(buf)
	return hex.EncodeToString(buf)
}

func truncate(value string, max int) string {
	if len(value) > max {
		return value[:max]
	}
	return value
}

func statIDs(info os.FileInfo) (int64, int64) {
	if stat, ok := info.Sys().(*syscall.Stat_t); ok {
		return int64(stat.Dev), int64(stat.Ino)
	}
	return 0, info.ModTime().UnixNano()
}

type offsetLineReader struct {
	r      io.Reader
	offset int64
	buf    []byte
}

func (r *offsetLineReader) ReadLine() ([]byte, bool, error) {
	line := []byte{}
	var one [1]byte
	for {
		n, err := r.r.Read(one[:])
		if n > 0 {
			r.offset++
			line = append(line, one[0])
			if one[0] == '\n' {
				return line, true, nil
			}
		}
		if err != nil {
			if errors.Is(err, io.EOF) && len(line) > 0 {
				return line, false, nil
			}
			return nil, false, err
		}
	}
}
