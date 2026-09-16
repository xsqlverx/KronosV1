# ⚙️ Kronos V1
### The Ultimate Cross-Platform Personal AI Assistant & Butler — By Noctvy

A real-time AI butler that can hear, see, understand, and control your computer — on any OS. Built with primary support for **macOS** and robust secondary support for **Windows**. Integrates real-time audio streaming, dynamic app discovery, safe file operations, OS settings control, and multi-provider intelligence (Groq, NVIDIA NIM, OpenRouter, and Gemini Live).

---

## ✨ Overview

**Kronos is your personal AI butler and autonomous desktop assistant.** Say **"Hey Kronos"** (or "Hey Jarvis") and it wakes; stay quiet and it slips back to sleep on its own — while asleep, your microphone never leaves the machine, so background chatter never sets it off. Under the hood, Kronos features a dual architecture:
1. **The Autonomous Agent Engine (`python -m kronos`)**: A lightweight, provider-agnostic runtime that dynamically discovers apps across macOS (Spotlight / App bundles) and Windows (Start Apps / App Paths), performs bounded and confirmed filesystem operations, and adapts system settings with verified read-backs.
2. **The Real-Time Voice HUD (`python main.py`)**: A rich, reactive desktop interface powered by Gemini Live for ultra-low latency voice streaming, webcam/screen vision, reactive audio waveforms, and instant acknowledgments.

Every skill — bundled or drop-in — **describes itself in its own file**, so adding a tool is a one-file operation and the core stays lean.

It's not just an assistant — it's an extension of your digital life.

---

## 🚀 Capabilities

### Core Features
| Feature | Description |
|---|---|
| 🤖 **Autonomous Agent Core** | Dedicated `kronos` engine: dynamic OS app discovery, safe file manipulation, and hardware controls across macOS and Windows |
| 🌐 **Multi-Provider Support** | Pluggable LLM integration supporting **Groq**, **NVIDIA NIM**, and **OpenRouter** alongside native Gemini Live |
| 🎙️ **Wake Word** | Local wake word detection — sleeps until called, auto-sleeps after 2 min of silence, and never streams audio while asleep. Opt-in, one-click download, toggle & manual sleep/wake from the UI |
| ⚡ **Instant Acknowledgment** | Speaks a short, context-aware reply in **your language** the instant a longer task starts — no more silent waiting |
| 🚀 **High-Speed Live Engine** | Ultra-responsive streaming via **Gemini 3.1 Flash Live** & high-throughput Groq models |
| 🧩 **Self-Describing Skills** | Actions and plugins share one shape (`TOOL` / `PLUGIN` dict + `run()`), auto-discovered at launch — adding or moving a skill is a single file |
| 🧠 **Recallable Memory** | No size limit and nothing silently forgotten — prompt carries active context, full facts queried on demand |
| 👁️ **Memory Panel** | See every fact Kronos has stored about you, when it learned it, and delete any of it in one click |
| ↩️ **Undo** | Take back what Kronos did — files it moved, renamed, created, or wrote, and settings it changed |
| ⚠️ **Real Confirmation** | Overwrites, deletions, and power actions require explicit confirmation — models cannot forge approvals |
| 🎧 **Audio Device Picker** | Choose microphone and speakers by name with calibrated hardware measurement |
| 🔗 **Session Continuity** | Dropped connections or voice switches never wipe conversation history |
| 🧩 **Plugin System** | Drop a single `.py` file into `plugins/` — Kronos learns a new skill on next launch |
| 🎨 **Live Theming** | Recolour the entire HUD from a hue wheel or hex — applied instantly across every panel |
| 〰️ **Reactive HUD** | Waveform and reactor core pulse to real audio — your mic while listening, Kronos while speaking |
| 🖥️ **System Control** | Launch apps, adjust volume/brightness, WiFi, shortcuts, power — with verified read-back verification |
| 👁️ **Visual Awareness** | Real-time screen capture and webcam vision piped into your session |
| 📂 **File Operations** | Read/write text files, safe copy/move/rename, folder creation, and desktop organization |
| 🔍 **Multi-Mode Web Search** | `news` / `research` / `price` / `compare` / `search` — Gemini Grounded first, DDG fallback |
| ⏰ **Smart Reminders** | OS-native scheduled notifications (macOS LaunchAgent / Windows Task Scheduler / Linux systemd) |
| 📱 **Remote Dashboard** | Control Kronos from your phone via secure local pairing |
| ⚡ **Auto-Start on Boot** | Registers with the OS startup system (macOS LaunchAgent / Windows Registry / Linux .desktop) |

---

## 🆕 What's New in Kronos V1

Kronos V1 introduces a brand-new architecture designed for **true portability, macOS compatibility, and modular autonomy**:

### 🤖 The Standalone KRONOS Engine
* **Dynamic App Discovery**: Discovers installed apps without hardcoded shortcut paths — uses Spotlight / `.app` bundles on macOS, and Start Apps / App Paths on Windows.
* **Portable System Adapters**: Volume, mute, brightness, and settings navigation with automatic read-backs. Unsupported hardware or missing permissions report clear, actionable messages.
* **Guaranteed Safety Gates**: File overwrites and moving to Trash require typing `YES` locally; models cannot authorize their own destructive actions.

### 🎙️ Local Wake Word
Kronos can sit quietly until called. Turn on **⚙ → WAKE WORD** and the microphone is processed **locally on your machine**. Nothing leaves your computer until Kronos hears its wake cue.

### ⚡ Instant Acknowledgment & Speed
No more silent waiting while tools run. Kronos immediately acknowledges your command in natural speech before executing tasks like web searches, file processing, or coding.

---

## 🔄 Core Reliability & Architecture

### 🧠 Unlimited Recallable Memory
* **No silent drops**: Facts stay in `memory/long_term.json` on your machine.
* **Smart budgeting**: The prompt carries core identity and recent preferences; an on-demand local lookup (`recall_memory`) retrieves the rest in microseconds.
* **Key indexing**: Interleaved indexing ensures forgotten categories are never missed.

### ↩️ Verified Undo
Say **"undo"** in any language to reverse the previous action:
* **Files**: move · rename · create · copy · write · delete · organize desktop
* **Settings**: volume · brightness · dark mode

Undo never guesses: it records actual system state *before* mutations and only acts when state is recoverable.

### 🎧 Intelligent Audio Calibration
Kronos benchmarks and deduplicates audio endpoints across OS host APIs, ensuring clean input and output without silent drops or distortion.

---

## 🗺️ Kronos Roadmap

| Version | Focus |
|---|---|
| **Foundation** | Session memory · reactive HUD · self-describing skills · recallable memory · undo · audio device picker |
| **Kronos V1** | Cross-platform agent engine (`kronos`) · dynamic app discovery (macOS & Windows) · multi-provider LLM transport (Groq / NVIDIA / OpenRouter) · safe confirmed file operations · native launchers (`.command` / `.cmd`) · CI test suite |
| **Kronos V2** | Full proactive butler integration · learned user habits & anticipation · custom unified interface · multi-model task routing |

---

## ⚡ Quick Start

### 1. Clone the repository
```bash
git clone https://github.com/xsqlverx/KronosV1.git
cd KronosV1
```

### 2. Launch on macOS (Primary Target)
```bash
bash start-kronos.command
```
*Creates the virtual environment, verifies dependencies, and launches the configuration wizard.*

### 3. Launch on Windows (Secondary Target)
```cmd
start-kronos.cmd
```
*Or run directly in PowerShell:*
```powershell
python -m kronos --config config/kronos.example.json chat
```

### 4. Running the Full Voice HUD
```bash
python setup.py        # installs OS-specific dependencies & Playwright browsers
python main.py         # launches the reactive PyQt6 HUD
```

---

## 📋 Requirements

| Requirement | Details |
| --- | --- |
| **OS** | macOS (Apple Silicon or Intel), Windows 10/11, or Linux |
| **Python** | 3.11 or 3.12 |
| **Microphone** | Required for voice interaction and wake word |
| **Speakers** | Required for voice replies |
| **API Keys** | Any supported provider: Groq, NVIDIA NIM, OpenRouter, or Gemini Live |

---

## 🛠️ Diagnostics & Verification

Run the built-in diagnostic and test suite anytime:

```bash
# Non-destructive environment and OS capability check
python -m kronos doctor

# Inspect registered tool contracts and schemas
python -m kronos tools

# Run the 36-test cross-platform regression suite
python -m unittest discover -s tests -v

# Run system verification script
python scripts/verify_kronos.py
```

---

## 🗂️ Project Structure

```text
KronosV1/
├── kronos/                   # Core autonomous agent runtime
│   ├── __main__.py           # CLI, setup wizard, doctor diagnostics
│   ├── agent.py              # Bounded model/tool execution loop
│   ├── apps.py               # Dynamic OS app discovery & execution
│   ├── contracts.py          # Tool contracts, validation, & outcomes
│   ├── files.py              # Bounded file operations & confirmations
│   ├── providers.py          # Groq, NVIDIA NIM, & OpenRouter transport
│   ├── runtime.py            # Tool registration & execution environment
│   └── system.py             # OS platform adapters (macOS / Windows)
├── main.py                   # Real-time Gemini Live voice loop & dispatch
├── ui.py                     # PyQt6 reactive HUD & settings drawer
├── start-kronos.command      # macOS one-click launcher
├── start-kronos.cmd          # Windows one-click launcher
├── setup.py                  # Voice HUD installer (skips foreign OS packages)
├── requirements-kronos.txt   # Minimal agent dependencies
├── requirements.txt          # Voice HUD full dependencies
├── actions/                  # Modular tool skills (auto-discovered)
├── plugins/                  # User drop-in plugin directory
├── memory/                   # Long-term local memory & config
├── core/                     # Audio devices, undo, confirmation gates
├── tests/                    # Cross-platform regression test suite
├── docs/                     # Architectural specifications & guides
└── HANDOFF.md                # Development status & verified evidence
```

---

## ⚠️ License & Attribution

Personal and non-commercial use only. Licensed under **[Creative Commons BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/)**.

KRONOS builds upon modular foundations, audio streaming architecture, and utility patterns explored in [Mark-LIII](https://github.com/FatihMakes/Mark-LIII) by FatihMakes.
