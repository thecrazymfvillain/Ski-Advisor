"""Local preview: serve site/ on http://localhost:8000 and forward /api/* to the live site, so pages show real weather.

Run:  python3 src/preview.py   (after python3 src/build.py)
"""
import http.server, os, ssl, sys, urllib.request
SITE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "site")
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
CTX = ssl.create_default_context(cafile="/root/.ccr/ca-bundle.crt") if os.path.exists("/root/.ccr/ca-bundle.crt") else None
class H(http.server.SimpleHTTPRequestHandler):
    def __init__(s, *a, **k): super().__init__(*a, directory=SITE, **k)
    def log_message(s, *a): pass
    def do_GET(s):
        if s.path.startswith("/api/"):
            try:
                with urllib.request.urlopen("https://theskiadvisor.com" + s.path, context=CTX, timeout=20) as r:
                    body = r.read(); s.send_response(r.status); s.send_header("Content-Type", r.headers.get("Content-Type", "application/json"))
            except urllib.error.HTTPError as e:
                body = e.read(); s.send_response(e.code); s.send_header("Content-Type", "application/json")
            s.send_header("Content-Length", str(len(body))); s.end_headers(); s.wfile.write(body); return
        super().do_GET()
print(f"Preview: http://localhost:{PORT}  (Ctrl+C to stop)")
http.server.ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
