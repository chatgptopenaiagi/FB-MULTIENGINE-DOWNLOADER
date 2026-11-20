"""Only serves mission-generated media; never browses arbitrary local files."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import time, json

ROOT = Path(__file__).resolve().parents[1]
DATA = (ROOT / ".private/fixture/sample.mp4").read_bytes()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        with (ROOT / ".private/fixture/requests.jsonl").open("a") as f:
            f.write(
                json.dumps(
                    {
                        "path": self.path.split("?")[0],
                        "range": self.headers.get("Range"),
                    }
                )
                + "\n"
            )
        if self.path.startswith("/blocked"):
            self.send_response(403)
            self.end_headers()
            return
        offset = int(self.headers.get("Range", "bytes=0-").split("=")[1].split("-")[0])
        self.send_response(206 if offset else 200)
        self.send_header("Content-Type", "video/mp4")
        self.send_header("Content-Length", str(len(DATA) - offset))
        self.send_header("ETag", '"fixture-v1"')
        if offset:
            self.send_header(
                "Content-Range", f"bytes {offset}-{len(DATA) - 1}/{len(DATA)}"
            )
        self.end_headers()
        try:
            for i in range(offset, len(DATA), 4096):
                self.wfile.write(DATA[i : i + 4096])
                self.wfile.flush()
                if self.path.startswith("/slow"):
                    time.sleep(0.03)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass


ThreadingHTTPServer(("127.0.0.1", 18765), Handler).serve_forever()
