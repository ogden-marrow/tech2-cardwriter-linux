from __future__ import annotations

import glob
import os
import re
import shutil
import stat
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

APP_ID = "com.github.ogdenmarrow.Tech2CardWriter"
APP_NAME = "Tech2 Card Writer"
APP_VERSION = "1.0.0"

TEN_MB = 10 * 1024 * 1024
THIRTY_TWO_MB = 32 * 1024 * 1024
VALID_CARD_SIZES = (TEN_MB, THIRTY_TWO_MB)


def _xdg(env_name: str, fallback: str) -> Path:
    value = os.environ.get(env_name) or fallback
    return Path(value).expanduser()


DATA_HOME = _xdg("XDG_DATA_HOME", "~/.local/share")
STATE_HOME = _xdg("XDG_STATE_HOME", "~/.local/state")
CACHE_HOME = _xdg("XDG_CACHE_HOME", "~/.cache")
USER_DATA = DATA_HOME / "tech2-cardwriter"
USER_STATE = STATE_HOME / "tech2-cardwriter"
USER_CACHE = CACHE_HOME / "tech2-cardwriter"
IMAGES_DIR = USER_DATA / "images"
LOG_DIR = USER_STATE / "logs"


def app_root() -> Path:
    """Return the install root (contains app/, wine/, lib/, share/)."""
    env = os.environ.get("TECH2_CARDWRITER_ROOT")
    if env:
        return Path(env).expanduser().resolve()
    # ROOT/lib/tech2_cardwriter/backend.py -> ROOT
    return Path(__file__).resolve().parents[2]


ROOT = app_root()
APP_DIR = ROOT / "app"
WINE_DIR = ROOT / "wine"
SHARE_DIR = ROOT / "share"


def prefix_dir() -> Path:
    return USER_DATA / "prefix"


def wine_binary() -> Path | None:
    bundled = WINE_DIR / "bin" / "wine"
    if bundled.is_file() and os.access(bundled, os.X_OK):
        return bundled
    system = shutil.which("wine")
    return Path(system) if system else None


def wine_env() -> dict[str, str]:
    wine = wine_binary()
    if wine is None:
        raise RuntimeError(
            "Wine is not installed and no bundled Wine was found. "
            "Install the 'wine' package or use the bundled .deb/source install."
        )
    env = os.environ.copy()
    env["WINEPREFIX"] = str(prefix_dir())
    env["WINEARCH"] = "win64"
    env["WINEDLLOVERRIDES"] = "mscoree,mshtml="
    env["WINEDEBUG"] = "" if os.environ.get("TECH2_DEBUG") else "-all"
    env["PATH"] = f"{wine.parent}:{env.get('PATH', '')}"
    return env


def ensure_prefix(timeout: int = 240) -> bool:
    """Create the Wine prefix on first run. Returns True if it was created."""
    prefix = prefix_dir()
    marker = prefix / "system.reg"
    if marker.is_file() and (prefix / "drive_c" / "windows").is_dir():
        return False
    prefix.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log = LOG_DIR / "wineboot.log"
    wine = wine_binary()
    assert wine is not None
    with log.open("wb") as fh:
        proc = subprocess.run(
            [str(wine), "wineboot", "-i"],
            env=wine_env(),
            stdout=fh,
            stderr=subprocess.STDOUT,
            timeout=timeout,
        )
    if proc.returncode != 0:
        raise RuntimeError(
            f"Wine could not create its prefix (exit {proc.returncode}). "
            f"See {log} for details."
        )
    return True


def map_com_port(port: str, com: int = 1) -> Path:
    """Expose a Linux serial device as COM<com> inside the Wine prefix."""
    dosdevices = prefix_dir() / "dosdevices"
    dosdevices.mkdir(parents=True, exist_ok=True)
    link = dosdevices / f"com{com}"
    try:
        if link.is_symlink() or link.exists():
            link.unlink()
    except OSError:
        pass
    link.symlink_to(os.path.realpath(port))
    return link


def launch_cardwriter(port: str) -> tuple[subprocess.Popen, Path]:
    exe = APP_DIR / "Card_writer.exe"
    if not exe.is_file():
        raise RuntimeError(f"Card_writer.exe was not found at {exe}.")
    ensure_prefix()
    map_com_port(port)
    wine = wine_binary()
    assert wine is not None
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log = LOG_DIR / f"cardwriter-{time.strftime('%Y%m%d-%H%M%S')}.log"
    fh = log.open("wb")
    proc = subprocess.Popen(
        [str(wine), "Card_writer.exe"],
        cwd=str(APP_DIR),
        env=wine_env(),
        stdout=fh,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    return proc, log


@dataclass(frozen=True)
class SerialPort:
    device: str
    label: str
    accessible: bool

    @property
    def sort_key(self):
        return (0 if any(x in self.device for x in ("ttyUSB", "ttyACM")) else 1, self.device)


def detect_ports(extra: Iterable[str] = ()) -> list[SerialPort]:
    found: list[str] = []
    for pattern in ("/dev/ttyUSB*", "/dev/ttyACM*"):
        found.extend(glob.glob(pattern))
    # ttyS0-ttyS3 cover built-in ports without listing all 32 legacy nodes.
    found.extend(f"/dev/ttyS{i}" for i in range(4))
    found.extend(extra)
    seen: set[str] = set()
    ports: list[SerialPort] = []
    for device in sorted(found):
        if device in seen or not os.path.exists(device):
            continue
        seen.add(device)
        try:
            mode = os.stat(device).st_mode
            if not stat.S_ISCHR(mode):
                continue
        except OSError:
            continue
        kind = "USB serial" if "ttyUSB" in device else "ACM serial" if "ttyACM" in device else "Serial"
        label = f"{device}  ·  {kind}"
        ports.append(SerialPort(device, label, os.access(device, os.R_OK | os.W_OK)))
    ports.sort(key=lambda p: p.sort_key)
    return ports


@dataclass(frozen=True)
class CardVersion:
    version: int
    size_mb: int
    coverage: str
    languages: str = ""


# Saab Tech 2 card images. Source: tech2wiki.com (CC0) and Saab TIS2000 release notes.
CARD_VERSIONS: dict[int, CardVersion] = {
    2: CardVersion(2, 32, "Saab 9-3 diagnostics; DTC C0131 08 and C0252 (ESP)", "many"),
    44: CardVersion(44, 10, "Saab 900 1990–1998 and 9000 1988–1998", "many"),
    135: CardVersion(135, 32, "9-3 (9400) 1998–2003, 9-3 Sport (9440) 2003–2008, 9-5 (9600) 1998–2008", "many"),
    136: CardVersion(136, 32, "9-3 (9400) 1998–2003, 9-3 Sport (9440) 2003–2009, 9-5 (9600) 1998–2009", "many"),
    143: CardVersion(143, 32, "9-3 (9400) 1998–2003, 9-3 Sport (9440) 2003–2010, 9-5 (9600) 1998–2010", "English only"),
    144: CardVersion(144, 32, "9-3 (9400) 1998–2003, 9-3 Sport (9440) 2003–2010, 9-5 (9600) 1998–2010", "many"),
    145: CardVersion(145, 32, "9-3 (9400) 1998–2003, 9-3 Sport (9440) 2003–2011, 9-5 (9600) 1998–2010", "many"),
    146: CardVersion(146, 32, "9-3 (9400) 1998–2003, 9-3 Sport (9440) 2003–2011, 9-5 (9600) 1998–2010", "many"),
    147: CardVersion(147, 32, "9-3 (9400) 1998–2003, 9-3 Sport (9440) 2003–2011, 9-5 (9600) 1998–2010", "many"),
    148: CardVersion(148, 32, "9-3 (9400) 1998–2003, 9-3 Sport (9440) 2003–2011, 9-5 (9600) 1998–2010", "many"),
}


@dataclass
class CardImage:
    path: Path
    size: int
    version: int | None
    version_label: str
    magic_ok: bool
    size_ok: bool
    coverage: str = ""
    warnings: list[str] = field(default_factory=list)

    @property
    def size_mb(self) -> float:
        return self.size / (1024 * 1024)

    @property
    def valid(self) -> bool:
        return self.magic_ok and self.size_ok

    @property
    def display_name(self) -> str:
        if self.version is not None:
            return f"Saab {self.version_label}  ·  {self.size_mb:g} MB"
        return f"{self.path.name}  ·  {self.size_mb:g} MB"


def inspect_image(path: str | os.PathLike[str], car: str = "9-5") -> CardImage:
    p = Path(path).expanduser()
    size = p.stat().st_size
    with p.open("rb") as fh:
        head = fh.read(16)
    magic_ok = head[:4] == b"T2  "
    match = None
    for m in re.finditer(r"(\d{2,3})(?:\.(\d{3}))?", p.stem):
        match = m
    version = int(match.group(1)) if match else None
    version_label = f"{version}.000" if version is not None else "unknown"
    if match and match.group(2):
        version_label = f"{version}.{match.group(2)}"
    expected = 10 if version == 44 else 32
    size_ok = size in VALID_CARD_SIZES
    info = CardImage(p, size, version, version_label, magic_ok, size_ok)
    if version in CARD_VERSIONS:
        info.coverage = CARD_VERSIONS[version].coverage
    if not magic_ok:
        info.warnings.append("Missing the 'T2  ' Tech 2 header. This may not be a card image.")
    if not size_ok:
        info.warnings.append(
            f"Unexpected size {info.size_mb:g} MB. Tech 2 images are 10 MB or 32 MB."
        )
    elif expected and abs(info.size_mb - expected) > 0.1:
        info.warnings.append(
            f"This looks like a {expected} MB image, but the file is {info.size_mb:g} MB."
        )
    if version == 44 and car == "9-5":
        info.warnings.append("v44.000 is for the 900/9000, not the 9-5.")
    if version is None:
        info.warnings.append("Could not read a version from the filename; verify this is the right image.")
    elif version not in CARD_VERSIONS:
        info.warnings.append("Unknown Saab version; verify this image matches your car.")
    if version == 143:
        info.warnings.append("v143.000 is English-only.")
    if version is not None and version >= 144:
        info.warnings.append("This image requires a 32 MB PCMCIA card.")
    return info


def known_images(extra: Iterable[Path] = ()) -> list[CardImage]:
    candidates: list[Path] = []
    search_dirs = [IMAGES_DIR, Path.home() / "Saab", Path.home() / "Downloads", Path.home() / "Documents"]
    for directory in search_dirs:
        try:
            if directory.is_dir():
                for pattern in ("*.bin", "*.BIN"):
                    candidates.extend(directory.glob(pattern))
        except OSError:
            pass
    candidates.extend(Path(p) for p in extra)
    seen: set[Path] = set()
    images: list[CardImage] = []
    for path in candidates:
        try:
            resolved = path.expanduser().resolve()
        except OSError:
            continue
        if resolved in seen or not resolved.is_file():
            continue
        seen.add(resolved)
        try:
            images.append(inspect_image(resolved))
        except OSError:
            continue
        if len(images) >= 100:
            break
    images.sort(key=lambda i: (i.version if i.version is not None else -1, i.path.name), reverse=True)
    return images


def copy_image_to_library(path: str | os.PathLike[str]) -> Path:
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    src = Path(path).expanduser()
    dst = IMAGES_DIR / src.name
    if src.resolve() != dst.resolve():
        shutil.copy2(src, dst)
    return dst


def format_size(num: int) -> str:
    return f"{num / (1024 * 1024):g} MB"


def install_hint() -> str:
    if not APP_DIR.is_dir():
        return f"Card Writer files are missing from {APP_DIR}."
    if wine_binary() is None:
        return "Wine is not installed. Install the 'wine' package or use the bundled build."
    return ""
