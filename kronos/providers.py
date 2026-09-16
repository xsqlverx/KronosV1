"""Small Chat Completions transport shared by the three requested providers."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path


PROVIDERS = {
    "groq": ("https://api.groq.com/openai/v1", "GROQ_API_KEY"),
    "openrouter": ("https://openrouter.ai/api/v1", "OPENROUTER_API_KEY"),
    "nvidia": ("https://integrate.api.nvidia.com/v1", "NVIDIA_API_KEY"),
}

DEFAULT_MODELS = {
    "groq": "openai/gpt-oss-120b",
    "openrouter": "openrouter/auto",
    "nvidia": "meta/llama-3.3-70b-instruct",
}


class ProviderError(Exception):
    pass


def default_model(provider: str) -> str:
    if provider not in DEFAULT_MODELS:
        raise ProviderError(f"Choose a provider from {', '.join(PROVIDERS)}.")
    return DEFAULT_MODELS[provider]


@dataclass(frozen=True)
class Config:
    provider: str = "groq"
    model: str = ""
    timeout: int = 45
    max_tokens: int = 2048

    @classmethod
    def load(cls, path: Path | None = None) -> "Config":
        values = {}
        if path and path.exists():
            try:
                values = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                raise ProviderError("Configuration is not readable JSON.") from None
            if not isinstance(values, dict) or set(values) - {"provider", "model", "timeout", "max_tokens"}:
                raise ProviderError("Configuration allows only provider, model, timeout, and max_tokens. Store keys in the OS credential store or environment.")
        values["provider"] = os.environ.get("KRONOS_PROVIDER", values.get("provider", "groq"))
        values["model"] = os.environ.get("KRONOS_MODEL", values.get("model", ""))
        cfg = cls(**values)
        if not isinstance(cfg.provider, str) or cfg.provider not in PROVIDERS:
            raise ProviderError(f"Choose a provider from {', '.join(PROVIDERS)}.")
        if not isinstance(cfg.model, str) or len(cfg.model) > 256:
            raise ProviderError("Model must be a model ID string.")
        if type(cfg.timeout) is not int or not 1 <= cfg.timeout <= 120:
            raise ProviderError("Timeout must be 1–120 seconds.")
        if type(cfg.max_tokens) is not int or not 128 <= cfg.max_tokens <= 8192:
            raise ProviderError("max_tokens must be 128–8192.")
        return cfg


def find_key(provider: str) -> str:
    try:
        import keyring
        stored = keyring.get_password("kronos", provider)
        if stored:
            return stored
    except Exception:
        pass
    return os.environ.get(PROVIDERS[provider][1], "").strip()


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Never forward the bearer credential to a redirect target.
        return None


class Client:
    def __init__(self, config: Config, key: str | None = None):
        self.config = config
        self.key = find_key(config.provider) if key is None else key
        self.opener = urllib.request.build_opener(_NoRedirect())

    def complete(self, messages: list[dict], tools: list[dict]) -> dict:
        if not self.config.model.strip():
            raise ProviderError("No model configured. Run python -m kronos setup or set KRONOS_MODEL to a tool-capable model ID.")
        if not self.key:
            raise ProviderError(f"No {self.config.provider} key configured. Run setup or set {PROVIDERS[self.config.provider][1]}.")
        payload = {"model": self.config.model, "messages": messages,
                   "stream": False, "max_tokens": self.config.max_tokens,
                   "tools": tools, "tool_choice": "auto"}
        if self.config.provider == "openrouter" and self.config.model == "openrouter/auto":
            payload["plugins"] = [{"id": "auto-router", "cost_tier": "max"}]
        request = urllib.request.Request(
            PROVIDERS[self.config.provider][0] + "/chat/completions",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Authorization": "Bearer " + self.key, "Content-Type": "application/json",
                     "Accept": "application/json", "User-Agent": "KRONOS/0.1"},
            method="POST",
        )
        try:
            with self.opener.open(request, timeout=self.config.timeout) as response:
                raw = response.read(2_000_001)
            if len(raw) > 2_000_000:
                raise ProviderError("Provider response exceeded the size limit.")
            data = json.loads(raw)
            choice = data["choices"][0]
            if choice.get("finish_reason") in ("length", "content_filter"):
                raise ProviderError("Provider response was truncated or filtered; no tools from that response were executed.")
            message = choice["message"]
            if not isinstance(message, dict):
                raise ValueError("Invalid message")
            return message
        except urllib.error.HTTPError as exc:
            explanations = {
                400: "Request rejected; check model tool support and configuration.",
                401: "The API key was rejected.", 403: "Access denied by the provider or its gateway.",
                404: "Model or endpoint was not found.", 429: "Provider rate limit or quota reached.",
            }
            raise ProviderError(f"{self.config.provider} HTTP {exc.code}: " + explanations.get(exc.code, "Provider request failed.")) from None
        except (urllib.error.URLError, TimeoutError, OSError):
            raise ProviderError("Provider connection failed or timed out. No request was automatically replayed.") from None
        except (ValueError, KeyError, IndexError, TypeError):
            raise ProviderError("Provider returned an invalid Chat Completions response.") from None
