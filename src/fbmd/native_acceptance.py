"""Explicit local acceptance checks performed by the actual packaged application."""

import hashlib
import json
from pathlib import Path
import time
from .native import require_runtime, registry, execute, merge_local, inspect_media


def run_checks(destination: Path) -> dict:
    destination = Path(destination).resolve()
    destination.mkdir(parents=True, exist_ok=False)
    runtime = require_runtime()
    start = time.time()
    video, audio = destination / "video.mp4", destination / "audio.m4a"
    commands = [
        [
            runtime["path"],
            "-nostdin",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "testsrc=size=320x180:rate=24",
            "-t",
            "3",
            "-pix_fmt",
            "yuv420p",
            "-c:v",
            "libopenh264",
            str(video),
        ],
        [
            runtime["path"],
            "-nostdin",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:sample_rate=44100",
            "-t",
            "3",
            "-c:a",
            "aac",
            str(audio),
        ],
    ]
    for command in commands:
        if execute(command).returncode:
            raise RuntimeError("Bundled fixture generation failed")
    merged = destination / "merged.mp4"
    info = merge_local(video, audio, merged)
    assert 2.8 <= info["duration"] <= 3.3, info
    starts = [float(s.get("start_time") or 0) for s in info["streams"]]
    assert max(starts) - min(starts) < 0.15
    if execute(
        [
            runtime["path"],
            "-nostdin",
            "-v",
            "error",
            "-xerror",
            "-i",
            str(merged),
            "-f",
            "null",
            "-",
        ]
    ).returncode:
        raise RuntimeError("Merged media decode failed")
    hls = destination / "hls.m3u8"
    if execute(
        [
            runtime["path"],
            "-nostdin",
            "-v",
            "error",
            "-i",
            str(merged),
            "-c",
            "copy",
            "-hls_time",
            "1",
            "-hls_playlist_type",
            "vod",
            str(hls),
        ]
    ).returncode:
        raise RuntimeError("HLS fixture generation failed")
    hls_output = destination / "hls-remux.mp4"
    if execute(
        [
            runtime["path"],
            "-nostdin",
            "-v",
            "error",
            "-protocol_whitelist",
            "file,crypto,data",
            "-i",
            str(hls),
            "-c",
            "copy",
            str(hls_output),
        ]
    ).returncode:
        raise RuntimeError("HLS processing failed")
    hls_info = inspect_media(hls_output)
    assert {"audio", "video"} <= {s["codec_type"] for s in hls_info["streams"]}
    # Drive yt-dlp's real separate-format selection and FFmpeg merger with owned fixture URLs.
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    import threading
    import yt_dlp

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            file = {"/video.mp4": video, "/audio.m4a": audio}.get(self.path)
            if file is None:
                self.send_error(404)
                return
            data = file.read_bytes()
            self.send_response(200)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    processing = []

    class Quiet:
        def debug(self, *args):
            pass

        def warning(self, *args):
            pass

        def error(self, *args):
            pass

    try:
        base = f"http://127.0.0.1:{server.server_port}"
        options = {
            "ffmpeg_location": runtime["path"],
            "outtmpl": str(destination / "selected.%(ext)s"),
            "format": "bv+ba",
            "merge_output_format": "mp4",
            "quiet": True,
            "logger": Quiet(),
            "postprocessor_hooks": [
                lambda data: processing.append(
                    {
                        "processor": data.get("postprocessor"),
                        "status": data.get("status"),
                    }
                )
            ],
        }
        with yt_dlp.YoutubeDL(options) as ydl:
            ydl.process_ie_result(
                {
                    "id": "owned-fixture",
                    "title": "Controlled split streams",
                    "formats": [
                        {
                            "format_id": "v",
                            "url": base + "/video.mp4",
                            "ext": "mp4",
                            "vcodec": "h264",
                            "acodec": "none",
                            "height": 180,
                            "width": 320,
                        },
                        {
                            "format_id": "a",
                            "url": base + "/audio.m4a",
                            "ext": "m4a",
                            "vcodec": "none",
                            "acodec": "aac",
                        },
                    ],
                },
                download=True,
            )
    finally:
        server.shutdown()
        thread.join()
        server.server_close()
    selected = inspect_media(destination / "selected.mp4")
    assert {"audio", "video"} <= {s["codec_type"] for s in selected["streams"]}
    report = {
        "status": "PASS",
        "registry": registry(),
        "separate_stream_merge": info,
        "audio_video_start_difference": max(starts) - min(starts),
        "hls_processing": hls_info,
        "yt_dlp_split_stream_merge": selected,
        "postprocessors": processing,
        "outputs": [],
        "elapsed_seconds": round(time.time() - start, 3),
    }
    for file in (merged, hls_output, destination / "selected.mp4"):
        with file.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        report["outputs"].append(
            {"path": str(file), "bytes": file.stat().st_size, "sha256": digest}
        )
    (destination / "native-acceptance.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    return report
