import unittest

from observatory.parsers import parse_caddy_line, parse_relay_line


class ParserTests(unittest.TestCase):
    def test_caddy(self):
        line='''{"ts":1727000000.5,"request":{"host":"WWW2.ONNWEE.ME.:443","remote_ip":"203.0.113.4","method":"GET","uri":"/search?q=coffee","headers":{"User-Agent":["curl/8.0"],"Accept":["application/json"],"Referer":["https://example.org/a?secret=x"]}},"status":200,"size":123}'''
        r=parse_caddy_line(line)
        self.assertIsNotNone(r)
        self.assertEqual(r.host, "www2.onnwee.me")
        self.assertEqual(r.path,"/search")
        self.assertEqual(r.query,"q=coffee")
        self.assertEqual(r.user_agent,"curl/8.0")

    def test_caddy_host_header_fallback(self):
        r = parse_caddy_line('{"request":{"uri":"/","headers":{"Host":["www2.onnwee.me"]}}}')
        self.assertEqual(r.host, "www2.onnwee.me")

    def test_relay(self):
        r=parse_relay_line('{"ts":"2026-09-21T00:00:00Z","event":"note.created","path":"/notes/x","content":"hello"}')
        self.assertEqual(r.event,"note.created")
        self.assertEqual(r.content,"hello")


if __name__ == "__main__": unittest.main()
