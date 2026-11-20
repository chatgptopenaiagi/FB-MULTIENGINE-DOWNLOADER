"""Install isolated, checksum-verified Android build tools. No system mutation."""

from pathlib import Path
import hashlib, subprocess, urllib.request, zipfile, os

ROOT = Path(__file__).resolve().parents[1] / ".toolchain"
ROOT.mkdir(exist_ok=True)


def download(url, name, checksum):
    dest = ROOT / name
    if not dest.exists():
        urllib.request.urlretrieve(url, dest)
    actual = hashlib.file_digest(dest.open("rb"), "sha256").hexdigest()
    if actual != checksum.strip():
        raise RuntimeError(f"Checksum mismatch: {name}")
    return dest


sdk = ROOT / "android-sdk"
archive = download(
    "https://dl.google.com/android/repository/commandlinetools-win-15859902_latest.zip",
    "cmdline.zip",
    "90ae805d20434428bffcb699c290860f19bb5f66a67e6b330067e3de801fb04a",
)
if not (sdk / "cmdline-tools/latest/bin/sdkmanager.bat").exists():
    with zipfile.ZipFile(archive) as z:
        z.extractall(ROOT / "cmdline-unpack")
    (sdk / "cmdline-tools").mkdir(parents=True, exist_ok=True)
    (ROOT / "cmdline-unpack/cmdline-tools").rename(sdk / "cmdline-tools/latest")
base = "https://services.gradle.org/distributions/gradle-8.13-bin.zip"
checksum = urllib.request.urlopen(base + ".sha256", timeout=60).read().decode()
gradle = download(base, "gradle.zip", checksum)
if not (ROOT / "gradle-8.13").exists():
    with zipfile.ZipFile(gradle) as z:
        z.extractall(ROOT)
env = dict(
    os.environ,
    JAVA_HOME=r"C:\Program Files\Android\openjdk\jdk-21.0.8",
    ANDROID_HOME=str(sdk),
    ANDROID_SDK_ROOT=str(sdk),
)
manager = str(sdk / "cmdline-tools/latest/bin/sdkmanager.bat")
subprocess.run(
    [manager, f"--sdk_root={sdk}", "--licenses"],
    input="y\n" * 100,
    text=True,
    env=env,
    check=True,
)
subprocess.run(
    [
        manager,
        f"--sdk_root={sdk}",
        "platform-tools",
        "platforms;android-35",
        "build-tools;35.0.0",
        "emulator",
        "system-images;android-30;google_apis;x86_64",
    ],
    input="y\n" * 100,
    text=True,
    env=env,
    check=True,
)
print("ANDROID_TOOLCHAIN_READY", flush=True)
