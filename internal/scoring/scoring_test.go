package scoring

import "testing"

func TestMachineProbeScoresHigh(t *testing.T) {
	a := Assess("OPTIONS", "/.well-known/example", "curl/8.1", "application/json")
	if a.Level != "high" {
		t.Fatalf("level = %s, want high", a.Level)
	}
	found := false
	for _, signal := range a.Signals {
		found = found || signal == "capability-probe"
	}
	if !found {
		t.Fatalf("capability-probe missing from %#v", a.Signals)
	}
}

func TestBrowserPageviewLow(t *testing.T) {
	a := Assess("GET", "/", "Mozilla/5.0 Chrome/120 Safari/537.36", "text/html,application/xhtml+xml")
	if a.Level != "low" {
		t.Fatalf("level = %s, want low", a.Level)
	}
}
