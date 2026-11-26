"""Local preview: serve site/ on http://localhost:8000 and forward /api/* to the live site, so pages show real weather.

Run:  python3 src/preview.py   (after python3 src/build.py)
"""
import http.server, os, ssl, subprocess, sys, urllib.request
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "site")
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
CTX = ssl.create_default_context(cafile="/root/.ccr/ca-bundle.crt") if os.path.exists("/root/.ccr/ca-bundle.crt") else None
def local_nws(rid):
    env = dict(os.environ, NODE_USE_ENV_PROXY="1")
    if os.path.exists("/root/.ccr/ca-bundle.crt"): env["NODE_EXTRA_CA_CERTS"] = "/root/.ccr/ca-bundle.crt"
    p = subprocess.run(["node", "--experimental-strip-types", "--no-warnings", os.path.join(ROOT, "src", "nws_preview.mts"), rid],
                       capture_output=True, env=env, timeout=30)
    return (200 if p.returncode == 0 else 404 if p.returncode == 4 else 503), "application/json", p.stdout
class H(http.server.SimpleHTTPRequestHandler):
    def __init__(s, *a, **k): super().__init__(*a, directory=SITE, **k)
    def log_message(s, *a): pass
    def do_GET(s):
        if s.path.startswith("/api/"):
            status, ctype, body = 502, "application/json", b'{"error":"preview could not reach the live site"}'
            try:
                with urllib.request.urlopen("https://theskiadvisor.com" + s.path, context=CTX, timeout=20) as r:
                    status, ctype, body = r.status, r.headers.get("Content-Type", "application/json"), r.read()
            except urllib.error.HTTPError as e:
                status, ctype, body = e.code, e.headers.get("Content-Type", ""), e.read()
            except Exception:
                pass
            # /api/nws/:id not on the live site yet? Run the same code locally (needs api.weather.gov reachable).
            if s.path.startswith("/api/nws/") and "json" not in ctype:
                status, ctype, body = local_nws(s.path.split("/")[3].split("?")[0])
            s.send_response(status); s.send_header("Content-Type", ctype)
            s.send_header("Content-Length", str(len(body))); s.end_headers(); s.wfile.write(body); return
        super().do_GET()
print(f"Preview: http://localhost:{PORT}  (Ctrl+C to stop)")
http.server.ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
