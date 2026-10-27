package backup

import (
	"database/sql"
	"flag"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"sort"
	"time"

	_ "modernc.org/sqlite"
)

func Run(args []string) error {
	fs := flag.NewFlagSet("backup", flag.ExitOnError)
	stateDir := fs.String("state", "state", "Directory containing observatory.sqlite3 and pseudonym.key")
	outputDir := fs.String("output", "backups", "Directory for timestamped backup snapshots")
	keep := fs.Int("keep", 14, "Number of snapshots to keep")
	if err := fs.Parse(args); err != nil {
		return err
	}

	stamp := time.Now().UTC().Format("20060102T150405Z")
	destination := filepath.Join(*outputDir, stamp)
	if err := os.MkdirAll(destination, 0o755); err != nil {
		return err
	}

	sourceDB := filepath.Join(*stateDir, "observatory.sqlite3")
	keyFile := filepath.Join(*stateDir, "pseudonym.key")
	if err := requireFile(sourceDB); err != nil {
		return err
	}
	if err := requireFile(keyFile); err != nil {
		return err
	}

	backupDB := filepath.Join(destination, "observatory.sqlite3")
	conn, err := sql.Open("sqlite", sourceDB)
	if err != nil {
		return err
	}
	defer conn.Close()
	if _, err := conn.Exec("VACUUM main INTO ?", backupDB); err != nil {
		return err
	}
	backupConn, err := sql.Open("sqlite", backupDB)
	if err != nil {
		return err
	}
	defer backupConn.Close()
	var integrity string
	if err := backupConn.QueryRow("PRAGMA integrity_check").Scan(&integrity); err != nil {
		return err
	}
	if integrity != "ok" {
		return fmt.Errorf("backup integrity check failed: %s", integrity)
	}
	if err := copyFile(keyFile, filepath.Join(destination, "pseudonym.key")); err != nil {
		return err
	}
	if err := os.WriteFile(filepath.Join(destination, "VERIFIED"), []byte("created="+stamp+"\nintegrity=ok\n"), 0o644); err != nil {
		return err
	}
	if err := pruneSnapshots(*outputDir, *keep); err != nil {
		return err
	}
	fmt.Println(destination)
	return nil
}

func requireFile(path string) error {
	info, err := os.Stat(path)
	if err != nil {
		return err
	}
	if info.IsDir() {
		return fmt.Errorf("%s is a directory", path)
	}
	return nil
}

func copyFile(src, dst string) error {
	in, err := os.Open(src)
	if err != nil {
		return err
	}
	defer in.Close()
	out, err := os.OpenFile(dst, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0o600)
	if err != nil {
		return err
	}
	defer out.Close()
	_, err = io.Copy(out, in)
	return err
}

func pruneSnapshots(outputDir string, keep int) error {
	if keep < 1 {
		keep = 1
	}
	entries, err := os.ReadDir(outputDir)
	if err != nil {
		return err
	}
	dirs := []string{}
	for _, entry := range entries {
		if entry.IsDir() {
			dirs = append(dirs, filepath.Join(outputDir, entry.Name()))
		}
	}
	sort.Strings(dirs)
	for _, expired := range dirs[:max(0, len(dirs)-keep)] {
		if err := os.RemoveAll(expired); err != nil {
			return err
		}
	}
	return nil
}
