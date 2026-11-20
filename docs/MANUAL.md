# Beginner manual

## First download

Windows: extract the entire portable ZIP, launch FBMD.exe, paste one accessible Facebook video/Reel or direct media link per line, press Add URLs, then Start. A queue entry is not proof that the source is accessible. Watch status and open the download folder after completion. Queue and history survive a restart. Settings chooses the destination and optional FFmpeg executable and saves those choices locally.

Android: install the APK, open it, paste or share a video link, Add, then Start. Downloads execute on the device in a foreground service. On Android 13+ allow notifications for visible progress. Use Save to folder to copy files through Android's system picker. Export before uninstalling. Release direct-media URLs must use HTTPS. Android has no desktop dependency.

Python: install the wheel, run `fbmd help`, then `fbmd download URL`. `fbmd doctor` reports installed engine versions. `fbmd --state PATH --media PATH` chooses isolated storage before a command. `fbmd add --file links.txt` and CSV files with a `url` column support bulk input. `fbmd export manifest.json` or `.csv` writes redacted history.

## Finding multiple Reels

On Windows Sources, enter profile/Page URLs, choose Playwright (or Selenium if specifically needed), and choose a bounded scroll count. Index only is initially checked. Review count and access outcome, then queue discovered links. Scans collect visible links and cannot prove completeness. A login gate stops the scan. Source discovery is desktop-only; on Android supply accessible individual media URLs.

Accounts lets you make a named account, explicitly enable encrypted session storage, then sign in manually in a dedicated browser. Import cookie JSON only if it is your own export and you understand it grants session access. Never share the file. Forget credentials removes saved local values; revoke upstream access separately in Facebook settings.

## Pause, resume and errors

Pause retains the partial file. Resume/retry requests another attempt; it respects saved server backoff. Range-capable servers with stable validators resume bytes; otherwise a download restarts safely. Cancel stops a pending/active item without deleting user files. Failed or blocked items require correcting network/access/source conditions before retrying. An expired signed URL may require a new permitted discovery or video link. Do not repeatedly retry a login gate or CAPTCHA.

Best and resolution ceilings apply only to exposed formats. Windows includes FFmpeg and FFprobe for split-stream merging, HLS processing, inspection and full decode validation. Android enables split-stream selection only after its on-device FFmpeg fixture test passes; Engines shows the result. A source may expose video without audio, or fewer qualities than expected. Missing streams, quality or duration are not inferred. A local controlled merge test does not prove a particular Facebook source offers split streams.

Diagnostics displays redacted events and queue state. Engine Control shows dependency versions, FFmpeg availability, free space and credential status. Export diagnostics when reporting a problem, then review the file for personal paths before sharing. Settings and state are local; no hosted service is required.
