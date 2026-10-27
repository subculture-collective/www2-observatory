package privacy

import "testing"

func TestPseudonymDeterministic(t *testing.T) {
	key := []byte("xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
	one := Pseudonym(key, "203.0.113.4", "src")
	two := Pseudonym(key, "203.0.113.4", "src")
	if one != two || one != "src_fcd743269a38f7d35f1f" {
		t.Fatalf("pseudonym = %q / %q", one, two)
	}
}

func TestSanitizeReferrer(t *testing.T) {
	clean, host := SanitizeReferrer("https://example.org/a?secret=x", map[string]bool{"www2.onnwee.me": true})
	if clean != "https://example.org/a" || host != "example.org" {
		t.Fatalf("clean=%q host=%q", clean, host)
	}
}
