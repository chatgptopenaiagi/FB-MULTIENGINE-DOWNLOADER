from __future__ import annotations
import json
import os
from pathlib import Path
import queue
import shutil
import sys
import threading
from PySide6.QtCore import QTimer, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QPlainTextEdit,
    QComboBox,
    QTableWidget,
    QTableWidgetItem,
    QListWidget,
    QStackedWidget,
    QLineEdit,
    QCheckBox,
    QFileDialog,
    QInputDialog,
    QHeaderView,
)
from .store import Store
from .engine import Worker
from .native import multimedia, registry
from .cli import defaults
from .manifest import import_urls, export_manifest

STYLE = """
QWidget { background:#101827; color:#e9f0fb; font-family:Segoe UI; font-size:13px; }
QLabel#brand { font-size:26px; font-weight:700; }
QLabel#sub { color:#a6b6ce; }
QPushButton { background:#26374f; border:0; border-radius:6px; padding:10px 14px; }
QPushButton:hover { background:#365373; }
QPushButton#accent { background:#147c75; }
QPlainTextEdit,QLineEdit,QComboBox { background:#19263a; border:1px solid #34445c; border-radius:5px; padding:8px; }
QTableWidget { background:#19263a; alternate-background-color:#1d2b41; gridline-color:#2d3b51; border:0; }
QHeaderView::section { background:#26374f; color:#bed0e8; border:0; padding:9px; }
QListWidget { background:#0c1320; border:0; padding:8px; }
QListWidget::item { padding:13px 9px; border-radius:6px; }
QListWidget::item:selected { background:#24546c; }
QCheckBox { padding:8px 0; }
"""


class Window(QMainWindow):
    def __init__(self, state: Path, media: Path):
        super().__init__()
        self.state_root = state
        state.mkdir(parents=True, exist_ok=True)
        self.settings_file = state / "settings.json"
        self.settings = {}
        if self.settings_file.is_file():
            try:
                self.settings = json.loads(
                    self.settings_file.read_text(encoding="utf-8")
                )
                media = Path(self.settings.get("media", str(media)))
                configured = self.settings.get("ffmpeg")
                if configured and Path(configured).is_file():
                    os.environ["FBMD_FFMPEG"] = configured
            except (ValueError, OSError, TypeError):
                self.settings = {}
        self.media = media
        self.store = Store(state, media)
        self.worker = None
        self.thread = None
        self.messages = queue.Queue()
        self.discovered = []
        self.setWindowTitle("FB MultiEngine Downloader")
        self.resize(1320, 840)
        self.setMinimumSize(1060, 720)
        base = QWidget()
        self.setCentralWidget(base)
        outer = QHBoxLayout(base)
        outer.setContentsMargins(0, 0, 0, 0)
        self.nav = QListWidget()
        self.nav.addItems(
            [
                "Home",
                "Sources",
                "Queue",
                "History",
                "Accounts",
                "Meta API",
                "Engine Control",
                "Diagnostics",
                "Settings",
                "Help",
            ]
        )
        self.nav.setFixedWidth(175)
        outer.addWidget(self.nav)
        right = QWidget()
        layout = QVBoxLayout(right)
        layout.setContentsMargins(25, 22, 25, 20)
        layout.setSpacing(12)
        outer.addWidget(right)
        brand = QLabel("FB MULTIENGINE")
        brand.setObjectName("brand")
        layout.addWidget(brand)
        sub = QLabel("Local downloads. Persistent history. Clear access boundaries.")
        sub.setObjectName("sub")
        layout.addWidget(sub)
        self.stack = QStackedWidget()
        layout.addWidget(self.stack, 1)
        self.status = QLabel(
            "Ready · paste accessible links or discover a Facebook source."
        )
        self.status.setWordWrap(True)
        self.status.setObjectName("sub")
        layout.addWidget(self.status)
        self.build_home()
        self.build_sources()
        self.build_table_page("Queue")
        self.build_table_page("History")
        self.build_accounts()
        self.build_meta()
        self.build_engines()
        self.build_diagnostics()
        self.build_settings()
        self.build_help()
        self.nav.currentRowChanged.connect(self.navigate)
        self.nav.setCurrentRow(0)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(500)
        self.doctor()

    def page(self, title):
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(0, 10, 0, 0)
        l.setSpacing(12)
        h = QLabel(title)
        h.setStyleSheet("font-size:18px;font-weight:600")
        l.addWidget(h)
        self.stack.addWidget(w)
        return l

    def button(self, layout, text, fn, accent=False):
        b = QPushButton(text)
        b.clicked.connect(fn)
        if accent:
            b.setObjectName("accent")
        layout.addWidget(b)
        return b

    def row(self, layout):
        r = QHBoxLayout()
        layout.addLayout(r)
        return r

    def text(self, layout, value):
        l = QLabel(value)
        l.setWordWrap(True)
        layout.addWidget(l)
        return l

    def background(self, fn):
        def run():
            try:
                fn()
            except Exception as e:
                self.messages.put(
                    type(e).__name__
                    + ": operation failed. Check source access, dependencies and diagnostics."
                )

        threading.Thread(target=run, daemon=True).start()

    def build_home(self):
        l = self.page("Download workspace")
        self.urls = QPlainTextEdit()
        self.urls.setPlaceholderText(
            "Paste one Facebook video, Reel, fb.watch or direct-media URL per line"
        )
        self.urls.setMaximumHeight(100)
        l.addWidget(self.urls)
        r = self.row(l)
        self.engine = QComboBox()
        self.engine.addItems(["auto", "http", "yt-dlp"])
        r.addWidget(self.engine)
        self.quality = QComboBox()
        self.quality.addItems(["best", "1080", "720", "480", "360", "mp4"])
        self.quality.setToolTip(
            "Resolution ceilings apply only when the source exposes compatible formats."
        )
        r.addWidget(self.quality)
        self.button(r, "Add URLs", self.add, True)
        self.button(r, "Import CSV / TXT", self.import_list)
        self.button(r, "Discover sources", self.scan_input)
        self.summary = QLabel()
        l.addWidget(self.summary)
        self.tables = {}
        self.make_table(l, "Home")
        self.actions(l)

    def make_table(self, l, name):
        table = QTableWidget(0, 10)
        table.setHorizontalHeaderLabels(
            [
                "ID",
                "Status",
                "Progress",
                "Speed",
                "Engine",
                "Quality",
                "Title / source",
                "Retries",
                "Path",
                "Container / codecs",
            ]
        )
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setSectionResizeMode(6, QHeaderView.Stretch)
        for col, width in enumerate([40, 85, 130, 85, 70, 60, 250, 55, 180]):
            table.setColumnWidth(col, width)
        table.itemSelectionChanged.connect(self.details)
        l.addWidget(table, 1)
        self.tables[name] = table

    def build_table_page(self, name):
        l = self.page(name)
        self.make_table(l, name)
        self.actions(l)

    def actions(self, l):
        r = self.row(l)
        for label, fn in [
            ("Start", self.start),
            ("Pause", lambda: self.control("pause")),
            ("Resume / retry", lambda: self.control("resume")),
            ("Cancel", lambda: self.control("cancel")),
            ("Open folder", self.open_media),
            ("Export", self.export),
        ]:
            self.button(r, label, fn, label == "Start")

    def build_sources(self):
        l = self.page("Sources and discovery")
        self.source_urls = QPlainTextEdit()
        self.source_urls.setPlaceholderText(
            "One profile / Page URL per line. Parameters such as ?id=...&sk=reels_tab are preserved."
        )
        self.source_urls.setMaximumHeight(100)
        l.addWidget(self.source_urls)
        r = self.row(l)
        self.discovery_engine = QComboBox()
        self.discovery_engine.addItems(["playwright", "selenium"])
        r.addWidget(self.discovery_engine)
        self.rounds = QComboBox()
        self.rounds.addItems(["20", "50", "100", "200", "5"])
        r.addWidget(self.rounds)
        self.dryrun = QCheckBox("Index only")
        self.dryrun.setChecked(True)
        r.addWidget(self.dryrun)
        self.button(r, "Scan / re-scan", self.scan_sources, True)
        self.button(r, "Queue discovered", self.queue_discovered)
        self.source_results = QPlainTextEdit()
        self.source_results.setReadOnly(True)
        l.addWidget(self.source_results, 1)
        self.text(
            l,
            "Scanning stops after five passes without new links or the configured limit. Coverage is partial; login walls and challenges stop the scan. Metadata filters are unavailable when the source supplies no verified metadata.",
        )

    def build_accounts(self):
        l = self.page("Accounts and encrypted sessions")
        r = self.row(l)
        self.account = QComboBox()
        self.account.addItem("default")
        folder = self.state_root / "accounts"
        if folder.exists():
            self.account.addItems([p.name for p in folder.iterdir() if p.is_dir()])
        r.addWidget(self.account)
        self.button(r, "Switch account", self.switch_account)
        self.button(r, "New account", self.new_account)
        self.account_status = QLabel()
        l.addWidget(self.account_status)
        self.consent = QCheckBox(
            "Save this dedicated browser session encrypted on this device"
        )
        l.addWidget(self.consent)
        self.text(
            l,
            "Sign in manually in the trusted browser. The app never reads passwords or imports unrelated browser profiles. Account queues and credentials are isolated. Cookies can grant account access; import only your own export.",
        )
        r = self.row(l)
        self.button(r, "Sign in in browser", self.login, True)
        self.button(r, "Import cookie JSON", self.import_cookies)
        self.button(r, "Forget credentials", self.forget)
        self.text(
            l,
            "Local logout removes saved credentials. Revoke Meta app permissions in Facebook settings to revoke access at the provider. Expired sessions must be renewed manually.",
        )
        l.addStretch()

    def build_meta(self):
        l = self.page("Official Meta API · optional")
        self.text(
            l,
            "OAuth needs a configured Meta app and reviewed permissions; neither was supplied. You can explicitly store an existing authorized token and probe supported identity / object access. Graph API does not grant arbitrary profile downloads.",
        )
        self.token = QLineEdit()
        self.token.setEchoMode(QLineEdit.Password)
        self.token.setPlaceholderText("Existing authorized access token")
        l.addWidget(self.token)
        self.button(l, "Save token encrypted", self.save_token)
        self.meta_id = QLineEdit("me")
        l.addWidget(self.meta_id)
        self.button(l, "Probe authorized object", self.meta, True)
        self.meta_result = QPlainTextEdit()
        self.meta_result.setReadOnly(True)
        l.addWidget(self.meta_result, 1)

    def build_engines(self):
        l = self.page("Native engine control")
        self.native_table = QTableWidget(0, 6)
        self.native_table.setHorizontalHeaderLabels(
            [
                "Engine",
                "Version",
                "Architecture",
                "Source",
                "Status",
                "Capabilities / diagnostics",
            ]
        )
        self.native_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.native_table.horizontalHeader().setSectionResizeMode(
            5, QHeaderView.Stretch
        )
        self.native_table.setMinimumHeight(270)
        l.addWidget(self.native_table)
        self.engine_info = QPlainTextEdit()
        self.engine_info.setReadOnly(True)
        l.addWidget(self.engine_info, 1)
        self.button(l, "Refresh capabilities", self.doctor)
        self.text(
            l,
            "HTTP downloads direct media. yt-dlp extracts Facebook videos. Playwright and Selenium discover visible links. Access restrictions stop work; no alternate-engine probing follows a restriction.",
        )

    def build_diagnostics(self):
        l = self.page("Diagnostics")
        self.diag = QPlainTextEdit()
        self.diag.setReadOnly(True)
        l.addWidget(self.diag, 1)
        r = self.row(l)
        self.button(r, "Refresh", self.diagnostics)
        self.button(r, "Export diagnostics", self.export_diagnostics)

    def build_settings(self):
        l = self.page("Storage and limits")
        self.storage_label = QLabel(str(self.store.media))
        l.addWidget(self.storage_label)
        self.button(l, "Choose media destination", self.destination)
        self.ffmpeg_label = QLabel(self.native_label())
        self.ffmpeg_label.setWordWrap(True)
        l.addWidget(self.ffmpeg_label)
        self.button(l, "Advanced: choose FFmpeg override", self.choose_ffmpeg)
        self.button(l, "Use integrated engines", self.reset_native)
        self.text(
            l,
            "One download at a time per queue. Imports: at most 1,000 URLs. Per-file quota: 10 GiB (FBMD_MAX_FILE_BYTES). ID-based filenames avoid unsafe metadata names. Existing files are preserved.",
        )
        l.addStretch()

    def build_help(self):
        l = self.page("Getting started")
        self.text(
            l,
            "1. Paste accessible links on Home, or scan profiles in Sources.\n2. Choose a quality ceiling and add URLs.\n3. Start the queue. Pause retains partial files; Resume / retry continues them.\n4. Open the media folder or export a redacted manifest.\n\nAccounts: save a dedicated, encrypted session with explicit consent.\nAndroid: local progressive downloads, queue and folder export. Profile discovery and browser authentication are desktop-only.\n\nThis is an alpha. The release report records actual Facebook results and platform verification. Fixture tests do not prove that every Facebook link works.",
        )
        l.addStretch()

    def navigate(self, index):
        self.stack.setCurrentIndex(index)
        if index == 6:
            self.doctor()
        if index == 7:
            self.diagnostics()

    def add(self):
        try:
            urls = self.urls.toPlainText().splitlines()
            if len(urls) > 1000:
                raise ValueError()
            ids = [
                self.store.enqueue(
                    u, self.engine.currentText(), self.quality.currentText()
                )
                for u in urls
                if u.strip()
            ]
            self.urls.clear()
            self.status.setText(
                f"{len(set(ids))} unique jobs accepted; existing history preserved."
            )
        except Exception:
            self.status.setText(
                "Invalid or inaccessible target. Use public HTTP(S) URLs; batch limit 1,000."
            )

    def import_list(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Import URL list", "", "URL lists (*.csv *.txt)"
        )
        if path:
            try:
                self.urls.setPlainText("\n".join(import_urls(Path(path))))
            except Exception:
                self.status.setText(
                    "Import failed; CSV needs a url column and at most 1,000 rows."
                )

    def scan_input(self):
        self.source_urls.setPlainText(self.urls.toPlainText())
        self.nav.setCurrentRow(1)
        self.scan_sources()

    def scan_sources(self):
        urls = [u for u in self.source_urls.toPlainText().splitlines() if u.strip()]
        engine = self.discovery_engine.currentText()
        rounds = int(self.rounds.currentText())
        dry = self.dryrun.isChecked()
        store = self.store
        if len(urls) > 25:
            self.status.setText("Source batch limit: 25.")
            return
        self.status.setText("Discovering visible links…")
        self.discovered = []

        def work():
            from .discovery import discover
            from .security import safe_url

            for url in urls:
                result = discover(store, url, engine, rounds)
                self.discovered.extend(result["urls"])
                if not dry:
                    for value in result["urls"][:1000]:
                        store.enqueue(value)
                self.messages.put(
                    (
                        "source",
                        json.dumps(
                            {
                                **result,
                                "source": safe_url(url),
                                "urls": [safe_url(u) for u in result["urls"]],
                            },
                            indent=2,
                        ),
                    )
                )

        self.background(work)

    def queue_discovered(self):
        try:
            for u in self.discovered[:1000]:
                self.store.enqueue(
                    u, self.engine.currentText(), self.quality.currentText()
                )
            self.status.setText(
                f"{min(1000, len(self.discovered))} discovered URLs submitted."
            )
        except Exception:
            self.status.setText("A discovered target was rejected by network policy.")

    def start(self):
        if self.thread and self.thread.is_alive():
            return
        self.worker = Worker(self.store)

        def work():
            try:
                self.worker.run()
            except Exception as e:
                self.messages.put(
                    type(e).__name__
                    + ": worker unavailable; another app may own this queue."
                )

        self.thread = threading.Thread(target=work, daemon=True)
        self.thread.start()

    def selection(self):
        item = self.nav.currentItem()
        name = item.text() if item else "Home"
        table = self.tables.get(name, self.tables["Home"])
        return [
            int(table.item(index.row(), 0).text())
            for index in table.selectionModel().selectedRows()
            if table.item(index.row(), 0)
        ]

    def control(self, action):
        for i in self.selection() or [None]:
            getattr(self.store, action)(i)
        if action == "resume":
            self.start()
        self.status.setText(
            action.capitalize() + " requested. Partial files are preserved."
        )

    def open_media(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.store.media)))

    def export(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export manifest", "fbmd-manifest.json", "JSON (*.json);;CSV (*.csv)"
        )
        if path:
            export_manifest(self.store, Path(path))

    def login(self):
        if not self.consent.isChecked():
            self.status.setText("Select the session-storage consent checkbox first.")
            return
        store = self.store

        def work():
            from .discovery import sign_in

            self.messages.put(
                "Session encrypted and saved."
                if sign_in(store, save_session=True)
                else "Sign-in timed out; no session saved."
            )

        self.status.setText(
            "Complete manual sign-in in the browser within three minutes."
        )
        self.background(work)

    def import_cookies(self):
        if not self.consent.isChecked():
            self.status.setText("Select the storage consent checkbox first.")
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Select your own Facebook cookie export", "", "JSON (*.json)"
        )
        if not path:
            return
        try:
            from .accounts import import_cookies

            count = import_cookies(self.store, Path(path))
            self.status.setText(
                f"{count} cookies encrypted. The original file remains yours to manage."
            )
        except Exception:
            self.status.setText(
                "Cookie import rejected. Use valid Facebook-only JSON cookies."
            )

    def forget(self):
        self.store.vault.forget()
        self.status.setText("Saved local credentials removed.")

    def new_account(self):
        name, ok = QInputDialog.getText(
            self, "New local account", "Account label (letters, digits, hyphen):"
        )
        import re

        if ok and re.fullmatch("[A-Za-z0-9-]{1,40}", name) and name != "default":
            self.account.addItem(name)
            self.account.setCurrentText(name)
            self.switch_account()

    def switch_account(self):
        if self.thread and self.thread.is_alive():
            self.status.setText("Pause the active queue before switching accounts.")
            return
        name = self.account.currentText()
        state = (
            self.state_root
            if name == "default"
            else self.state_root / "accounts" / name
        )
        self.store = Store(
            state, self.media / name if name != "default" else self.media
        )
        self.status.setText("Selected account: " + name)

    def save_token(self):
        if self.token.text().strip():
            self.store.vault.put("meta-token", self.token.text().strip())
            self.token.clear()
            self.status.setText("Token encrypted locally.")

    def meta(self):
        obj = self.meta_id.text()
        store = self.store

        def work():
            from .discovery import meta_lookup
            from .security import safe_url

            result = meta_lookup(store, obj)
            for url in result["urls"]:
                store.enqueue(url, "http")
            result["urls"] = [safe_url(u) for u in result["urls"]]
            self.messages.put(("meta", json.dumps(result, indent=2)))

        self.background(work)

    def doctor(self):
        from .accounts import status

        native = registry()
        self.native_table.setRowCount(len(native["engines"]))
        for row, item in enumerate(native["engines"]):
            values = [
                item["name"],
                item.get("version", ""),
                item["architecture"],
                item["source"],
                item["status"],
                ", ".join(item.get("capabilities", [])) or item["diagnostic"],
            ]
            for column, value in enumerate(values):
                self.native_table.setItem(row, column, QTableWidgetItem(str(value)))
        self.ffmpeg_label.setText(self.native_label())
        self.engine_info.setPlainText(
            json.dumps(
                {
                    "native_registry": native,
                    "free_bytes": shutil.disk_usage(self.store.media).free,
                    "accounts": status(self.store),
                    "remote_downloaders": False,
                    "parallel_downloads": 1,
                },
                indent=2,
            )
        )

    def diagnostics(self):
        self.diag.setPlainText(json.dumps(self.store.diagnostics(), indent=2))

    def export_diagnostics(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export diagnostics", "fbmd-diagnostics.json", "JSON (*.json)"
        )
        if path:
            Path(path).write_text(
                json.dumps(self.store.diagnostics(), indent=2), encoding="utf-8"
            )

    def destination(self):
        if self.thread and self.thread.is_alive():
            self.status.setText("Pause the queue before changing storage.")
            return
        path = QFileDialog.getExistingDirectory(
            self, "Media destination", str(self.store.media)
        )
        if path:
            self.media = Path(path)
            self.store.media = Path(path)
            self.storage_label.setText(path)
            self.settings["media"] = str(Path(path).resolve())
            self.settings_file.write_text(json.dumps(self.settings), encoding="utf-8")

    def choose_ffmpeg(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose installed FFmpeg", "", "Executable (*.exe)"
        )
        if path:
            os.environ["FBMD_FFMPEG"] = path
            self.ffmpeg_label.setText("FFmpeg: " + path)
            self.settings["ffmpeg"] = path
            self.settings_file.write_text(json.dumps(self.settings), encoding="utf-8")
            self.doctor()

    def reset_native(self):
        os.environ.pop("FBMD_FFMPEG", None)
        self.settings.pop("ffmpeg", None)
        self.settings_file.write_text(json.dumps(self.settings), encoding="utf-8")
        self.doctor()

    def native_label(self):
        runtime = multimedia()
        source = (
            "Integrated"
            if runtime["source"] == "bundled"
            else runtime["source"].capitalize()
        )
        return f"FFmpeg / FFprobe: {source} | {runtime['status']}\n{runtime.get('version', '')}\n{runtime['diagnostic']}"

    def details(self):
        selected = self.selection()
        if selected:
            j = self.store.job(selected[0])
            self.status.setText(j["error"] or j["path"] or j["display"])

    def refresh(self):
        try:
            while True:
                msg = self.messages.get_nowait()
                if isinstance(msg, tuple):
                    (
                        self.source_results if msg[0] == "source" else self.meta_result
                    ).appendPlainText(msg[1])
                    self.status.setText("Operation finished; see results.")
                else:
                    self.status.setText(msg)
        except queue.Empty:
            pass
        rows = self.store.rows()
        self.summary.setText(
            f"{len(rows)} jobs · {sum(j['status'] == 'complete' for j in rows)} complete · {sum(j['status'] == 'running' for j in rows)} active"
        )
        for name, table in self.tables.items():
            filtered = [
                j
                for j in rows
                if name != "History"
                or j["status"] in ("complete", "failed", "blocked", "cancelled")
            ]
            table.blockSignals(True)
            table.setRowCount(len(filtered))
            for row, j in enumerate(filtered):
                progress = (
                    f"{j['downloaded'] / 1048576:.1f} / {j['total'] / 1048576:.1f} MB"
                    if j["total"]
                    else f"{j['downloaded'] / 1048576:.1f} MB / ?"
                )
                values = [
                    j["id"],
                    j["status"],
                    progress,
                    f"{j['rate'] / 1048576:.2f} MB/s",
                    j["engine"],
                    j["resolution"] or j["quality"],
                    j["title"] or j["display"],
                    max(0, j["attempts"] - 1),
                    j["path"],
                    " / ".join(
                        [
                            json.loads(j["media_info"]).get("format") or "",
                            ", ".join(
                                s.get("codec_name") or ""
                                for s in json.loads(j["media_info"]).get("streams", [])
                            ),
                        ]
                    ).strip(" /"),
                ]
                for col, v in enumerate(values):
                    text = str(v)
                    item = table.item(row, col)
                    if item is None:
                        table.setItem(row, col, QTableWidgetItem(text))
                    elif item.text() != text:
                        item.setText(text)
            table.blockSignals(False)
        from .accounts import status

        self.account_status.setText(json.dumps(status(self.store)))

    def closeEvent(self, event):
        if self.worker:
            self.worker.stop.set()
        event.accept()


def render_acceptance(destination):
    from PySide6.QtCore import Qt

    destination = Path(destination).resolve()
    destination.mkdir(parents=True, exist_ok=False)
    app = QApplication.instance() or QApplication([])
    app.setStyleSheet(STYLE)
    window = Window(destination / "state", destination / "media")
    window.setAttribute(Qt.WA_DontShowOnScreen, True)
    window.show()
    for i in range(window.nav.count()):
        window.nav.setCurrentRow(i)
        app.processEvents()
        if i in (0, 6, 8):
            window.grab().save(str(destination / f"view-{i}.png"))
    result = {
        "status": "PASS",
        "screens_rendered": window.nav.count(),
        "native_status": multimedia()["status"],
        "frozen": bool(getattr(sys, "frozen", False)),
    }
    window.close()
    return result


def main(state=None, media=None):
    ds, dm = defaults()
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyleSheet(STYLE)
    window = Window(Path(state or ds), Path(media or dm))
    window.show()
    app.exec()


if __name__ == "__main__":
    main()
