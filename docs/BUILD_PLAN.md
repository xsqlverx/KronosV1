# KRONOS prototype build

Scope agreed September 16, 2026: a text-first desktop agent; macOS primary,
Windows secondary. The proactive personal butler is the later product goal.
Upstream baseline: Mark-LIII `b3f7708`.

## Implementation

- Add an independent `python -m kronos` entry point. Keep upstream voice/UI
  available while removing their dependency from the new desktop agent.
- Configure NVIDIA NIM, OpenRouter, or Groq per session. Use one tool-capable
  model initially; additional routing should follow measured model behavior.
- Validate every tool argument before execution; return structured outcomes.
- Discover installed applications, resolve ambiguity, then launch identified apps.
- Add bounded file operations and OS-specific settings adapters.
- Require local terminal confirmation for overwrites and trash operations.
- Bound model loops and suppress repeated identical mutations within one request.
- Add offline tests and Windows/macOS CI; report desktop checks separately.

## Verification limits

This machine is Windows. CI can check macOS installation, imports, and mocked
adapter contracts, but cannot prove another person's desktop permissions or
hardware. A Groq key was subsequently found through the environment and used for
synthetic live checks. NVIDIA/OpenRouter credentials were not available.

## Initial findings

- Python 3.12.10 environment exists; `pip check` passes outside the sandbox.
- Upstream launcher uses fixed aliases and unverified keyboard-search fallbacks.
- Upstream Gemini Live is coupled to UI/audio startup.
- Upstream `.gitignore` has inline comments that invalidate three secret rules.
- Git remote still points at upstream; no push is part of this build.

## Build result

The text runtime, 15 tools, minimal setup launchers, offline tests, and CI
configuration are implemented. Windows hardware and Groq tool use were tested.
See `HANDOFF.md` for exact results, limitations, and the next review steps.
