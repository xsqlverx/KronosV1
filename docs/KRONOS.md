# KRONOS: desktop prototype

KRONOS's eventual purpose is a personal butler that learns and anticipates its
owner's needs. This build implements the first foundation: a text agent that
can discover/open apps, work with files, and control supported system settings.
Custom UI, new voice integration, and anticipation are deferred.

The upstream Mark-LIII application is still launched with `python main.py`.
The new KRONOS runtime is launched with `python -m kronos`. It does not import
the upstream UI, microphone, Gemini SDK, or proactive services.

## Try it on the development Windows machine

From the repository folder:

```powershell
.\.venv-kronos\Scripts\python.exe -m kronos --config config/kronos.example.json chat
```

The example selects Groq `openai/gpt-oss-20b`, which passed a live file-tool test
on September 16, 2026. It uses `GROQ_API_KEY` from the environment or an OS-stored
key. Model availability is provider/account-dependent and can change.

Try requests such as:

- "Open Calculator."
- "What are my current volume and brightness?"
- "Mute my speakers." / "Unmute my speakers."
- "Set volume to 25 percent."
- "Open sound settings."
- "Create a folder named kronos-demo here and write hello to a new note.txt inside it."
- "Read kronos-demo/note.txt."

Use `/reset` to clear conversation or `/quit` to exit. Tool outcomes are printed
before the model's final response. An OS launch request is not proof an app is
fully ready; KRONOS labels that distinction.

## Fresh checkout

Prerequisites for this developer build: Python 3.11 or 3.12, the source checkout,
an internet connection for installation and chat, and a provider API key.
This is not yet a packaged four-step gift installation.

Windows:

```bat
start-kronos.cmd
```

macOS (from Terminal inside the checkout):

```bash
bash start-kronos.command
```

The launcher creates `.venv-kronos`, installs KRONOS dependencies (including Qt
for native setup), and opens a native provider/key window if needed. Subsequent runs reuse that
environment; dependencies reinstall only when the requirements file changes.
The launcher does not install or alter global Python packages.

To reopen the native key-entry window after updating the checkout:

```bash
# macOS
bash start-kronos.command setup
```

```bat
:: Windows
start-kronos.cmd setup
```

Paste the key using the button or the normal keyboard shortcut, choose the
provider, then click **Save connection** and **Continue**. KRONOS chooses the
default model automatically. The key is
masked by default. The window reports save errors inline; saving does not claim
to validate API access. The regular launcher continues to the existing text
assistant after setup. This window configures the new KRONOS runtime, not the
legacy Gemini application launched by `main.py`.

For a text-only fallback: `python -m kronos setup --terminal`. Hidden terminal
key entry does not echo characters; native setup avoids that confusion.

Keys entered in setup are saved through `keyring` to the OS credential store.
Saved credentials take priority over environment keys, so replacing a key in
the window takes effect even if an older environment key remains set.
If the credential store is unavailable, setup reports that fact; it never falls
back to storing the key in JSON. Environment variables also work:

| Provider | Key variable | Endpoint |
| --- | --- | --- |
| Groq | `GROQ_API_KEY` | `https://api.groq.com/openai/v1` |
| NVIDIA NIM | `NVIDIA_API_KEY` | `https://integrate.api.nvidia.com/v1` |
| OpenRouter | `OPENROUTER_API_KEY` | `https://openrouter.ai/api/v1` |

Default models:

| Provider | Default model behavior |
| --- | --- |
| Groq | `openai/gpt-oss-120b` |
| NVIDIA NIM | `meta/llama-3.3-70b-instruct` |
| OpenRouter | `openrouter/auto` with max capability routing |

`KRONOS_PROVIDER` and `KRONOS_MODEL` override the configuration. The default
configuration file is `~/.kronos/config.json`; `--config PATH` selects another.
Only one provider/model is used per session today. Per-task routing across all
three is not implemented; the shared provider boundary is in place.

Official provider references used for the transport:
[Groq compatibility](https://console.groq.com/docs/openai),
[NVIDIA LLM APIs](https://docs.api.nvidia.com/nim/re/reference/llm-apis),
[OpenRouter tool calling](https://openrouter.ai/docs/guides/features/tool-calling).

## Files and confirmation

Default file roots are the current user's home and the current working directory.
Use one or more `--root PATH` arguments before the command to restrict access.
Resolved paths outside the selected roots are refused. Root folders themselves
cannot be moved, trashed, or overwritten. These checks are not an OS security
sandbox against a malicious process concurrently swapping filesystem paths.

Text read/write supports UTF-8 up to 100 KB. Individual file copy/move/rename is
supported; copy is capped at 50 MB. Directory copy/move and binary document
parsing are deferred. Folder creation and listing work.

Overwriting an existing file or moving a file to Trash requires typing `YES`
in the local terminal. A model cannot provide that approval through a tool
argument. Noninteractive input declines those operations. No permanent deletion
tool is exposed. Existing destinations are never overwritten by copy or move.
Text overwrites are atomic but do not yet have a user-accessible undo feature.

## Platform status

| Capability | Windows | macOS implementation |
| --- | --- | --- |
| App inventory | Start apps, App Paths registry, Start Menu shortcuts | Spotlight plus standard app directories |
| App launch | Discovered app ID/path | Discovered `.app` bundle path |
| Text and file tools | Supported | Shared portable implementation |
| Volume/mute | Core Audio via pycaw; read-back verified | AppleScript; read-back implemented |
| Brightness | WMI-capable displays; read-back verified | Optional `brightness` utility on supported displays |
| Settings | Main window and named sections | Main System Settings window only |

macOS brightness uses [nriley/brightness](https://github.com/nriley/brightness)
if already installed; KRONOS does not install it automatically. Without it,
KRONOS reports the limitation and can open Settings. External display support
varies on both platforms. macOS may request file access permissions for
protected folders. Actual permissions and hardware still need a Mac trial.

## Diagnostics and verification

```text
python -m kronos doctor
python -m kronos tools
python -m unittest discover -s tests -v
python scripts/verify_kronos.py
```

`doctor` checks configuration presence, packages, and device readouts without
sending a cloud request or changing settings. Its exit code is zero when the
diagnostic completes; inspect the report for unavailable capabilities.

The verification script is read-only by default. `--settings` changes and
restores volume/mute/brightness, `--launch Calculator` requests an app launch,
and `--live-model openai/gpt-oss-20b` sends synthetic file-tool requests to Groq.
The live check exposes only file read/write in a disposable folder to the model.

The GitHub Actions workflow checks Python 3.11/3.12 on Windows and macOS. It is
added locally, not yet run remotely. CI validates installation and offline
contracts, not an interactive Mac desktop.

## Architecture

- `kronos/agent.py`: bounded model/tool loop, complete-turn history, duplicate
  mutation suppression within each request, visible outcomes on provider failure.
- `kronos/providers.py`: credential lookup and Chat Completions transport; no
  automatic request replay and no forwarding credentials through redirects.
- `kronos/contracts.py`: tool schemas, validation, typed success/error outcomes.
- `kronos/runtime.py`: assembles the exposed tools independently of providers/UI.
- `kronos/apps.py`: OS app inventory, name disambiguation, discovered-target launch.
- `kronos/files.py`: bounded file operations and local confirmation callback.
- `kronos/system.py`: lazy platform adapters with settings read-back checks.
- `kronos/__main__.py`: CLI, setup wizard, direct tool calls, and diagnostics.

No arbitrary model-generated shell tool is exposed. Upstream action handlers
are not blindly wrapped: several return success strings without verifying OS
results. Their behavior informed the new adapters, which need stronger contracts.

## Before the gift handoff

1. Test on the friend's actual Mac (Apple Silicon/Intel and macOS version still
   need recording), including setup/keychain, app discovery, audio and file access.
2. Finish native brightness behavior or explicitly scope supported hardware.
3. Exercise NVIDIA/OpenRouter with supplied keys and chosen models, then decide
   whether task routing improves latency/reliability over one capable model.
4. Package Python/dependencies, streamline permissions and key setup, and count
   every required action against the four-step onboarding target.
5. Add the intended voice experience, then custom UI and learned anticipation.

Preserve the upstream attribution and license. Git `origin` currently points to
FatihMakes/Mark-LIII; switch to the user's own repository before any push.
