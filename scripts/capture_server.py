"""Sirve las páginas de 3Dmol.js y recibe los PNG que devuelve el lienzo WebGL.

El volcado de un lienzo pesa varios megabytes en base64; enviarlo por el chat
desperdicia contexto. Con este servidor la página los escribe directamente en
disco mediante POST /save?name=<archivo>.

Uso:  python capture_server.py [complex.json]   (dejar corriendo en segundo plano)
"""
import base64, json, os, sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs


class Handler(SimpleHTTPRequestHandler):
    def do_POST(self):
        query = parse_qs(urlparse(self.path).query)
        name = "".join(c for c in query.get("name", ["captura"])[0]
                       if c.isalnum() or c in "_-") + ".png"
        raw = self.rfile.read(int(self.headers.get("Content-Length", 0))).decode()
        if "," in raw:
            raw = raw.split(",", 1)[1]
        with open(name, "wb") as fh:
            fh.write(base64.b64decode(raw))
        body = b"ok"
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
        sys.stderr.write(f"guardado {name}\n")

    def log_message(self, *args):
        pass


def main(cfg_path="complex.json"):
    port = 8766
    if os.path.exists(cfg_path):
        try:
            port = json.load(open(cfg_path, encoding="utf-8")).get("port", 8766)
        except (ValueError, OSError):
            pass
    print(f"Sirviendo {os.getcwd()} en http://localhost:{port}")
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "complex.json")
