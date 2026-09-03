"""Agent Town server: static files + a WebSocket RELAY to the pixel office.

Why the relay: the office's standalone /ws only accepts same-origin browsers (it closes
cross-origin sockets with 4003 "forbidden origin") but does accept clients that send NO
Origin header. So the page connects to ws://127.0.0.1:5180/ws (its own origin), and this
server re-sends the upgrade to the office with Origin stripped + Host rewritten, then pipes
bytes both ways. WebSocket frames are relayed verbatim.
Run: python serve.py   → http://127.0.0.1:5180
"""
import json, os, socket, threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
SERVER_JSON = os.path.expanduser(r"~\.pixel-agents\server.json")
PORT = 5180


def office():
    try:
        d = json.load(open(SERVER_JSON))
        return d.get("token", ""), int(d.get("port", 5177))
    except Exception:
        return "", 5177


def pipe(src, dst):
    try:
        while True:
            b = src.recv(65536)
            if not b:
                break
            dst.sendall(b)
    except OSError:
        pass
    finally:
        for s in (src, dst):
            try: s.shutdown(socket.SHUT_RDWR)
            except OSError: pass


class H(SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=HERE, **k)

    def do_GET(self):
        if self.path.startswith("/token.json"):
            token, port = office()
            body = json.dumps({"token": token, "port": port}).encode()
            self.send_response(200); self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store"); self.end_headers(); self.wfile.write(body); return
        if self.path.startswith("/ws") and "upgrade" in (self.headers.get("Connection", "").lower()):
            return self.relay_ws()
        return super().do_GET()

    def relay_ws(self):
        token, port = office()
        up = socket.create_connection(("127.0.0.1", port), timeout=10)
        # rebuild the upgrade request for the office: same path (+token), no Origin, its Host
        path = self.path if "token=" in self.path else (self.path + ("&" if "?" in self.path else "?") + f"token={token}")
        lines = [f"GET {path} HTTP/1.1", f"Host: 127.0.0.1:{port}"]
        for k, v in self.headers.items():
            if k.lower() in ("host", "origin"):
                continue
            lines.append(f"{k}: {v}")
        up.sendall(("\r\n".join(lines) + "\r\n\r\n").encode())
        up.settimeout(None)
        client = self.connection
        client.settimeout(None)
        t = threading.Thread(target=pipe, args=(up, client), daemon=True); t.start()
        pipe(client, up)          # blocks until either side closes
        t.join(timeout=1)
        self.close_connection = True

    def end_headers(self):  # never let the browser cache the town — edits must show on reload
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, *a):  # quiet
        pass


if __name__ == "__main__":
    print(f"[agent-town] http://127.0.0.1:{PORT}  (relaying /ws to the office from {SERVER_JSON})")
    ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
