import unittest
from observatory.scoring import assess


class ScoringTests(unittest.TestCase):
    def test_machine_probe_scores_high(self):
        a=assess("OPTIONS","/.well-known/example","curl/8.1","application/json")
        self.assertEqual(a.level,"high")
        self.assertIn("capability-probe",a.signals)

    def test_browser_pageview_low(self):
        a=assess("GET","/","Mozilla/5.0 Chrome/120 Safari/537.36","text/html,application/xhtml+xml")
        self.assertEqual(a.level,"low")


if __name__ == "__main__": unittest.main()
