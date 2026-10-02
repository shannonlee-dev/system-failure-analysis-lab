"""Print the actual worker PID without changing any processes."""

import argparse
import sys
from pathlib import Path

# The standalone shell monitor also works before installing the Python package.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from failure_lab.process import select_monitor_pid  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--launch-pid", type=int)
    args = parser.parse_args()
    pid = select_monitor_pid(args.port, args.launch_pid)
    if pid is None:
        return 1
    print(pid)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
