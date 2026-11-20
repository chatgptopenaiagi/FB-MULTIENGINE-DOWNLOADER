from __future__ import annotations
import argparse
import getpass
import json
import os
from pathlib import Path
import sys
from platformdirs import user_data_dir
from . import __version__
from .store import Store
from .engine import Worker, ffmpeg_path


def defaults():
    state = Path(
        os.environ.get("FBMD_STATE", user_data_dir("FBMultiEngine", "DragonHydra"))
    )
    media = Path(
        os.environ.get(
            "FBMD_MEDIA",
            r"F:\AILAB\FB-MULTIENGINE-DOWNLOADER"
            if Path("F:/AILAB").exists()
            else str(Path.home() / "Downloads" / "FBMultiEngine"),
        )
    )
    return state, media


def main(argv=None):
    default_state, default_media = defaults()
    parser = argparse.ArgumentParser(
        description="Local Facebook and direct-media downloader. Only use sources you may access and download."
    )
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--state", type=Path, default=default_state)
    parser.add_argument("--media", type=Path, default=default_media)
    parser.add_argument("--account", default="default")
    sub = parser.add_subparsers(dest="command", required=True)
    add = sub.add_parser("add")
    add.add_argument("urls", nargs="*")
    add.add_argument("--file", type=Path)
    add.add_argument("--engine", choices=["auto", "http", "yt-dlp"], default="auto")
    run = sub.add_parser("run")
    run.add_argument("--watch", action="store_true")
    for name in ("pause", "resume", "cancel"):
        p = sub.add_parser(name)
        p.add_argument("id", type=int, nargs="?")
    for name in (
        "list",
        "queue",
        "history",
        "diagnostics",
        "doctor",
        "forget",
        "token",
        "gui",
    ):
        sub.add_parser(name)
    login = sub.add_parser("login")
    login.add_argument("--save-session", action="store_true")
    accounts = sub.add_parser("accounts")
    accounts.add_argument("action", choices=["status"])
    export = sub.add_parser("export")
    export.add_argument("path", type=Path)
    download = sub.add_parser("download")
    download.add_argument("urls", nargs="+")
    download.add_argument(
        "--quality",
        choices=["best", "1080", "720", "480", "360", "mp4"],
        default="best",
    )
    serve = sub.add_parser("serve")
    serve.add_argument("--port", type=int, default=8765)
    api_token = sub.add_parser("api-token")
    api_token.add_argument("--reveal", action="store_true")
    discovery = sub.add_parser("discover")
    discovery.add_argument("url")
    discovery.add_argument(
        "--engine", choices=["playwright", "selenium"], default="playwright"
    )
    discovery.add_argument("--rounds", type=int, default=5)
    discovery.add_argument("--enqueue", action="store_true")
    meta = sub.add_parser("meta")
    meta.add_argument("object_id")
    meta.add_argument("--api-version", default="v27.0")
    meta.add_argument("--enqueue", action="store_true")
    if argv is None:
        argv = sys.argv[1:]
    if argv == ["help"]:
        parser.print_help()
        return 0
    args = parser.parse_args(argv)
    try:
        import re

        if not re.fullmatch("[A-Za-z0-9-]{1,40}", args.account):
            raise ValueError("Invalid account label")
        if args.account != "default":
            args.state = args.state / "accounts" / args.account
            args.media = args.media / args.account
        if args.command == "gui":
            from .gui import main as gui_main

            gui_main(args.state, args.media)
            return 0
        store = Store(args.state, args.media)
        result = {}
        if args.command == "add":
            from .manifest import import_urls

            urls = args.urls + (import_urls(args.file) if args.file else [])
            if len(urls) > 1000:
                raise ValueError("Batch limit exceeded")
            result = {
                "jobs": [
                    store.enqueue(u, args.engine)
                    for u in urls
                    if u.strip() and not u.lstrip().startswith("#")
                ]
            }
        elif args.command == "run":
            worker = Worker(store)
            try:
                worker.run(args.watch)
            except KeyboardInterrupt:
                worker.stop.set()
                store.pause()
            result = {"jobs": store.rows()}
        elif args.command in ("list", "queue", "history"):
            result = store.rows()
        elif args.command == "accounts":
            from .accounts import status

            result = status(store)
        elif args.command == "export":
            from .manifest import export_manifest

            export_manifest(store, args.path)
            result = {"exported": str(args.path)}
        elif args.command == "download":
            if len(args.urls) > 1000:
                raise ValueError("Batch limit exceeded")
            for url in args.urls:
                store.enqueue(url, quality=args.quality)
            Worker(store).run()
            result = {"jobs": store.rows()}
        elif args.command in ("serve", "api-token"):
            import secrets

            token = store.vault.get("api-token")
            if not token:
                token = secrets.token_urlsafe(32)
                store.vault.put("api-token", token)
            if args.command == "api-token":
                result = (
                    {"token": token}
                    if args.reveal
                    else {
                        "status": "stored encrypted; --reveal explicitly displays the local API token"
                    }
                )
            else:
                from .api import create_app
                import uvicorn

                uvicorn.run(
                    create_app(store, token),
                    host="127.0.0.1",
                    port=args.port,
                    access_log=False,
                )
                return 0
        elif args.command == "diagnostics":
            result = store.diagnostics()
        elif args.command == "doctor":
            import importlib.metadata

            result = {
                "version": __version__,
                "python": sys.version.split()[0],
                "ffmpeg": bool(ffmpeg_path()),
                "engines": {
                    name: importlib.metadata.version(name)
                    for name in ("yt-dlp", "requests", "cryptography")
                },
                "vault": "Windows DPAPI" if os.name == "nt" else "OS keyring",
            }
        elif args.command in ("pause", "resume", "cancel"):
            getattr(store, args.command)(args.id)
            result = {"status": args.command}
        elif args.command == "discover":
            from .discovery import discover

            result = discover(store, args.url, args.engine, args.rounds)
            if args.enqueue:
                result["jobs"] = [store.enqueue(u) for u in result["urls"]]
            # Do not print signed CDN URLs in terminal diagnostics.
            from .security import safe_url

            result["urls"] = [safe_url(u) for u in result["urls"]]
        elif args.command == "meta":
            from .discovery import meta_lookup

            result = meta_lookup(store, args.object_id, args.api_version)
            if args.enqueue:
                result["jobs"] = [store.enqueue(u, "http") for u in result["urls"]]
            from .security import safe_url

            result["urls"] = [safe_url(u) for u in result["urls"]]
        elif args.command == "login":
            from .discovery import sign_in

            result = {
                "authenticated": sign_in(store, save_session=args.save_session),
                "save_requested": args.save_session,
            }
        elif args.command == "token":
            token = getpass.getpass("Meta access token (hidden): ")
            if not token.strip():
                raise ValueError("Empty token")
            store.vault.put("meta-token", token.strip())
            result = {"saved": True}
        elif args.command == "forget":
            store.vault.forget()
            result = {"forgotten": True}
        print(json.dumps(result, indent=2))
        if args.command in ("run", "download") and any(
            j["status"] in ("failed", "blocked") for j in result["jobs"]
        ):
            return 2
        if isinstance(result, dict) and result.get("status") in (
            "error",
            "blocked",
            "unsupported",
        ):
            return 2
        return 0
    except Exception as e:
        print(
            json.dumps(
                {
                    "error": type(e).__name__,
                    "detail": "Operation failed. Check input, state directory, dependencies and permissions.",
                }
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
