"""Stable typed Python facade; storage paths are always explicit."""

from pathlib import Path
from .store import Store
from .engine import Worker


class Downloader:
    def __init__(
        self, state_directory: str | Path, media_directory: str | Path
    ) -> None:
        self.store = Store(Path(state_directory), Path(media_directory))

    def enqueue(self, url: str, engine: str = "auto", quality: str = "best") -> int:
        return self.store.enqueue(url, engine, quality)

    def run(self) -> list[dict]:
        Worker(self.store).run()
        return self.store.rows()

    def pause(self, job_id: int | None = None) -> None:
        self.store.pause(job_id)

    def resume(self, job_id: int | None = None) -> None:
        self.store.resume(job_id)

    def cancel(self, job_id: int | None = None) -> None:
        self.store.cancel(job_id)

    def history(self) -> list[dict]:
        return self.store.rows()
