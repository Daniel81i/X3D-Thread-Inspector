# AMD Ryzen X3D - Dual-CCD & Thread Inspector

🌐 **[English](README.md)** | **[日本語](README.ja.md)**

---

A real-time processor and thread diagnostics tool tailored for dual-CCD AMD processors such as the **AMD Ryzen 9 7950X3D / 9950X3D** (**CCD0: 3D V-Cache** vs **CCD1: Frequency**).

Designed specifically for heavy multitasking environments (like VRChat, SteamVR, and modern games), this tool lets you verify whether **latency-sensitive rendering and physics workloads are safely hosted on 3D V-Cache (CCD0)** while **background tasks, audio, and network threads are offloaded to the high-frequency cores (CCD1)** to preserve critical headroom against stutter.

---

## Key Features

* **100% Anti-Cheat Safe (Zero-Risk)**
  * Fully safe to run alongside games protected by Easy Anti-Cheat (EAC), BattlEye, Vanguard, etc.
  * No memory injection, hooking, or intrusive DLL scans. Strictly queries safe, non-invasive Windows API performance metrics.
* **High-Accuracy Thread Role Estimation**
  * Accurately pinpoints the process's initial **`Main/GameLoop`** thread (Primary Thread: 100% certainty).
  * Automatically classifies active threads (`Render/Gfx`, `Physics/IK`, `Audio/Network`, `Worker`) based on real-time CPU cycle consumption ranks.
* **Dual-CCD Parallel Inspector (CCD0 Top 5 vs CCD1 Top 5)**
  * Side-by-side inspection of the top 5 heaviest threads on each CCD.
  * Instant visual indicators (**`⮀` orange icon**) whenever a thread migrates between logical cores.
* **🖥️ System Total CPU & Per-CCD System Usage Live Gauges**
  * Displays overall PC-wide CPU utilization alongside individual CCD0 (V-Cache) and CCD1 (Freq) total loads in real time, letting you easily correlate the target game's distribution with full system activity.
* **Dynamic Auto-Resizing & Collapsible UI**
  * Click the collapse button to automatically shrink the window height down to a compact **250px HUD**.
  * Expand anytime into a full **560px detailed diagnostic dashboard**.
* **⚡ Live Power Plan Badge & Warnings**
  * Displays active Windows power plan (e.g. `Balanced`). Instantly alerts you if switched to `High Performance` which inadvertently disables core parking on dual-CCD Ryzen processors.
* **📌 Always on Top Toggle**
  * Easily toggle always-on-top mode on or off to send the window behind other applications when needed.

---

## Preview

### 1. Expanded Diagnostic Mode (Full Dashboard)

![Expanded Diagnostic Mode](assets/screenshot_full.png)

> **Real-World Inspection (VRChat under heavy load)**:
> Core gaming workloads (`Main/GameLoop`, `Render/Gfx`, and `Physics/IK`) are cleanly packed into the 3D V-Cache on **CCD0**, while background tasks (`Audio/Network`, worker threads) are offloaded onto high-frequency **CCD1**.

<details>
<summary>View ASCII Text UI Diagram</summary>

```text
┌──────────────────────────────────────────────────────────────────────────┐
│ AMD Ryzen 9 X3D - Dual-CCD & Thread Inspector                     — □ ✕ │
├──────────────────────────────────────────────────────────────────────────┤
│ Target: [ vrchat.exe   ] [ Set ]  [PWR: Balanced (Rec)]     [x] Always on Top│
│ ● Target: vrchat.exe  |  PID: 18420  |  Threads: 68  |  [Affinity: All Cores]│
├──────────────────────────────────────────────────────────────────────────┤
│ 🖥️ System Total CPU: 24.5%          [CCD0: 38.2%  |  CCD1: 10.8%]       │
│ [██████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░]│
│ ⚡ Target CCD0 (V-Cache): 61.2% [38th]      🚀 Target CCD1 (Freq): 38.8% [30th]│
│ [██████████████████████░░░░░░]             [██████████████░░░░░░░░░░░░░░]│
│ Logical Core Allocation (0-15: CCD0 V-Cache | 16-31: CCD1 Freq)          │
│ ■■■■■■■■ ■■■■■■■■   ■■■■■■□□ □□□□□□□□                                    │
├──────────────────────────────────────────────────────────────────────────┤
│ [▼ Collapse Thread Details (CCD0 Top 5 vs CCD1 Top 5)]                   │
├────────────────────────────────────┬─────────────────────────────────────┤
│ ⚡ CCD0 (3D V-Cache) Top 5 Threads │ 🚀 CCD1 (Frequency) Top 5 Threads   │
│                                    │                                     │
│ #1 C02  Main/GameLoop   20.9%      │ #1 C16  Audio/Network  3.3%         │
│ #2 C10  Render/Gfx       4.3%      │ #2 C18  Audio/Network  3.1%         │
│ #3 C12  Physics/IK       4.0%      │ #3 C31  Worker         3.1%         │
│ #4 C14  Physics/Job      3.6%      │ #4 C20  Worker         3.0%         │
│ #5 C01  Worker           2.2%      │ #5 C22  Worker         2.8%         │
└────────────────────────────────────┴─────────────────────────────────────┘
```
</details>

### 2. Compact HUD Mode (Collapsed)

![Compact HUD Mode](assets/screenshot_collapsed.png)

<details>
<summary>View ASCII Text UI Diagram</summary>

```text
┌──────────────────────────────────────────────────────────────────────────┐
│ AMD Ryzen 9 X3D - Dual-CCD & Thread Inspector                     — □ ✕ │
├──────────────────────────────────────────────────────────────────────────┤
│ Target Process: [ vrchat.exe          ] [ Set / Refresh ]  [ ] Always on Top │
│ ● Target: vrchat.exe  |  PID: 23300  |  Threads: 373 |  [Affinity: All Cores]│
├──────────────────────────────────────────────────────────────────────────┤
│ System Total CPU: 15.0%                    [CCD0: 22.1%  |  CCD1: 7.9%] │
│ ⚡ CCD0 (3D V-Cache): 58.4%  [194 th]       🚀 CCD1 (Frequency): 41.6% [179 th]│
│ [██████████████████████░░░░░░]             [██████████████░░░░░░░░░░░░░░]│
│ Logical Core Activity (0-15: CCD0 V-Cache | 16-31: CCD1 Freq)             │
│ ■■■■■■■■ ■■■■■■■■   ■■■■■■■■ ■■■■■■■■                                    │
├──────────────────────────────────────────────────────────────────────────┤
│ [▶ Expand Thread Details (CCD0 Top 5 vs CCD1 Top 5)]                     │
└──────────────────────────────────────────────────────────────────────────┘
```
</details>

---

## How to Run

### A. Run directly with Python
Requires Python 3.10 or newer (Standard library only; no pip dependencies required to run):
```bash
python ccd_monitor.py
# Or double-click start_monitor.bat
```

### B. Build Standalone EXE Locally (PyInstaller)
```bash
pip install pyinstaller
pyinstaller --noconsole --onefile --clean --name "X3D-Thread-Inspector" ccd_monitor.py
```
Outputs standalone executable to `dist/X3D-Thread-Inspector.exe`.

---

## Automated CI/CD (GitHub Actions)

This repository includes a ready-to-use GitHub Actions workflow (`.github/workflows/build.yml`):

* **Every push to `main`**: Automatically builds on a clean Windows runner, tags a new version (`v0.0.1` → `v0.0.2`...), and publishes a GitHub Release with standalone `.exe` and `.zip` packages.
* **Manual trigger**: You can trigger a release with `patch`, `minor`, or `major` version bumps directly from the GitHub Actions tab.

---

## License
MIT License
