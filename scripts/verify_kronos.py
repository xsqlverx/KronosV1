"""Opt-in real-system checks. No cloud calls or mutations without explicit flags.

Run from repository root: python scripts/verify_kronos.py
Add --settings to change and restore current settings, --launch NAME to open
one discovered app, or --live-model ID for a Groq test using disposable files.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kronos.agent import Agent
from kronos.apps import AppCatalog
from kronos.contracts import Registry
from kronos.providers import Client, Config, ProviderError
from kronos.runtime import build_registry
from kronos.system import System


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--settings", action="store_true")
    parser.add_argument("--launch")
    parser.add_argument("--live-model")
    args = parser.parse_args()
    report = {}
    catalog = AppCatalog()
    catalog.refresh()
    report["app_inventory"] = {"count": len(catalog.apps), "warnings": catalog.warnings}
    system = System()
    report["system"] = system.get().to_dict()
    if args.launch:
        report["launch"] = catalog.open(args.launch).to_dict()
    if args.settings:
        audio = system.volume_state()
        brightness = system.brightness_state()
        try:
            report["volume_change"] = system.volume(audio["volume"] + (1 if audio["volume"] < 100 else -1)).to_dict()
            report["mute_change"] = system.mute(not audio["muted"]).to_dict()
            if len(brightness) == 1:
                value = brightness[0]["brightness"]
                report["brightness_change"] = system.brightness(value + (1 if value < 100 else -1)).to_dict()
        except Exception as exc:
            report["settings_error"] = str(exc)
        finally:
            # Restoration attempts are independent so an audio failure cannot
            # prevent restoring brightness (or vice versa).
            for label, restore in (
                ("volume", lambda: system.volume(audio["volume"])),
                ("mute", lambda: system.mute(audio["muted"])),
                ("brightness", lambda: system.brightness(brightness[0]["brightness"]) if len(brightness) == 1 else None),
            ):
                try:
                    result = restore()
                    report[label + "_restored"] = result.to_dict() if result else "not changed"
                except Exception as exc:
                    report[label + "_restored"] = {"error": type(exc).__name__}
    if args.live_model:
        # This model sees synthetic content only, with file access restricted to
        # a fresh disposable folder. OS/app tools are not exposed in this check.
        with tempfile.TemporaryDirectory(prefix="kronos-smoke-") as directory:
            root = Path(directory).resolve()
            target = root / "smoke.txt"
            all_tools = build_registry([root])
            registry = Registry([all_tools.tools[name] for name in ("file_write", "file_read")])
            events = []
            provider_diagnostics = []
            class DiagnosticClient(Client):
                def complete(self, messages, tools):
                    try:
                        return super().complete(messages, tools)
                    except ProviderError as exc:
                        underlying = exc.__context__
                        if isinstance(underlying, urllib.error.HTTPError):
                            raw = underlying.read(4000).decode("utf-8", errors="replace")
                            provider_diagnostics.append(raw.replace(self.key, "[REDACTED]"))
                        raise
            agent = Agent(DiagnosticClient(Config(provider="groq", model=args.live_model)), registry,
                          f"Only allowed folder: {root}", lambda name, result: events.append({"tool": name, "result": result.to_dict()}))
            answer = agent.ask(f"Write exactly KRONOS_READY to the text file {target}, then read it back and tell me its contents.")
            report["live_agent"] = {
                "provider": "groq", "model": args.live_model, "answer": answer,
                "diagnostics": provider_diagnostics,
                "tools_executed": [{"tool": e["tool"], "ok": e["result"]["ok"], "code": e["result"]["code"]} for e in events],
                "file_verified": target.exists() and target.read_text(encoding="utf-8") == "KRONOS_READY",
            }
    print(json.dumps(report, indent=2))
    failed = bool(report.get("settings_error"))
    for label, item in report.items():
        if label.endswith(("_change", "_restored")) and isinstance(item, dict):
            failed |= not item.get("ok", False)
    if args.live_model:
        failed |= not report["live_agent"]["file_verified"]
    if args.launch:
        failed |= not report["launch"]["ok"]
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
