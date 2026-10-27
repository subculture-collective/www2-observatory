package config

import (
	"os"
	"strconv"
)

type Config struct {
	CaddyLog           string
	AllowedHosts       string
	RelayLog           string
	RelayDir           string
	DBPath             string
	KeyFile            string
	Bind               string
	Port               int
	Token              string
	SessionMinutes     int
	ContentMax         int
	PollSeconds        float64
	StaticDir          string
	TrustCaddyClientIP bool
}

func Load() Config {
	return Config{
		CaddyLog:           getenv("OBS_CADDY_LOG", "/logs/access.jsonl"),
		AllowedHosts:       getenv("OBS_ALLOWED_HOSTS", "www2.onnwee.me"),
		RelayLog:           getenv("OBS_RELAY_LOG", ""),
		RelayDir:           getenv("OBS_RELAY_DIR", ""),
		DBPath:             getenv("OBS_DB", defaultStatePath("state/observatory.sqlite3", "/data/observatory.sqlite3")),
		KeyFile:            getenv("OBS_KEY_FILE", defaultStatePath("state/pseudonym.key", "/data/pseudonym.key")),
		Bind:               getenv("OBS_BIND", "127.0.0.1"),
		Port:               getenvInt("OBS_PORT", 9099),
		Token:              getenv("OBS_TOKEN", ""),
		SessionMinutes:     getenvInt("OBS_SESSION_MINUTES", 30),
		ContentMax:         getenvInt("OBS_CONTENT_MAX", 8192),
		PollSeconds:        getenvFloat("OBS_POLL_SECONDS", 1.0),
		StaticDir:          getenv("OBS_STATIC_DIR", "frontend/dist"),
		TrustCaddyClientIP: getenv("OBS_TRUST_CADDY_CLIENT_IP", "false") == "true",
	}
}

func getenv(name, fallback string) string {
	if value := os.Getenv(name); value != "" {
		return value
	}
	return fallback
}

func getenvInt(name string, fallback int) int {
	value, err := strconv.Atoi(getenv(name, strconv.Itoa(fallback)))
	if err != nil {
		return fallback
	}
	return value
}

func getenvFloat(name string, fallback float64) float64 {
	value, err := strconv.ParseFloat(getenv(name, strconv.FormatFloat(fallback, 'f', -1, 64)), 64)
	if err != nil {
		return fallback
	}
	return value
}

func defaultStatePath(local, container string) string {
	if _, err := os.Stat(local); err == nil {
		return local
	}
	return container
}
