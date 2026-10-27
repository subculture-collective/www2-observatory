package main

import (
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/onnwee/www2-observatory/internal/api"
	"github.com/onnwee/www2-observatory/internal/backup"
	"github.com/onnwee/www2-observatory/internal/config"
	"github.com/onnwee/www2-observatory/internal/db"
	"github.com/onnwee/www2-observatory/internal/ingest"
	"github.com/onnwee/www2-observatory/internal/privacy"
)

func main() {
	if err := run(os.Args[1:]); err != nil {
		slog.Error("observatory failed", "error", err)
		os.Exit(1)
	}
}

func run(args []string) error {
	fs := flag.NewFlagSet("www2-observatory", flag.ExitOnError)
	bind := fs.String("bind", "", "Address to bind to")
	port := fs.Int("port", 0, "Port to listen on")
	if err := fs.Parse(args); err != nil {
		return err
	}

	cfg := config.Load()
	if *bind != "" {
		cfg.Bind = *bind
	}
	if *port != 0 {
		cfg.Port = *port
	}

	cmd := "run"
	if fs.NArg() > 0 {
		cmd = fs.Arg(0)
	}
	if cmd == "healthcheck" {
		return healthcheck(cfg)
	}
	if cmd == "backup" {
		return backup.Run(fs.Args()[1:])
	}

	conn, err := db.Connect(cfg.DBPath)
	if err != nil {
		return err
	}
	if err := db.RefreshDiagnostics(conn); err != nil {
		conn.Close()
		return err
	}
	if err := conn.Close(); err != nil {
		return err
	}

	key, err := privacy.LoadOrCreateKey(cfg.KeyFile)
	if err != nil {
		return err
	}
	ingestor := ingest.New(cfg, key)

	if cmd == "reconcile-access" {
		counts, err := ingestor.ReconcileAccess()
		if err != nil {
			return err
		}
		return json.NewEncoder(os.Stdout).Encode(counts)
	}
	if cmd == "ingest-once" {
		counts, err := ingestor.IngestOnce()
		if err != nil {
			return err
		}
		return json.NewEncoder(os.Stdout).Encode(counts)
	}

	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()
	ingestDone := make(chan struct{})
	go func() {
		defer close(ingestDone)
		ingestor.Run(ctx)
	}()

	server := &http.Server{
		Addr:              fmt.Sprintf("%s:%d", cfg.Bind, cfg.Port),
		Handler:           api.NewServer(cfg),
		ReadHeaderTimeout: 5 * time.Second,
	}

	go func() {
		<-ctx.Done()
		shutdownCtx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()
		_ = server.Shutdown(shutdownCtx)
	}()

	slog.Info("observatory listening", "url", fmt.Sprintf("http://%s:%d", cfg.Bind, cfg.Port))
	if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
		return err
	}
	<-ingestDone
	return nil
}

func healthcheck(cfg config.Config) error {
	client := http.Client{Timeout: 2 * time.Second}
	resp, err := client.Get(fmt.Sprintf("http://%s:%d/healthz", cfg.Bind, cfg.Port))
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return fmt.Errorf("healthcheck failed: %s", resp.Status)
	}
	return nil
}
