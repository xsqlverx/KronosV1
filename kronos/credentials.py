"""Credential setup shared by native and terminal interfaces."""
from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict
from pathlib import Path

from .providers import Config, PROVIDERS, ProviderError, default_model


class SetupError(Exception):
    pass


def save_connection(path: Path, provider: str, model: str, key: str, store=None) -> None:
    model, key = model.strip(), key.strip()
    if provider not in PROVIDERS:
        raise SetupError("Choose a provider.")
    if not model:
        model = default_model(provider)
    if not model or len(model) > 256 or any(c.isspace() for c in model):
        raise SetupError("KRONOS could not choose a valid default model for this provider.")
    if not key or any(c.isspace() for c in key):
        raise SetupError("Paste your API key. It must not contain spaces or line breaks.")
    if len(key) > 4096:
        raise SetupError("That key is too long. Paste only the API key.")
    for variable, selected in (("KRONOS_PROVIDER", provider), ("KRONOS_MODEL", model)):
        if os.environ.get(variable) and os.environ[variable] != selected:
            raise SetupError(f"{variable} overrides this selection. Remove that environment override or match its value here.")
    try:
        previous = Config.load(path)
    except ProviderError:
        previous = Config()
    config = Config(provider=provider, model=model, timeout=previous.timeout, max_tokens=previous.max_tokens)
    try:
        if store is None:
            import keyring as store
        path.parent.mkdir(parents=True, exist_ok=True)
        # Stage the non-secret configuration before updating credentials.
        fd, temporary = tempfile.mkstemp(prefix=".config-", suffix=".json", dir=path.parent)
    except Exception:
        raise SetupError("Could not prepare configuration storage. Check folder permissions and install requirements-kronos.txt.") from None
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(asdict(config), handle, indent=2)
            handle.write("\n")
        try:
            store.set_password("kronos", provider, key)
            if store.get_password("kronos", provider) != key:
                raise RuntimeError("Credential read-back failed")
        except Exception:
            raise SetupError("The OS credential store could not save or read back the key. On Mac, allow Keychain access if prompted, then try again. No key was written to a file.") from None
        try:
            os.replace(temporary, path)
        except OSError:
            raise SetupError("The key was saved, but configuration could not be updated. Check folder permissions and retry.") from None
    finally:
        Path(temporary).unlink(missing_ok=True)
