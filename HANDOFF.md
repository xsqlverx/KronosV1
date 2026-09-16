# KRONOS morning brief — September 16, 2026

## Follow-up: native API-key setup

`python -m kronos setup` now opens a native PyQt6 window with custom QPainter
artwork, provider selection, model entry, masked key entry, Paste/Show controls,
and background credential saving. Terminal setup remains available with
`setup --terminal`. Reopen via `bash start-kronos.command setup` on Mac or
`start-kronos.cmd setup` on Windows after updating the checkout.

New files: `kronos/setup_ui.py`, `kronos/credentials.py`, `tests/test_setup.py`.
Updated: CLI setup dispatch, credential lookup (stored key precedes environment
key), Qt dependencies, and run documentation. Save checks read-back from the OS
credential store and never writes the key to configuration. It does not claim
to test provider access. A blocked keychain/configuration write shows an inline
error. Existing timeout/token settings are retained.

The UI was rendered and inspected on Windows. Save tests use a mock credential
store, so no real key was changed during validation. Mac Keychain interaction
still needs the friend's machine. Original build results follow below.

## Outcome

A working text-agent prototype is implemented alongside the original Mark-LIII
application. The core can discover apps dynamically, launch them, read/write
text files, copy/move/rename individual files, and change supported system
settings. It has 15 structured tools and a configurable provider transport.

This is a Windows-verified prototype, not a completed Mac gift build.

## Run it now

From `C:\KRONOS` in PowerShell:

```powershell
.\.venv-kronos\Scripts\python.exe -m kronos --config config/kronos.example.json chat
```

The example uses Groq `openai/gpt-oss-20b`. The existing environment already
contains a Groq key; no key was displayed or copied into source files. No
NVIDIA/OpenRouter keys were found by the intended credential lookup.

For persistent personal setup, run `start-kronos.cmd`. Its wizard stores
configuration under the user profile and uses the OS credential store for keys.
The wizard/keychain write itself has not been exercised with the user's key.

## Verified evidence

| Check | Result |
| --- | --- |
| Fresh minimal environment | Created `.venv-kronos`; installation and `pip check` passed |
| Regression suite | 36 tests run: 35 passed, 1 Windows symlink-permission skip |
| Dependency-free startup | `python -S -m kronos tools` passed; no UI/audio/SDK imports required |
| App discovery | 231 OS inventory entries found, with no discovery warnings |
| App launch | Calculator launched through a discovered OS app ID; CalculatorApp process/window observed |
| Volume | Changed 32 → 33, verified, restored to 32 |
| Mute | Changed false → true, verified, restored to false |
| Brightness | Changed 60 → 61, verified, restored to 60 |
| Live model/tool loop | Groq wrote exactly `KRONOS_READY` to a disposable file, read it back, and replied; disk contents independently matched |
| Full CLI/model interaction | Natural-language request opened Windows sound settings; SystemSettings process/window observed |
| macOS launcher syntax | `bash -n` passed using Git Bash; this is not a Mac runtime test |
| Secret exclusions | Three formerly broken `.gitignore` rules now match their intended paths |
| Whitespace check | `git diff --check` passed |

The temporary live-test file was removed when its disposable test directory
closed. Calculator and Settings may remain open. Original audio and brightness
settings were restored and subsequently re-read successfully.

## Core decisions and fixes

- Added a separate `python -m kronos` runtime so the prototype works without
  Gemini Live, the legacy HUD, microphone services, or proactive startup work.
- Kept the original application files intact. This is a new core entry point,
  not a cosmetic rename of the upstream app.
- App targets come from Windows Start Apps/App Paths/shortcuts or macOS
  Spotlight/application bundles. Ambiguous names return choices with IDs and
  locations; no typing app names into Start/Spotlight and assuming success.
- Tools validate inputs and return structured outcomes. Overwrites and Trash
  require local terminal confirmation; models cannot approve their own actions.
- Repeated identical mutations within a request are not executed again. Provider
  requests are not automatically retried; prior tool outcomes remain in history.
- Volume/mute/brightness report read-back results. Windows WMI brightness on
  this machine returns no numeric method status; the adapter now handles that.
- Groq initially rejected the default Python client header at its gateway.
  Explicit KRONOS client identification fixed this. A read-only model listing
  was used to select an actually available model. One early GPT-OSS request
  returned HTTP 400; subsequent live file-tool and settings runs passed. This
  sample is not a long-run model-reliability benchmark.
- Pinned the four direct minimal dependencies to the versions installed here.
  Windows-only packages carry platform markers. Added line-ending attributes
  so shell launchers remain LF and Windows launchers use CRLF.

## Remaining work and limitations

1. **Mac desktop verification:** no actual macOS execution happened. App launch,
   AppleScript volume, file permissions, keychain setup, and hardware controls
   still need the friend's machine. Architecture/OS versions are not yet known.
2. **Mac brightness:** requires the optional `brightness` utility and supported
   hardware. Without it, the tool returns unsupported. Mac Settings opens the
   main window; direct pane navigation is not implemented.
3. **Provider coverage:** Groq is live-tested. NVIDIA/OpenRouter share the tested
   transport but have no live credential/model verification. Sessions use one
   provider/model; task splitting across providers is not implemented yet.
4. **Portability delivery:** launchers exist, but Python and a checkout/API key
   remain prerequisites. The final four-step gift onboarding is not complete.
5. **Scope:** text-only new runtime. No new voice integration, custom UI,
   anticipation, persistent conversation memory, or background monitoring.
6. **Files:** UTF-8 read/write up to 100 KB; individual file copies up to 50 MB.
   Directory copy/move and binary document parsing are deferred. Overwrite has
   confirmation and atomic replacement, but no user-facing undo yet. File roots
   constrain normal use; they are not a hostile-process filesystem sandbox.
7. **CI:** Windows/macOS Python 3.11/3.12 workflow added locally, not yet executed
   on GitHub. Offline Mac adapter tests do not prove hardware behavior.

## File map

| Files | Purpose |
| --- | --- |
| `kronos/agent.py`, `providers.py` | Model loop, provider transport and credentials |
| `kronos/contracts.py`, `runtime.py` | Tool validation, outcomes, registration |
| `kronos/apps.py`, `files.py`, `system.py` | App discovery, filesystem and OS actions |
| `kronos/__main__.py`, `__init__.py` | CLI, setup, diagnostics and package |
| `requirements-kronos.txt`, `config/kronos.example.json` | Minimal dependencies and non-secret example configuration |
| `start-kronos.cmd`, `start-kronos.command`, `scripts/bootstrap_kronos.py` | Portable developer startup |
| `tests/test_kronos.py`, `scripts/verify_kronos.py` | Offline regressions and opt-in real-system checks |
| `.github/workflows/kronos.yml` | Cross-platform CI configuration |
| `.gitignore`, `.gitattributes` | Secret/environment exclusions and portable line endings |
| `docs/KRONOS.md`, `docs/BUILD_PLAN.md`, `HANDOFF.md` | Run guide, scope and evidence |

## Antigravity's next bounded work

- Run the documented checks and report exact failures without restructuring the core.
- Obtain the user's own GitHub repository URL before changing the remote.
  Current `origin` is still `https://github.com/FatihMakes/Mark-LIII.git`.
- Commit/push these changes only into the intended user repository when asked.
- Watch the new CI run after push and return concrete failures for correction.
- Preserve upstream attribution/license. Do not commit `.venv*`, credentials,
  runtime memory, or linked sessions.

No commits or pushes were made during this build.
