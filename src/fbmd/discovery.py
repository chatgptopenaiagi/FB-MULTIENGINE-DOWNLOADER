from __future__ import annotations
import re
import time
from urllib.parse import urlsplit, urljoin
import requests
from .store import validate_url, identity
from .network import check_public

DOM_MEDIA = """() => ({links: [...document.querySelectorAll('a[href]')].map(a=>a.href),
 media: [...document.querySelectorAll('video,video source')].map(v=>v.currentSrc||v.src).filter(Boolean),
 gate: !!document.querySelector('input[type=password],form[action*="login"],iframe[src*="captcha"]')})"""


def collect(base, data):
    result = {}
    for value in data.get("links", []) + data.get("media", []):
        url = urljoin(base, value)
        p = urlsplit(url)
        facebook = p.hostname and (
            p.hostname == "facebook.com" or p.hostname.endswith(".facebook.com")
        )
        direct = bool(re.search(r"\.(mp4|webm|mov|jpg|jpeg|png)(?:$|\?)", url, re.I))
        if p.scheme in ("http", "https") and (
            direct
            or (
                facebook
                and (
                    re.search(r"/(reel|videos)/\d+", p.path)
                    or (p.path.rstrip("/") == "/watch" and "v=" in p.query)
                )
            )
        ):
            result[identity(url)] = url
    return list(result.values())


def restricted(url, gate):
    return gate or any(
        x in urlsplit(url).path.lower() for x in ("/login", "/checkpoint", "/captcha")
    )


def discover(store, url, engine="playwright", rounds=5, headless=True):
    validate_url(url)
    check_public(url, store.allow_local)
    host = urlsplit(url).hostname or ""
    if not store.allow_local and not (
        host == "fb.watch" or host == "facebook.com" or host.endswith(".facebook.com")
    ):
        raise ValueError("Browser discovery is limited to Facebook sources")
    rounds = max(1, min(int(rounds), 200))
    result = {
        "status": "empty",
        "urls": [],
        "detail": "No accessible media links found; discovery is bounded and does not prove the source has no media.",
    }
    try:
        if engine == "playwright":
            from playwright.sync_api import sync_playwright

            with sync_playwright() as p:
                browser = launch_browser(p, headless)
                context = browser.new_context(storage_state=store.vault.get("browser"))
                try:
                    page = context.new_page()
                    response = page.goto(
                        url, wait_until="domcontentloaded", timeout=45000
                    )
                    page.wait_for_timeout(1800)
                    if response and response.status in (401, 403, 429):
                        result.update(
                            status="blocked",
                            detail=f"HTTP {response.status}; no access workaround attempted.",
                        )
                    else:
                        found = {}
                        stagnant = 0
                        for _ in range(rounds):
                            data = page.evaluate(DOM_MEDIA)
                            if restricted(page.url, data["gate"]):
                                result.update(
                                    status="blocked",
                                    urls=[],
                                    detail="Login, checkpoint or access challenge detected; use manual browser sign-in and retry.",
                                )
                                break
                            before = len(found)
                            for value in collect(page.url, data):
                                found[identity(value)] = value
                            stagnant = stagnant + 1 if len(found) == before else 0
                            result["urls"] = list(found.values())
                            if stagnant >= 5:
                                break
                            page.evaluate("window.scrollBy(0, window.innerHeight)")
                            page.wait_for_timeout(1200)
                        if result["urls"] and result["status"] != "blocked":
                            result.update(
                                status="found",
                                detail=f"Visible media links collected over at most {rounds} scrolls; completeness is not guaranteed.",
                            )
                finally:
                    context.close()
                    browser.close()
        elif engine == "selenium":
            from selenium import webdriver
            from .native import application_directory

            root = application_directory()
            bundle = root / "engines/browser"
            driver_path = root / "engines/discovery/chromedriver.exe"
            if not bundle.is_dir():
                bundle = root / ".toolchain/playwright"
                driver_path = root / ".toolchain/discovery/chromedriver.exe"
            if bundle.is_dir():
                from selenium.webdriver.chrome.service import Service

                browsers = list(bundle.rglob("chrome.exe"))
                if len(browsers) != 1 or not driver_path.is_file():
                    raise RuntimeError("Matching bundled ChromeDriver is missing")
                options = webdriver.ChromeOptions()
                options.binary_location = str(browsers[0])
                if headless:
                    options.add_argument("--headless=new")
                driver = webdriver.Chrome(
                    service=Service(str(driver_path)), options=options
                )
            else:
                options = webdriver.EdgeOptions()
                if headless:
                    options.add_argument("--headless=new")
                driver = webdriver.Edge(options=options)
            try:
                driver.set_page_load_timeout(45)
                state = store.vault.get("browser", {})
                host = urlsplit(url).hostname or ""
                if state and (host == "facebook.com" or host.endswith(".facebook.com")):
                    driver.get("https://www.facebook.com/")
                    for c in state.get("cookies", []):
                        if c["domain"].lstrip(".") == "facebook.com" or c[
                            "domain"
                        ].endswith(".facebook.com"):
                            cookie = {
                                k: v
                                for k, v in c.items()
                                if k
                                in (
                                    "name",
                                    "value",
                                    "domain",
                                    "path",
                                    "secure",
                                    "httpOnly",
                                    "sameSite",
                                )
                            }
                            if c.get("expires", -1) > 0:
                                cookie["expiry"] = int(c["expires"])
                            driver.add_cookie(cookie)
                driver.get(url)
                found = {}
                for _ in range(rounds):
                    time.sleep(1.2)
                    data = driver.execute_script("return (" + DOM_MEDIA + ")()")
                    if restricted(driver.current_url, data["gate"]):
                        result.update(
                            status="blocked",
                            urls=[],
                            detail="Login or access challenge detected; no bypass attempted.",
                        )
                        break
                    for value in collect(driver.current_url, data):
                        found[identity(value)] = value
                    result["urls"] = list(found.values())
                    driver.execute_script("window.scrollBy(0,window.innerHeight)")
                if result["urls"] and result["status"] != "blocked":
                    result.update(
                        status="found",
                        detail="Visible DOM media links collected; discovery is bounded.",
                    )
            finally:
                driver.quit()
        else:
            raise ValueError("Unknown discovery engine")
    except Exception as e:
        result.update(
            status="error",
            urls=[],
            detail=f"{type(e).__name__}: browser discovery failed. Check browser/driver installation, network and source availability.",
        )
    store.record_discovery(engine, url, result)
    return result


def launch_browser(playwright, headless):
    from .native import application_directory
    import sys

    roots = [
        application_directory() / "engines/browser",
        application_directory() / ".toolchain/playwright",
    ]
    for root in roots:
        if root.is_dir():
            executables = list(root.rglob("chrome.exe"))
            if len(executables) != 1:
                raise RuntimeError("Bundled browser is incomplete or ambiguous")
            return playwright.chromium.launch(
                executable_path=str(executables[0]), headless=headless
            )
    if getattr(sys, "frozen", False):
        raise RuntimeError(
            "Bundled browser missing; repair the application installation"
        )
    try:
        return playwright.chromium.launch(channel="msedge", headless=headless)
    except Exception:
        return playwright.chromium.launch(headless=headless)


def sign_in(store, seconds=180, save_session=False):
    """Human completes Facebook login in a dedicated, non-persistent browser."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = launch_browser(p, False)
        context = browser.new_context()
        try:
            page = context.new_page()
            page.goto(
                "https://www.facebook.com/",
                wait_until="domcontentloaded",
                timeout=45000,
            )
            deadline = time.monotonic() + seconds
            while time.monotonic() < deadline:
                page.wait_for_timeout(1000)
                if any(
                    c["name"] == "c_user"
                    for c in context.cookies("https://www.facebook.com")
                ) and not restricted(page.url, False):
                    if save_session:
                        store.vault.put("browser", context.storage_state())
                    return True
            return False
        finally:
            context.close()
            browser.close()


def meta_lookup(store, object_id, version="v27.0"):
    if not re.fullmatch(r"\d+|me", object_id) or not re.fullmatch(
        r"v\d+\.\d+", version
    ):
        raise ValueError(
            "Use a numeric Meta object ID or me, and a version such as v27.0"
        )
    token = store.vault.get("meta-token")
    if not token:
        return {
            "status": "blocked",
            "detail": "No Meta access token configured",
            "urls": [],
        }
    # No general profile enumeration: probe only an explicitly supplied authorized object.
    try:
        response = requests.get(
            f"https://graph.facebook.com/{version}/{object_id}",
            headers={"Authorization": "Bearer " + token},
            params={"fields": "id,name" if object_id == "me" else "id,source"},
            timeout=25,
            allow_redirects=False,
        )
        data = response.json()
        if response.status_code != 200 or "error" in data:
            code = data.get("error", {}).get("code", "unknown")
            return {
                "status": "blocked",
                "detail": f"Meta rejected this capability (HTTP {response.status_code}, code {code}). Version, object, token and permissions must support it.",
                "urls": [],
            }
        source = data.get("source")
        return {
            "status": "found" if source else "unsupported",
            "detail": "Authorized object lookup returned a source."
            if source
            else "Token accepted; this object exposes no downloadable source.",
            "urls": [validate_url(source)] if source else [],
        }
    except Exception as e:
        return {
            "status": "error",
            "detail": f"{type(e).__name__}: Meta request failed",
            "urls": [],
        }
