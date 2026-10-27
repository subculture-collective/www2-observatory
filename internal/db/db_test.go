package db

import (
	"path/filepath"
	"testing"
	"time"
)

func TestConcurrentWriterWaitsForIngestion(t *testing.T) {
	path := filepath.Join(t.TempDir(), "observatory.sqlite3")
	writer, err := Connect(path)
	if err != nil {
		t.Fatal(err)
	}
	defer writer.Close()
	reader, err := Connect(path)
	if err != nil {
		t.Fatal(err)
	}
	defer reader.Close()
	tx, err := writer.Begin()
	if err != nil {
		t.Fatal(err)
	}
	defer tx.Rollback()
	if _, err := tx.Exec("INSERT INTO ingest_state(source) VALUES ('first')"); err != nil {
		t.Fatal(err)
	}
	done := make(chan error, 1)
	go func() { done <- SetState(reader, "second", 1, 1) }()
	select {
	case err := <-done:
		t.Fatalf("write returned before the ingestion lock was released: %v", err)
	case <-time.After(100 * time.Millisecond):
	}
	if err := tx.Commit(); err != nil {
		t.Fatal(err)
	}
	select {
	case err := <-done:
		if err != nil {
			t.Fatal(err)
		}
	case <-time.After(6 * time.Second):
		t.Fatal("write did not resume after ingestion committed")
	}
}
