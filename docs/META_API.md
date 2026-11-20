# Meta API capabilities and limits

Official documentation was checked on 2026-11-20 against Graph v27.0 references. No configured Meta App ID, reviewed permission grant or live token was supplied. Therefore **no authenticated Graph operation or OAuth flow was demonstrated** in this mission. The implemented optional integration is an explicit existing-token capability probe; it is not general Facebook profile enumeration.

| Reference | Documented boundary | Application behavior |
|---|---|---|
| [Page](https://developers.facebook.com/docs/graph-api/reference/page/) | Access depends on Page ownership/tasks and permissions such as pages_read_engagement, with pages_read_user_content for user content; public access features may require review. | No assumption that an arbitrary profile ID is a Page or readable. |
| [Page feed](https://developers.facebook.com/docs/graph-api/reference/page/feed/) | Page task/token and permission requirements apply; pagination and historical limits apply. | Not yet implemented as a bulk Page feed adapter. |
| [Page video_reels](https://developers.facebook.com/docs/graph-api/reference/page/video_reels/) | The checked reference says reading this edge is unsupported; publishing documentation does not establish read access. | No Reels-listing call or claim. |
| [Page post](https://developers.facebook.com/docs/graph-api/reference/page-post/) | The official page repeatedly timed out during this session. | Current Page-post read permissions were not independently established; no Page-post adapter is claimed. |
| [Video](https://developers.facebook.com/docs/graph-api/reference/video/) | Reference contains legacy/deprecation and source-field material; source availability depends on version, object and access. | Numeric ID `fields=id,source` is a capability probe only, with failure/unsupported outcomes. |

The feed documentation and the dedicated video_reels reference do not provide a consistent basis for arbitrary Reels reads. We use the stricter boundary: no supported Reels enumeration claim. `meta_lookup` requests `me?fields=id,name` for token identity, or an explicitly supplied numeric object with `fields=id,source`. Authorization is an HTTPS Bearer header. Redirects are disabled. Only a returned source is offered to the guarded media queue. A missing token, denied request, unsupported field or absent source remains a clear failure/unsupported result.

OAuth onboarding remains blocked by missing app configuration and approval, not by a missing secret to embed. A future implementation must use the [official Facebook Login](https://developers.facebook.com/docs/facebook-login/) flow and [Android SDK](https://github.com/meta/facebook-android-sdk), keep any required secret in a trusted backend, request only supported scopes, and demonstrate authorized Page access before enabling a Page collection feature. App-owned embedded WebView login is not implemented. Never put App Secrets into public clients or repository settings files.
