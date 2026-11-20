"""Create test media, requiring an existing FFmpeg or imageio-ffmpeg dev package."""

from pathlib import Path
import shutil
import subprocess

root = Path(__file__).resolve().parents[1]
target = root / ".private/fixture/sample.mp4"
target.parent.mkdir(parents=True, exist_ok=True)
ffmpeg = shutil.which("ffmpeg")
if not ffmpeg:
    import imageio_ffmpeg

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
if not target.exists():
    subprocess.run(
        [
            ffmpeg,
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "testsrc=size=320x180:rate=24",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:sample_rate=44100",
            "-t",
            "6",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-movflags",
            "+faststart",
            str(target),
        ],
        check=True,
    )
print("GENERATED_FIXTURE_READY", target.stat().st_size)
