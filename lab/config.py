from __future__ import annotations

import os

from .constant import CONFIG, DEFAULT_AGENT_PORT


def config_value(key: str, default: str = "") -> str:
    if not CONFIG.exists():
        return default
    prefix = f"export {key}="
    for line in CONFIG.read_text().splitlines():
        if line.startswith(prefix):
            value = line[len(prefix):].strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
                value = value[1:-1]
            return os.path.expandvars(value)
    return default


def agent_port() -> int:
    try:
        return int(config_value("AGENT_PORT", str(DEFAULT_AGENT_PORT)))
    except ValueError:
        return DEFAULT_AGENT_PORT


def read_env_lines() -> list[str]:
    return CONFIG.read_text().splitlines()


def env_value(lines: list[str], key: str) -> str:
    prefix = f"export {key}="
    for line in lines:
        if line.startswith(prefix):
            return line[len(prefix):]
    return ""


def replace_env_value(lines: list[str], key: str, value: str) -> list[str]:
    prefix = f"export {key}="
    replacement = f"export {key}={value}"
    changed = False
    next_lines = []
    for line in lines:
        if line.startswith(prefix):
            next_lines.append(replacement)
            changed = True
        else:
            next_lines.append(line)
    if not changed:
        next_lines.append(replacement)
    return next_lines

