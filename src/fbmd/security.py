from __future__ import annotations
import ctypes
from ctypes import wintypes
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit, urlunsplit
from cryptography.fernet import Fernet


def safe_url(value: str) -> str:
    """Diagnostics deliberately omit query strings, fragments and userinfo."""
    try:
        p = urlsplit(value)
        return urlunsplit((p.scheme, p.hostname or "", p.path, "", ""))
    except ValueError:
        return "[invalid URL]"


def redact(value: str) -> str:
    value = re.sub(r"https?://[^\s<>\"\']+", lambda m: safe_url(m[0]), str(value))
    value = re.sub(
        r"(?i)(access_token|cookie|authorization|password|appsecret_proof|secret)\s*[:=]\s*[^\r\n]+",
        r"\1=[redacted]",
        value,
    )
    value = re.sub(
        r"\b(EAA[A-Za-z0-9]{12,}|gh[pousr]_[A-Za-z0-9_]+)\b", "[redacted]", value
    )
    return value[:1500]


class Blob(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_ubyte))]


def _dpapi(data: bytes, decrypt=False) -> bytes:
    buf = ctypes.create_string_buffer(data)
    source = Blob(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_ubyte)))
    result = Blob()
    crypt = ctypes.WinDLL("crypt32", use_last_error=True)
    fn = crypt.CryptUnprotectData if decrypt else crypt.CryptProtectData
    fn.argtypes = [
        ctypes.POINTER(Blob),
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(Blob),
    ]
    fn.restype = wintypes.BOOL
    if not fn(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(result)):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return ctypes.string_at(result.pbData, result.cbData)
    finally:
        free = ctypes.WinDLL("kernel32").LocalFree
        free.argtypes = [ctypes.c_void_p]
        free.restype = ctypes.c_void_p
        free(result.pbData)


class Vault:
    """Fernet ciphertext; Windows key wrapped by current-user DPAPI.

    Other platforms require an OS keyring. Never stores a raw master key.
    """

    def __init__(self, directory: Path):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        if sys.platform == "win32":
            path = self.directory / "master.dpapi"
            if not path.exists():
                # O_EXCL prevents simultaneous starts from replacing each other's key.
                wrapped = _dpapi(Fernet.generate_key())
                try:
                    with path.open("xb") as f:
                        f.write(wrapped)
                except FileExistsError:
                    pass
            key = _dpapi(path.read_bytes(), decrypt=True)
        else:
            import keyring

            backend = keyring.get_keyring()
            if backend.priority <= 0 or "plaintext" in type(backend).__name__.lower():
                raise RuntimeError("A secure OS keyring is required on this platform")
            account = hashlib.sha256(str(self.directory.resolve()).encode()).hexdigest()
            stored = keyring.get_password("fbmd-master", account)
            if stored is None:
                stored = Fernet.generate_key().decode()
                keyring.set_password("fbmd-master", account, stored)
            key = stored.encode()
        self.cipher = Fernet(key)

    def seal(self, value: str) -> str:
        return self.cipher.encrypt(value.encode()).decode()

    def open(self, value: str) -> str:
        return self.cipher.decrypt(value.encode()).decode()

    def put(self, name: str, value):
        if name not in ("browser", "meta-token", "api-token"):
            raise ValueError("Unknown credential name")
        target = self.directory / (name + ".enc")
        temp = target.with_suffix(".tmp")
        temp.write_text(self.seal(json.dumps(value)), encoding="utf-8")
        temp.replace(target)

    def get(self, name: str, default=None):
        target = self.directory / (name + ".enc")
        return (
            json.loads(self.open(target.read_text(encoding="utf-8")))
            if target.exists()
            else default
        )

    def forget(self):
        for name in ("browser.enc", "meta-token.enc", "api-token.enc"):
            (self.directory / name).unlink(missing_ok=True)
