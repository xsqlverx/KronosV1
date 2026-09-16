"""Run: python -m kronos [doctor | setup | tools | call TOOL JSON | chat]."""
from __future__ import annotations

import argparse
import getpass
import importlib.util
import json
import platform
import sys
from dataclasses import asdict
from pathlib import Path

from .agent import Agent, strict_json
from .providers import Client, Config, PROVIDERS, ProviderError, default_model, find_key
from .runtime import build_registry


def confirm(description: str) -> bool:
    if not sys.stdin.isatty():
        return False
    try:
        return input(f"\n{description}\nType YES to proceed: ").strip() == "YES"
    except (EOFError, KeyboardInterrupt):
        return False


def default_config() -> Path:
    return Path.home() / ".kronos" / "config.json"


def setup_terminal(path: Path) -> int:
    if not sys.stdin.isatty():
        print("Setup requires an interactive terminal.")
        return 2
    provider = input("Provider (groq/openrouter/nvidia): ").strip().lower()
    if provider not in PROVIDERS:
        print("Unknown provider.")
        return 2
    model = default_model(provider)
    print(f"Using default model: {model}")
    key = getpass.getpass("API key (hidden; blank to use the environment): ").strip()
    if key:
        try:
            import keyring
            keyring.set_password("kronos", provider, key)
        except Exception:
            print(f"OS credential storage unavailable. Set {PROVIDERS[provider][1]} in your environment; the key was not written to a file.")
            return 2
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(Config(provider=provider, model=model)), indent=2) + "\n", encoding="utf-8")
    print(f"Configuration saved to {path}. Run python -m kronos chat.")
    return 0


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="KRONOS desktop agent prototype")
    parser.add_argument("--config", type=Path, default=default_config())
    parser.add_argument("--root", type=Path, action="append", help="Allowed file root, repeatable. Default: home and working directory.")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("doctor", help="Read-only environment and device checks; no network or AI calls")
    setup_parser = sub.add_parser("setup", help="Open the native API-key setup window")
    setup_parser.add_argument("--terminal", action="store_true", help="Use legacy terminal prompts instead")
    sub.add_parser("tools", help="Print tool schemas without model credentials")
    call = sub.add_parser("call", help="Directly invoke a tool without a model")
    call.add_argument("tool")
    call.add_argument("arguments", help="JSON object, or - to read JSON from stdin")
    chat = sub.add_parser("chat", help="Interactive text agent")
    chat.add_argument("--once", help="Process a single request")
    args = parser.parse_args(argv)
    if args.command == "setup":
        if args.terminal:
            return setup_terminal(args.config)
        try:
            from .setup_ui import run_setup
        except ImportError:
            print("Install the updated requirements-kronos.txt or rerun start-kronos to enable the native setup window.")
            return 2
        return run_setup(args.config)
    roots = [p.resolve() for p in (args.root or [Path.home(), Path.cwd()])]
    registry = build_registry(roots, confirm)
    if args.command == "tools":
        print(json.dumps(registry.declarations(), indent=2))
        return 0
    if args.command == "call":
        try:
            raw = sys.stdin.read(120_001) if args.arguments == "-" else args.arguments
            if len(raw) > 120_000:
                raise ValueError("too large")
            arguments = strict_json(raw)
        except (ValueError, RecursionError):
            print(json.dumps({"ok": False, "code": "invalid_arguments", "message": "Provide valid JSON up to 120 KB."}))
            return 2
        result = registry.execute(args.tool, arguments)
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
        return 0 if result.ok else 1
    try:
        config = Config.load(args.config)
        if args.command == "doctor":
            report = {"python": platform.python_version(), "platform": platform.platform(),
                      "config_path": str(args.config), "provider": config.provider,
                      "model": config.model or "not configured", "key_available": bool(find_key(config.provider)),
                      "file_roots": [str(p) for p in roots], "tools": len(registry.tools),
                      "optional_packages": {name: importlib.util.find_spec(name) is not None for name in ("keyring", "send2trash", "pycaw")},
                      "system": registry.execute("system_get", {}).to_dict(),
                      "mac_desktop_verified": False}
            print(json.dumps(report, indent=2, ensure_ascii=False))
            return 0
        client = Client(config)
        if not config.model or not client.key:
            print("KRONOS needs a provider model and API key. Run python -m kronos setup. Tools and doctor work without credentials.")
            return 2
        def show(name, result):
            print(f"[{name}] {result.code}: {result.message}", flush=True)
        agent = Agent(client, registry, f"OS: {platform.system()}. Working directory: {Path.cwd()}. Allowed file roots: {[str(p) for p in roots]}", show)
        if getattr(args, "once", None):
            print(agent.ask(args.once))
            return 1 if agent.last_error else 0
        print("KRONOS — type a request; /reset clears conversation, /quit exits.")
        while True:
            try:
                request = input("You> ").strip()
            except EOFError:
                break
            if request == "/quit":
                break
            if request == "/reset":
                agent.turns.clear()
                print("Conversation cleared.")
            elif request:
                print("KRONOS>", agent.ask(request))
        return 0
    except ProviderError as exc:
        print(str(exc))
        return 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nStopped. Check the last tool result before retrying an interrupted action.")
        raise SystemExit(130)
