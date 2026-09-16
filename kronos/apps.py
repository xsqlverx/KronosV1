"""Installed-app inventory. Launch targets come from the OS, not model text."""
from __future__ import annotations

import hashlib
import json
import os
import platform
import plistlib
import subprocess
import time
import unicodedata
from dataclasses import asdict, dataclass
from pathlib import Path

from .contracts import Result, ToolError, success


def run(args: list[str], timeout: int = 15) -> subprocess.CompletedProcess:
    options = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}
    try:
        result = subprocess.run(args, capture_output=True, text=True, encoding="utf-8",
                                errors="replace", timeout=timeout, **options)
    except subprocess.TimeoutExpired:
        raise ToolError("timeout", "The operating system command timed out; its outcome is unknown.") from None
    if result.returncode:
        raise ToolError("os_command_failed", (result.stderr or result.stdout or "OS command failed.").strip()[:600])
    return result


def powershell(script: str) -> str:
    # Scripts are application-authored; user/model strings are never interpolated.
    return run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
                "[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new(); " + script]).stdout


def normalize(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


@dataclass(frozen=True)
class App:
    id: str
    name: str
    target: str
    kind: str

    @classmethod
    def make(cls, name: str, target: str, kind: str) -> "App":
        ident = hashlib.sha256((kind + ":" + target).encode("utf-8")).hexdigest()[:16]
        return cls(ident, name, target, kind)

    def public(self) -> dict:
        return {"id": self.id, "name": self.name, "source": self.kind, "location": self.target}


class AppCatalog:
    def __init__(self):
        self.system = platform.system()
        self.apps: list[App] = []
        self.warnings: list[str] = []
        self.refreshed = 0.0

    def refresh(self) -> None:
        self.warnings = []
        if self.system == "Windows":
            found = self._windows()
        elif self.system == "Darwin":
            found = self._macos()
        else:
            raise ToolError("unsupported", "App discovery currently supports Windows and macOS.")
        # Collapse identical targets, preserving distinct apps with similar names.
        self.apps = sorted({a.id: a for a in found}.values(), key=lambda a: (normalize(a.name), a.id))
        self.refreshed = time.monotonic()

    def _windows(self) -> list[App]:
        apps: list[App] = []
        try:
            raw = powershell("Get-StartApps | Select-Object Name,AppID | ConvertTo-Json -Compress")
            records = json.loads(raw) if raw.strip() else []
            if isinstance(records, dict):
                records = [records]
            for record in records:
                name, target = record.get("Name"), record.get("AppID")
                if isinstance(name, str) and isinstance(target, str) and target:
                    apps.append(App.make(name, target, "start_apps"))
        except (ToolError, OSError, ValueError, TypeError):
            self.warnings.append("Windows Start-app inventory was unavailable; other sources were checked.")
        names = {normalize(a.name) for a in apps}
        import winreg
        for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            for view in (winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY):
                try:
                    with winreg.OpenKey(hive, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths", 0, winreg.KEY_READ | view) as root:
                        for index in range(winreg.QueryInfoKey(root)[0]):
                            subname = winreg.EnumKey(root, index)
                            try:
                                with winreg.OpenKey(root, subname) as entry:
                                    target = os.path.expandvars(winreg.QueryValueEx(entry, "")[0]).strip('"')
                                path = Path(target)
                                if path.is_file() and path.suffix.lower() == ".exe":
                                    name = path.stem
                                    if normalize(name) not in names:
                                        apps.append(App.make(name, str(path), "app_paths"))
                                        names.add(normalize(name))
                            except (OSError, TypeError):
                                continue
                except OSError:
                    continue
        for variable in ("APPDATA", "PROGRAMDATA"):
            base = os.environ.get(variable)
            if not base:
                continue
            directory = Path(base) / "Microsoft/Windows/Start Menu/Programs"
            for path in directory.rglob("*.lnk"):
                if normalize(path.stem) not in names:
                    apps.append(App.make(path.stem, str(path), "shortcut"))
                    names.add(normalize(path.stem))
        return apps

    def _macos(self) -> list[App]:
        paths: set[Path] = set()
        try:
            result = run(["mdfind", "kMDItemContentType == 'com.apple.application-bundle'"], timeout=10)
            paths.update(Path(line) for line in result.stdout.splitlines() if line.endswith(".app"))
        except (ToolError, OSError):
            self.warnings.append("Spotlight unavailable; standard Applications folders were scanned.")
        for root in (Path("/Applications"), Path.home() / "Applications", Path("/System/Applications"), Path("/System/Library/CoreServices")):
            if not root.is_dir():
                continue
            for directory, children, _ in os.walk(root, followlinks=False):
                depth = len(Path(directory).relative_to(root).parts)
                keep = []
                for name in children:
                    if name.endswith(".app"):
                        paths.add(Path(directory) / name)
                    elif depth < 4:
                        keep.append(name)
                children[:] = keep
        apps = []
        for path in paths:
            if not path.is_dir():
                continue
            name = path.stem
            try:
                with (path / "Contents/Info.plist").open("rb") as handle:
                    info = plistlib.load(handle)
                name = info.get("CFBundleDisplayName") or info.get("CFBundleName") or name
            except (OSError, ValueError, plistlib.InvalidFileException):
                pass
            apps.append(App.make(str(name), str(path), "bundle"))
        return apps

    def _ensure(self, refresh: bool = False) -> None:
        if refresh or not self.refreshed or time.monotonic() - self.refreshed > 300:
            self.refresh()

    def list(self, query: str = "", refresh: bool = False, offset: int = 0, limit: int = 40) -> Result:
        self._ensure(refresh)
        matches = [a for a in self.apps if normalize(query) in normalize(a.name)]
        return success(f"Found {len(matches)} matching installed apps.",
                       apps=[a.public() for a in matches[offset:offset + limit]],
                       total=len(matches), offset=offset, warnings=self.warnings)

    def open(self, query: str) -> Result:
        if not normalize(query):
            raise ToolError("invalid_arguments", "Provide an app name or discovered ID.")
        self._ensure()
        matches = [a for a in self.apps if a.id == query or normalize(a.name) == normalize(query)]
        if not matches:
            matches = [a for a in self.apps if normalize(query) in normalize(a.name)]
        if not matches:
            return Result(False, "not_found", "No installed app matched. Refresh apps_list or provide its installed name.", {"warnings": self.warnings})
        if len(matches) != 1:
            return Result(False, "ambiguous", "Several apps match. Ask the user to choose, then use its ID.",
                          {"apps": [a.public() for a in matches[:25]]})
        app = matches[0]
        if app.kind == "bundle":
            run(["open", "-a", app.target])
        elif app.kind == "start_apps":
            # Explorer accepts the OS-provided application ID, never a shell expression.
            subprocess.Popen(["explorer.exe", "shell:AppsFolder\\" + app.target])
        elif app.kind in ("shortcut", "app_paths"):
            if not Path(app.target).is_file():
                raise ToolError("not_found", "App was removed or moved. Refresh the inventory.")
            os.startfile(app.target)
        else:
            raise ToolError("unsupported", "Unknown application launch method.")
        return Result(True, "launch_requested", f"Asked the OS to open {app.name}; app readiness is not verified.", {"app": app.public()})
