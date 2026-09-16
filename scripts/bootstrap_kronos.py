"""Portable development launcher; no global package installation."""
from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    if sys.version_info[:2] not in ((3, 11), (3, 12)):
        print("This prototype is validated for Python 3.11/3.12. Install one of those versions and run the launcher again.")
        return 2
    os.chdir(ROOT)
    environment = ROOT / ".venv-kronos"
    python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    requirements = ROOT / "requirements-kronos.txt"
    stamp = environment / ".requirements-sha256"
    digest = hashlib.sha256(requirements.read_bytes()).hexdigest()
    try:
        if not python.is_file():
            print("Creating KRONOS's isolated environment...", flush=True)
            subprocess.run([sys.executable, "-m", "venv", str(environment)], check=True)
        if not stamp.is_file() or stamp.read_text().strip() != digest:
            print("Installing KRONOS dependencies...", flush=True)
            subprocess.run([str(python), "-m", "pip", "install", "-r", str(requirements)], check=True)
            subprocess.run([str(python), "-m", "pip", "check"], check=True)
            stamp.write_text(digest, encoding="utf-8")
        # Explicit diagnostics and command arguments do not trigger setup.
        if len(sys.argv) > 1:
            return subprocess.call([str(python), "-m", "kronos", *sys.argv[1:]])
        check = subprocess.run([str(python), "-c",
                                "from kronos.providers import Config,find_key; from kronos.__main__ import default_config; "
                                "c=Config.load(default_config()); raise SystemExit(0 if c.model and find_key(c.provider) else 2)"])
        if check.returncode:
            result = subprocess.call([str(python), "-m", "kronos", "setup"])
            if result:
                return result
        return subprocess.call([str(python), "-m", "kronos", "chat"])
    except subprocess.CalledProcessError:
        print("Setup failed. Check the installer message above and your connection, then rerun this launcher. No global packages were changed.")
        return 1
    except OSError as exc:
        print(f"Could not start KRONOS: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
