from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

CONFIG = ROOT / "config" / "env-default.sh"
MONITOR = ROOT / "scripts" / "monitor.sh"
COLLECT = ROOT / "scripts" / "collect_real_evidence.sh"
CPU_ANALYZER = ROOT / "tools" / "cpu_spike_analyzer.py"
CPU_SAMPLER = ROOT / "tools" / "monitor_cpu_sampling.sh"

ASSET_DIR = ROOT / "assets" / "agent-app-leak"
APP = ASSET_DIR / "agent-app-leak"
APP_ZIP = ASSET_DIR / "agent-app-leak.zip"

INTERACTIVE_LOG_DIR = ROOT / "evidence" / "interactive"
DEFAULT_AGENT_PORT = 15034

ENV_KEYS = (
    "AGENT_HOME",
    "AGENT_PORT",
    "AGENT_UPLOAD_DIR",
    "AGENT_KEY_PATH",
    "AGENT_LOG_DIR",
    "MEMORY_LIMIT",
    "CPU_MAX_OCCUPY",
    "MULTI_THREAD_ENABLE",
)

