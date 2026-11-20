"""Build signed release with a project-local key; never prints signing passwords."""

import os
from pathlib import Path
import secrets
import subprocess
from fbmd.security import _dpapi

root = Path(__file__).resolve().parents[1]
private = root / ".private/signing"
private.mkdir(parents=True, exist_ok=True)
password_file = private / "password.dpapi"
key = private / "fbmd-release.jks"
if not password_file.exists():
    if key.exists():
        raise RuntimeError(
            "Existing signing key has no local password; refusing to replace it"
        )
    with password_file.open("xb") as f:
        f.write(_dpapi(secrets.token_urlsafe(48).encode()))
password = _dpapi(password_file.read_bytes(), decrypt=True).decode()
env = os.environ.copy()
env.update(
    JAVA_HOME="C:/Program Files/Android/openjdk/jdk-21.0.8",
    ANDROID_HOME=str(root / ".toolchain/android-sdk"),
    ANDROID_SDK_ROOT=str(root / ".toolchain/android-sdk"),
    GRADLE_USER_HOME=str(root / ".toolchain/gradle-home"),
    FBMD_KEYSTORE=str(key),
    FBMD_STORE_PASSWORD=password,
    FBMD_KEY_PASSWORD=password,
)
if not key.exists():
    subprocess.run(
        [
            env["JAVA_HOME"] + "/bin/keytool.exe",
            "-genkeypair",
            "-keystore",
            str(key),
            "-alias",
            "fbmd",
            "-keyalg",
            "RSA",
            "-keysize",
            "3072",
            "-validity",
            "10000",
            "-storepass:env",
            "FBMD_STORE_PASSWORD",
            "-keypass:env",
            "FBMD_KEY_PASSWORD",
            "-dname",
            "CN=FB MultiEngine Downloader, OU=Independent Open Source",
        ],
        env=env,
        check=True,
    )
subprocess.run(
    [
        str(root / ".toolchain/gradle-8.13/bin/gradle.bat"),
        "-p",
        str(root / "android"),
        "assembleRelease",
        "connectedDebugAndroidTest",
        "--console=plain",
    ],
    env=env,
    check=True,
)
print("SIGNED_RELEASE_BUILT; signing key and DPAPI password stay in .private/signing")
