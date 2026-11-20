# Architecture and recovery

Windows and the wheel share `src/fbmd`. `store.py` owns SQLite WAL transactions and additive schema migration, `engine.py` owns scheduling and file finalization, `network.py` owns public-address/redirect validation, `discovery.py` owns bounded Playwright/Selenium scans and explicit Graph probes, `security.py`/`accounts.py` own credentials, and `manifest.py` owns import/export. `client.py` is the public typed facade. `api.py` is an optional authenticated loopback adapter. `gui.py` and `cli.py` call the same store/worker. The flat module layout keeps this alpha's boundaries visible without empty abstraction directories.

Android uses an independent SQLite WAL database, Android Keystore, a native foreground service, OkHttp and embedded Python/yt-dlp. Kotlin Compose provides the interface. It never delegates extraction to a hosted service. Android release direct-media downloads require HTTPS; debug builds permit only local HTTP test fixtures. Android profile discovery and authenticated browser sessions are not implemented.

## Queue lifecycle

`queued -> running -> complete`, or `running -> retry -> running`; paused, blocked, failed and cancelled are explicit states. A transaction claims one task. Windows/Python also uses an OS file lock so two processes cannot run the same queue. A reopened worker recovers abandoned running tasks to queued. Retry waits are persisted; resume retains a server-imposed backoff. Access restrictions stop that job. Engines are selected by capability, not by trying another identity or access path after a denial.

There is one active download per queue. Account queues are isolated, so concurrently running independent account processes are not governed by a shared global rate limit. Keep one worker active per Facebook origin. Imports are bounded to 1,000 desktop URLs or 100 Android URLs; browser source batches are limited to 25. Downloads have a 10 GiB file ceiling. HTTP paths check advertised size, actual bytes and disk availability. yt-dlp's own resumable state is retained.

## Identity, paths and crash recovery

Facebook Reel/video/watch aliases share a canonical numeric ID. Other direct URLs keep query parameters for identity; signed URLs are encrypted at rest. Diagnostics omit query strings. Filename construction uses task ID and a hash of identity, never titles or URL path components. Content hashes prevent saving a second identical completed file. A prior file's hash is rechecked before deduplication.

HTTP writes `.part`, flushes and syncs it, validates length/container, optionally runs FFmpeg decoding, writes a checksum receipt, then renames. If a final file already exists, it is only reused when its receipt matches; an unknown file is preserved and the job fails. Stable ETag or Last-Modified validators gate range resume; a 200 response restarts the part safely. Bad range metadata or changed validators fail rather than append mismatched content. A crash after rename is recovered from the receipt. Pausing/cancelling retains partial files for inspection; it does not delete user data.

Windows yt-dlp writes into a per-job staging directory before verification and finalization. The native registry supplies a verified bundled FFmpeg path; a broken selected runtime cannot silently fall back to PATH. FFprobe records stream/container metadata. Android native yt-dlp uses its own `.part` handling and validates completed media tracks with MediaExtractor. Android HTTP uses its own hash receipt. Android's bundled FFmpeg runs a local merge/decode self-test before split-stream selection is enabled; failure leaves progressive selection available with a diagnostic.

## Diagnostics and contracts

Jobs and events record status, chosen engine, bytes, estimated total when known, retries, file path and hash. Desktop adds extractor title, content type and available resolution. Missing metadata remains empty. Error text from third-party extractors is not stored verbatim because it can contain signed media links. Browser discovery records outcome/count and coverage uncertainty. JSON/CSV exports are credential-free and CSV formula prefixes are escaped.

`contracts/openapi.json` is generated from the actual FastAPI app. Android is standalone and does not consume the optional desktop API in this alpha. No LAN pairing contract is claimed. See the verification report for failure injection and installed-artifact evidence.
