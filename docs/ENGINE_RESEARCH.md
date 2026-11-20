# Engine research — Mission 001

Research snapshot: 2026-11-20. All 41 supplied repositories were checked against live GitHub metadata. Relevant candidates received README review, and the leading candidates received source/tree inspection. This is an engineering selection assessment, not a claim that every upstream project was executed. Raw metadata and exact search results are in `evidence/repository-inventory.json` and `evidence/research-details.json`.

## All 41 repositories

`Unknown` / `NOASSERTION` is not a license grant. Push timestamps include non-default branches; they are not proof of active maintenance. No source from an unlicensed repository was copied.

| # | Repository | Reported license | Last push | Assessment / decision |
|---|---|---|---|---|
| 1 | [nanofatdog/fb_reel_dl](https://github.com/nanofatdog/fb_reel_dl) | Unknown | 2026-06-27 | Reference only: browser discovery + yt-dlp pattern; license not independently established; session handling replaced. |
| 2 | [huandu/facebook](https://github.com/huandu/facebook) | MIT | 2026-08-21 | Go Graph SDK; no media extractor; official HTTP requests avoid another runtime. |
| 3 | [meta/facebook-ios-sdk](https://github.com/meta/facebook-ios-sdk) | NOASSERTION | 2026-11-19 | Official iOS SDK; outside Windows/Android/Python targets. |
| 4 | [meta/facebook-android-sdk](https://github.com/meta/facebook-android-sdk) | NOASSERTION | 2026-11-17 | Official Android authentication reference; OAuth deferred until a configured reviewed Meta app exists. |
| 5 | [facebookarchive/facebook-php-sdk](https://github.com/facebookarchive/facebook-php-sdk) | Unknown | 2019-01-13 (archived) | Archived legacy PHP SDK; incompatible runtime and deprecated API surface. |
| 6 | [warifp/FacebookToolkit](https://github.com/warifp/FacebookToolkit) | MIT | 2024-09-11 | Broad automation/bot toolkit; unnecessary actions and access risks; excluded. |
| 7 | [Wizcorp/phonegap-facebook-plugin](https://github.com/Wizcorp/phonegap-facebook-plugin) | NOASSERTION | 2021-01-03 | Cordova plugin; legacy hybrid stack, incompatible with native Compose design. |
| 8 | [hungtraan/FacebookBot](https://github.com/hungtraan/FacebookBot) | MIT | 2022-07-31 | Messenger/NLP bot; no relevant media engine. |
| 9 | [mobolic/facebook-sdk](https://github.com/mobolic/facebook-sdk) | Apache-2.0 | 2024-08-02 | Python Graph SDK evaluated; small explicit Graph probe uses requests to keep capabilities transparent. |
| 10 | [kevinzg/facebook-scraper](https://github.com/kevinzg/facebook-scraper) | MIT | 2024-06-22 | Public post scraper; stale default branch and brittle HTML assumptions; no primary dependency. |
| 11 | [facebookarchive/php-graph-sdk](https://github.com/facebookarchive/php-graph-sdk) | NOASSERTION | 2022-01-11 (archived) | Archived PHP Graph SDK; no extractor and wrong target runtime. |
| 12 | [IAmBlackHacker/Facebook-BruteForce](https://github.com/IAmBlackHacker/Facebook-BruteForce) | Unknown | 2024-05-11 | Account brute-force tool; categorically excluded; never executed. |
| 13 | [tschellenbach/Django-facebook](https://github.com/tschellenbach/Django-facebook) | NOASSERTION | 2021-11-28 | Legacy Django integration; no need for a web server framework or this auth stack. |
| 14 | [facebookresearch/fairseq](https://github.com/facebookresearch/fairseq) | MIT | 2025-09-30 (archived) | Sequence-to-sequence ML toolkit; unrelated. |
| 15 | [Schmavery/facebook-chat-api](https://github.com/Schmavery/facebook-chat-api) | MIT | 2021-12-24 (archived) | Archived unofficial chat API; unrelated and unnecessary credential handling. |
| 16 | [jaredhanson/passport-facebook](https://github.com/jaredhanson/passport-facebook) | MIT | 2024-04-21 | Node Passport login adapter; auth concept only, no downloader. |
| 17 | [meta/folly](https://github.com/meta/folly) | Apache-2.0 | 2026-11-20 | C++ foundation library; unrelated to selected managed-language architecture. |
| 18 | [opauth/facebook](https://github.com/opauth/facebook) | Unknown | 2023-11-29 | PHP OAuth strategy; wrong runtime and no media extraction. |
| 19 | [chinoogawa/fbht](https://github.com/chinoogawa/fbht) | NOASSERTION | 2024-05-09 | Hacking toolkit; categorically excluded; never executed. |
| 20 | [simi/omniauth-facebook](https://github.com/simi/omniauth-facebook) | Unknown | 2026-08-11 | Ruby OAuth strategy; wrong runtime; official app configuration still needed. |
| 21 | [sindresorhus/caprine](https://github.com/sindresorhus/caprine) | MIT | 2026-01-02 | Messenger desktop client; interface reference only, not a media extractor. |
| 22 | [vikas5914/Facebook-Video-Downloader](https://github.com/vikas5914/Facebook-Video-Downloader) | MIT | 2023-11-11 | PHP video script; README directs Reels to a third-party RapidAPI service; excluded. |
| 23 | [shawwn/llama-dl](https://github.com/shawwn/llama-dl) | GPL-3.0 | 2023-06-28 | LLaMA model download utility; unrelated to Facebook media. |
| 24 | [HoangTran0410/FBMediaDownloader](https://github.com/HoangTran0410/FBMediaDownloader) | Unknown | 2025-02-27 | Node media tool migrated toward extension; token/session assumptions and missing license; excluded. |
| 25 | [theofficialvkr/VKrDownloader](https://github.com/theofficialvkr/VKrDownloader) | MIT | 2025-12-14 | README describes a hosted extraction API; third-party service not selected. |
| 26 | [katariyanikhil/SaveIt](https://github.com/katariyanikhil/SaveIt) | Unknown | 2022-05-13 | Flutter app; README explicitly requires permission to reuse code; no reuse. |
| 27 | [tam7t/photograbber](https://github.com/tam7t/photograbber) | GPL-3.0 | 2021-02-14 (archived) | Archived photo tool; legacy API and GPL obligations not needed. |
| 28 | [irazasyed/video-downloader](https://github.com/irazasyed/video-downloader) | MIT | 2019-10-25 (archived) | Archived video wrapper last pushed 2019; no current engine advantage. |
| 29 | [morganecf/facebook](https://github.com/morganecf/facebook) | Unknown | 2015-04-07 | 2015 message export utilities; not video discovery. |
| 30 | [duongxthanh/facebook-reels-downloader](https://github.com/duongxthanh/facebook-reels-downloader) | MIT | 2026-09-11 | Reference only: Selenium visible links and CSV/yt-dlp flow; independently implemented incremental collection. |
| 31 | [milancodess/universalDownloader](https://github.com/milancodess/universalDownloader) | Unknown | 2026-11-09 | Source delegates Facebook to third-party metadownloader/snapsave; excluded. |
| 32 | [MariyaSha/WebscrapingFacebook](https://github.com/MariyaSha/WebscrapingFacebook) | Unknown | 2023-06-16 | Selenium photo tutorial warns selectors become obsolete; missing license; no code reuse. |
| 33 | [RaghavSood/FBMessageScraper](https://github.com/RaghavSood/FBMessageScraper) | Unknown | 2015-06-28 (archived) | Archived chat export; unrelated to video extraction. |
| 34 | [a11global/facebook-ads-performance-downloader](https://github.com/a11global/facebook-ads-performance-downloader) | MIT | 2021-10-11 | Ads performance data downloader; not video media. |
| 35 | [jcontini/facebook-photos-download](https://github.com/jcontini/facebook-photos-download) | MIT | 2021-06-01 | Photo metadata and index-only pattern useful; README passes passwords on command line; no code reuse. |
| 36 | [sh13y/Facebook-Video-Download-API](https://github.com/sh13y/Facebook-Video-Download-API) | NOASSERTION | 2025-11-13 | Reference architecture: FastAPI + yt-dlp + FFmpeg. Reject disabled TLS verification and title-based temp paths. |
| 37 | [tonyflo/facebook-download-photos](https://github.com/tonyflo/facebook-download-photos) | GPL-3.0 | 2025-03-30 | Photo scraper; command-line password flow and GPL-3 scope not adopted. |
| 38 | [NicheOffice/facebook-video-downloader](https://github.com/NicheOffice/facebook-video-downloader) | MIT | 2019-02-08 | Old PHP shared-hosting website; lacks local persistent native architecture. |
| 39 | [Lackoftactics/facebook_data_analyzer](https://github.com/Lackoftactics/facebook_data_analyzer) | Unknown | 2022-05-18 (archived) | Ruby analysis of already-exported Facebook data; no download engine. |
| 40 | [awesome-yasin/Media-Downloader](https://github.com/awesome-yasin/Media-Downloader) | Unknown | 2023-11-14 | README uses RapidAPI-hosted media services; excluded from local engine. |
| 41 | [bcat95/Facebook-Video-Downloader](https://github.com/bcat95/Facebook-Video-Downloader) | Unknown | 2020-08-12 | Old downloader demo with missing license/current support evidence; excluded. |

## Scored shortlist

Scores are judgment on suitability for this project, from 0 (unusable) to 5 (strong). Maintenance uses current upstream evidence; reliability means architecture/test evidence, not guaranteed Facebook access. Security includes credential and network defaults; license measures clarity and ease of independent integration. A high score in one role does not substitute for another role.

| Component | Function fit | Maintenance | Reliability | Security | License clarity | Local packaging | /30 | Decision |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| yt-dlp | 5 | 5 | 4 | 4 | 5 | 5 | 28 | Primary Facebook video extractor |
| Playwright | 5 | 5 | 5 | 4 | 5 | 4 | 28 | Primary visible DOM discovery |
| Selenium | 4 | 5 | 4 | 4 | 5 | 4 | 26 | Optional browser fallback, user-selected |
| FFmpeg | 5 | 5 | 5 | 4 | 3 | 4 | 26 | Mission 002 integrated Windows merge/inspection/verification runtime |
| youtubedl-android 0.18.1 | 5 | 3 | 4 | 4 | 4 | 5 | 25 | Embedded Android extraction and locally tested native FFmpeg |
| Official Meta SDK / Graph | 2 | 5 | 5 | 5 | 4 | 4 | 25 | Authorized capabilities only; app setup gate |
| nanofatdog/fb_reel_dl | 5 | 3 | 2 | 2 | 0 | 3 | 15 | Architecture reference only |
| duongxthanh/facebook-reels-downloader | 4 | 3 | 2 | 2 | 5 | 3 | 19 | Discovery reference only |
| sh13y/Facebook-Video-Download-API | 4 | 2 | 3 | 1 | 3 | 2 | 15 | API/merge reference, no code reuse |
| kevinzg/facebook-scraper | 3 | 1 | 3 | 2 | 5 | 3 | 17 | Excluded as default engine |
| milancodess/universalDownloader | 3 | 4 | 2 | 1 | 0 | 2 | 12 | Excluded: external extraction dependency |
| Android Fetch | 3 | 2 | 4 | 4 | 5 | 4 | 22 | Considered; native SQLite/OkHttp avoids extra queue/JitPack |

## Source-level findings

- [fb_reel_dl downloader](https://github.com/nanofatdog/fb_reel_dl/blob/ef65e319f9b823739953a69a888b5aec5fca59c7/src/fb_reel_dl/downloader.py): scroll/stagnation discovery and yt-dlp are relevant. Plaintext storage state, existing-browser cookie acquisition and anti-automation launch settings were not adopted. This implementation uses a fresh browser context, opt-in encrypted state and explicit stop conditions.
- [Selenium reels script](https://github.com/duongxthanh/facebook-reels-downloader/blob/dea2f669d80efe743a1930293bbd4892fb270792/reels.py): persistent-profile and unchanged-offset termination patterns can miss lazy-loaded items or retain secrets. Our browser state is encrypted and links are collected on each bounded scroll. No upstream test suite was established merely from test-URL filenames.
- [FastAPI service](https://github.com/sh13y/Facebook-Video-Download-API/blob/15d1fd7b045cc2bd07b45f413efbd157fbc8c1d8/app/services/video_service.py): extract/merge separation is useful. Disabled certificate verification, raw error output and title-derived temporary paths were rejected. Our paths use IDs and URL hashes; logs omit raw library errors.
- [Universal downloader service](https://github.com/milancodess/universalDownloader/blob/cbabe83fe37260359903fbe2934cca075495a886/services/facebookInstaService.js) delegates extraction to other providers. No such service receives URLs or credentials from this app.
- [Android engine](https://github.com/yausername/youtubedl-android/tree/d725d5c9a18c3a99a13ee0308bf78275dc310760): source review covered initialization, request arguments, progress callback and process cancellation. Native Python/yt-dlp executes inside the APK. Mission 002 integrates both `io.github.junkfood02.youtubedl-android:library:0.18.1` and its `ffmpeg:0.18.1` component, with a pruned dependency closure and startup merge/decode test. No remote bridge is required. Runtime verification is on x86_64; ARM64 execution remains unverified.
- [yt-dlp Facebook extractor](https://github.com/yt-dlp/yt-dlp/blob/master/yt_dlp/extractor/facebook.py) supplies regression URLs and extraction behavior. Release uses the recorded installed version, not a vendored fork. Network restrictions and upstream changes still affect availability.
- [Meta Android SDK](https://github.com/meta/facebook-android-sdk) is the official login route after an app is configured. Its login guidance does not support app-owned WebView login; none was implemented.

## Current GitHub searches

The four supplied search URLs were attempted. GitHub connector rejected bare search-page fetches and web fetches returned cache misses. Equivalent authenticated repository searches for `facebook` and `facebook download`, pages 1 and 2 with 10 items each, succeeded; exact names/order are saved in research-details.json. Search rank is not evidence of safety or function. The supplied nanofatdog entry plus those 40 entries make the 41-item inventory.

## Selected architecture

Original application code connects maintained official libraries rather than merging unrelated downloaders. Windows/Python share a SQLite/WAL engine. Browser discovery emits candidates and never silently switches around an access restriction. yt-dlp handles Facebook extraction; the direct HTTP engine handles public media with validated DNS/redirects and Range/If-Range recovery. Integrated FFmpeg merges selected formats and decode-checks files; wheel provisioning remains explicit. Native Android has its own persistent SQLite queue, OkHttp transport, foreground service, MediaExtractor validation and Keystore vault.

## Additional primary sources

[Playwright authentication](https://playwright.dev/python/docs/auth), [Selenium](https://github.com/SeleniumHQ/selenium), [FFmpeg licensing](https://ffmpeg.org/legal.html), [Android Fetch](https://github.com/tonyofrancis/Fetch), [Meta Graph documentation](https://developers.facebook.com/docs/graph-api/). Review META_API.md for endpoint-specific limits. No downloaded upstream media or credentials belong in this repository.
