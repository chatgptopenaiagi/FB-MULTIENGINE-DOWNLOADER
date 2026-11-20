import json
import time
from pathlib import Path


def status(store):
    cookies = store.vault.get("browser", {}).get("cookies", [])
    active = [
        c
        for c in cookies
        if c.get("name") == "c_user"
        and (c.get("expires", -1) < 0 or c["expires"] > time.time())
    ]
    return {
        "browser_session": "saved_unverified" if active else "missing_or_expired",
        "meta_token": "saved_unverified"
        if store.vault.get("meta-token")
        else "missing",
        "storage": "DPAPI / OS keyring",
        "password_stored": False,
    }


def import_cookies(store, path: Path):
    if path.stat().st_size > 1024 * 1024:
        raise ValueError("Cookie file too large")
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    cookies = data.get("cookies", []) if isinstance(data, dict) else data
    result = []
    for c in cookies:
        domain = c.get("domain", "")
        if domain.lstrip(".") != "facebook.com" and not domain.endswith(
            ".facebook.com"
        ):
            continue
        if not isinstance(c.get("name"), str) or not isinstance(c.get("value"), str):
            raise ValueError("Invalid cookie")
        expires = c.get("expires", c.get("expirationDate", -1))
        if expires > 0 and expires < time.time():
            continue
        result.append(
            {
                "name": c["name"],
                "value": c["value"],
                "domain": domain,
                "path": c.get("path", "/"),
                "expires": expires,
                "httpOnly": bool(c.get("httpOnly", True)),
                "secure": bool(c.get("secure", True)),
                "sameSite": c.get("sameSite")
                if c.get("sameSite") in ("Strict", "Lax", "None")
                else "Lax",
            }
        )
    if not result:
        raise ValueError("No current Facebook cookies")
    store.vault.put("browser", {"cookies": result, "origins": []})
    return len(result)
