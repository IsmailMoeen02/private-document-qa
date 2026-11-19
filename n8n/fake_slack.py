"""A stand-in for a Slack incoming webhook, so the n8n alert step makes a real HTTP call that can be seen. Logs each message to fake_slack.log."""
import json, sys
from http.server import BaseHTTPRequestHandler, HTTPServer
LOG = sys.argv[2] if len(sys.argv) > 2 else "fake_slack.log"
class H(BaseHTTPRequestHandler):
    def do_POST(self):
        n = int(self.headers.get("content-length", 0)); body = self.rfile.read(n).decode()
        open(LOG, "a").write(body + "\n"); self.send_response(200); self.end_headers(); self.wfile.write(b"ok")
    def log_message(self, *a): pass
HTTPServer(("127.0.0.1", int(sys.argv[1]) if len(sys.argv) > 1 else 8799), H).serve_forever()
