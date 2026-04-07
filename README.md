# GridMarkets Houdini Render Automator

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Houdini](https://img.shields.io/badge/Houdini-20.0+-orange)
![GridMarkets](https://img.shields.io/badge/GridMarkets-API-green)

> **Note:** This repository is a technical case study and portfolio showcase. The full source code is integrated into a proprietary production pipeline and is under NDA. The documentation and code snippets provided here demonstrate the logic, pipeline architecture, and integration with GridMarkets and Houdini (`hython`). 

## Overview
A standalone Python CLI tool that completely automates submitting Houdini Karma renders and compositing jobs (via COP) to the GridMarkets cloud render farm directly from Google Drive. 

Instead of manually opening Houdini, saving files locally, setting up render nodes, logging into GridMarkets, tracking dependencies, and manually converting EXR sequences, this tool does it all with a single shell command—running entirely headless.

---

## 🚀 The Core Achievement: Headless Graph Parsing

The most powerful aspect of this pipeline is how it reads the Houdini `.hip` file without ever opening a graphical interface. 

Using **`hython`** (Houdini's headless Python engine), the tool dynamically maps the node graph and orchestrates a perfect cloud-rendering dependency chain:

1. **Auto-Scanning:** It scans the `/out` network to find all user-defined `OUT_*` targets (e.g., `OUT_horizontal`, `OUT_vertical`).
2. **Dependency Resolution:** It traces back the node connections to discover exactly which render passes (`RND_`) need to finish before a compositing pass (`COMP_`) can begin.
3. **Smart Queuing:** It submits the separated jobs to the GridMarkets Cloud GPU Farm. Compositing jobs are queued safely behind their render dependencies.
4. **Auto-Delivery & Post-Processing:** As soon as completing frames hit the synced Google Drive, rigorous asynchronous polling detects them and uses `FFmpeg` to auto-convert the raw heavy formats into final, delivery-ready `.mp4` and ProRes sequence videos.

### Pipeline Flow

```mermaid
graph TD
    subgraph 1. Headless Parsing (hython)
    A[Terminal CLI<br/>'gridmarkets target'] --> B(Scan /out for OUT_ nodes)
    B --> C[Resolve Dependencies<br>Separate RND from COMP nodes]
    end
    
    subgraph 2. GridMarkets Orchestration
    C -->|API Submit via Envoy| D{Cloud GPU Farm}
    D -->|Parallel Renders| E[RND: Karma beauty, wipes, passes]
    E -->|On Success Trigger| F[COMP: Apply Alpha & Overlays]
    end
    
    subgraph 3. Delivery
    F -->|WatchFile Daemon| G[Auto-Download to Google Drive]
    G --> H[FFmpeg: Auto-Convert EXR/PNG to MP4/ProRes]
    end
```

## How It Works (Usage)

The tool operates via a simple CLI which artists can run from anywhere without launching Houdini.

```bash
# 1. Shows all available HIP file versions on the synced drive
$ gridmarkets list-hip
Found: logo.v20.hiplc

# 2. Render all setups or pick specific targets (Vertical/Horizontal)
$ gridmarkets render -t OUT_horizontal -t OUT_vertical

# 3. The CLI handles Envoy authentication, packs HDAs, and submits to the farm
[GridMarkets] Connected to Envoy API
[Houdini Parse] Found OUT_horizontal.
[Houdini Parse] Dependencies: 'beauty_YT', 'wipe_A_YT' -> 'COMP_alpha_YT'
[GridMarkets] Submitting 3 Render Jobs and 1 Composite Job...
[GridMarkets] Job abc123_456 submitted!

# 4. Jobs are monitored async
$ gridmarkets status
beauty_YT: RUNNING (45%)
wipe_A_YT: COMPLETED (100%)
COMP_alpha_YT: PENDING (waiting on dependencies)
```
## 💻 CLI Commands & Usage

This tool provides artists with a unified, terminal-based interface to manage everything from checking dependencies to batch rendering multiple setups simultaneously.

### Available Commands

| Command | Description |
| :--- | :--- |
| `gridmarkets info` | Connects to Houdini and shows all discovered targets and dependencies. |
| `gridmarkets list` | Lists all available HIP file versions found on the shared drive. |
| `gridmarkets render` | Scans the node graph and submits **all** discovered targets to the farm. |
| `gridmarkets render -t OUT_x` | Renders only a specific node target (e.g., `OUT_horizontal`). |
| `gridmarkets convert` | Manually triggers the FFmpeg conversion of existing comp sequences. |

### Render Configuration Options

When running a render submission, multiple flags are available to control versions, frames, and cloud hardware options dynamically.

| Option | Short Format | Default Value | Description |
| :--- | :---: | :---: | :--- |
| `--name` | `-n` | `logo` | The base name of the HIP file to look for. |
| `--version` | `-v` | `latest` | Explicitly define a HIP file version number. |
| `--target` | `-t` | `all` | Specific `OUT_*` target node (can specify multiple). |
| `--frames` | `-f` | `from scene` | Override the frame range (format: `"start end step"`). |
| `--instances` | `-i` | `5` | Set the max number of parallel render instances per job. |
| `--gpu` | *none* | `enabled` | Execute cloud rendering on GPU hardware (Karma XPU). |
| `--cpu` | *none* | *none* | Force cloud rendering to standard CPU nodes. |
| `--fps` | *none* | `24` | The output target FPS for the final MP4/ProRes conversion. |

---

## Code Snippets

While the full API integration is restricted, you can find a few core components in the `code_snippets` directory that demonstrate the engineering approach behind this tool:

* **`hython_node_scanner.py`**: An extraction of the node scanning logic, demonstrating how to use `hou` in Python to dynamically traverse the node tree and build a dependency list based on input connections.
* **`config.toml.example`**: Demonstrates the data-driven configuration schema handling environment variables, paths, and API integrations.

---
*Created by [Your Name] for Portfolio Demonstration.*
