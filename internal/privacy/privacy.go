package privacy

import (
	"crypto/hmac"
	"crypto/rand"
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"net/url"
	"os"
	"path/filepath"
	"regexp"
	"strings"
)

var secretPatterns = []*regexp.Regexp{
	regexp.MustCompile(`(?i)(authorization\s*[:=]\s*bearer\s+)[A-Za-z0-9._~+/=-]{12,}`),
	regexp.MustCompile(`(?i)((?:api[_-]?key|token|password|passwd|secret)\s*[:=]\s*)[^\s,;]{8,}`),
	regexp.MustCompile(`-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----[\s\S]*?-----END (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----`),
	regexp.MustCompile(`\b(?:sk|rk|pk)-[A-Za-z0-9_-]{20,}\b`),
}

func LoadOrCreateKey(path string) ([]byte, error) {
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return nil, err
	}
	key, err := os.ReadFile(path)
	if err == nil {
		key = []byte(strings.TrimSpace(string(key)))
		if len(key) >= 32 {
			return key, nil
		}
	} else if !errors.Is(err, os.ErrNotExist) {
		return nil, err
	}
	key = make([]byte, 32)
	if _, err := rand.Read(key); err != nil {
		return nil, err
	}
	file, err := os.OpenFile(path, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0o600)
	if err != nil {
		return nil, err
	}
	defer file.Close()
	if _, err := file.Write(key); err != nil {
		return nil, err
	}
	return key, nil
}

func Pseudonym(key []byte, value, prefix string) string {
	mac := hmac.New(sha256.New, key)
	_, _ = mac.Write([]byte(value))
	digest := hex.EncodeToString(mac.Sum(nil))
	return prefix + "_" + digest[:20]
}

func ScrubText(text string, maxLen int) string {
	if maxLen >= 0 && len(text) > maxLen {
		text = text[:maxLen]
	}
	out := text
	for _, pattern := range secretPatterns {
		out = pattern.ReplaceAllStringFunc(out, func(match string) string {
			groups := pattern.FindStringSubmatch(match)
			if len(groups) > 1 {
				return groups[1] + "[REDACTED]"
			}
			return "[REDACTED]"
		})
	}
	return out
}

func SanitizeReferrer(raw string, ownHosts map[string]bool) (string, string) {
	if raw == "" {
		return "", ""
	}
	parsed, err := url.Parse(raw)
	if err != nil {
		return "", ""
	}
	host := strings.ToLower(parsed.Hostname())
	if !ownHosts[host] {
		parsed.RawQuery = ""
	}
	parsed.Fragment = ""
	clean := parsed.String()
	if len(clean) > 2048 {
		clean = clean[:2048]
	}
	if len(host) > 255 {
		host = host[:255]
	}
	return clean, host
}
