from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading
import time
import pytest

PAYLOAD = b"\x00\x00\x00\x20ftypisom" + bytes(range(256)) * 8192


@pytest.fixture(autouse=True)
def isolate_transport_tests(request, monkeypatch):
    # These synthetic byte fixtures verify transport/state, not multimedia decoding.
    # Native tests and packaged acceptance run the real executables separately.
    if request.node.get_closest_marker("native") is None:
        monkeypatch.setattr("fbmd.engine.ffmpeg_path", lambda: None)


@pytest.fixture
def server():
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            requests.append({"path": self.path, "range": self.headers.get("Range")})
            path = self.path.split("?")[0]
            if path == "/blocked.mp4":
                self.send_response(403)
                self.end_headers()
                return
            if path == "/page":
                data = b'<html><body><a href="/sample.mp4">Video</a><a href="https://www.facebook.com/reel/123456">Reel</a></body></html>'
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return
            if path == "/login":
                data = b'<html><input type="password"><a href="/sample.mp4">Media</a></html>'
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return
            if path == "/html.mp4":
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(b"<html>Log in</html>")
                return
            start = int(
                self.headers.get("Range", "bytes=0-").split("=")[1].split("-")[0]
            )
            ranged = self.headers.get("Range") and path != "/ignore-range.mp4"
            if not ranged:
                start = 0
            self.send_response(206 if ranged else 200)
            self.send_header("Content-Type", "video/mp4")
            self.send_header("ETag", '"fixture-v1"')
            self.send_header("Content-Length", str(len(PAYLOAD) - start))
            if ranged:
                self.send_header(
                    "Content-Range",
                    f"bytes {start + 1 if path == '/bad-range.mp4' else start}-{len(PAYLOAD) - 1}/{len(PAYLOAD)}",
                )
            self.end_headers()
            try:
                for i in range(start, len(PAYLOAD), 16384):
                    self.wfile.write(PAYLOAD[i : i + 16384])
                    self.wfile.flush()
                    if path == "/slow.mp4":
                        time.sleep(0.012)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{httpd.server_port}", requests
    httpd.shutdown()
    thread.join()
