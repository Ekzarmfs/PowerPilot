# ⚡ PowerPilot

> **Intelligent Battery Optimization & Real-Time Telemetry Engine for Windows 11**

[![Live Presentation](https://img.shields.io/badge/Presentation-GitHub%20Pages-38bdf8?style=for-the-badge&logo=github)](https://Ekzarmfs.github.io/PowerPilot/)
[![Windows 11](https://img.shields.io/badge/Platform-Windows%2011%20x64-0078d4?style=for-the-badge&logo=windows11)](https://github.com/Ekzarmfs/PowerPilot)
[![Python](https://img.shields.io/badge/Python-3.11+-ffd343?style=for-the-badge&logo=python)](https://github.com/Ekzarmfs/PowerPilot)

---

## 🌐 Live Presentation & Interactive Simulator

Experience the interactive web demo and pitch deck directly in your browser:  
👉 **[https://Ekzarmfs.github.io/PowerPilot/](https://Ekzarmfs.github.io/PowerPilot/)**

---

## ✨ Key Features

- **⚡ Hardware Telemetry Arc:** Real-time circular battery gauge displaying instantaneous discharge wattage and accurate time-to-empty calculations.
- **🧹 One-Click Clean Sweep:** Terminates non-essential user background apps (Electron helpers, webview syncers) while strictly protecting Windows kernel services. Reclaims **~1.2 GB RAM** and extends runtime by **+48 minutes**.
- **💼 Power Loadout Profiles:** Instant system-wide switching between **Work Focus**, **Gaming Performance**, and **Maximum Endurance**.
- **🛠️ Background Energy Optimizer:** Identifies and throttles heavy background leeches (Windows Search Indexer, DiagTrack telemetry, Teams webviews).

---

## 🚀 Running PowerPilot Locally

### Prerequisites
- Windows 10 / 11 (64-bit)
- Python 3.10+

### Quick Start
```powershell
# Clone the repository
git clone https://github.com/Ekzarmfs/PowerPilot.git
cd PowerPilot

# Install dependencies
pip install -r requirements.txt

# Launch PowerPilot
python main.py
```

### Build Standalone Executable (.exe)
Double-click `build_exe.bat` to compile a single portable `dist/PowerPilot.exe` without requiring Python.

---

## 📄 License
MIT License &bull; Developed by [Ekzarmfs](https://github.com/Ekzarmfs)