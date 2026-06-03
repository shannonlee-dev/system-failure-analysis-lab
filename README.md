# System Failure Analysis Lab

Resource failure analysis project for an `agent-app-leak` binary. The project collects runtime evidence for memory pressure, CPU spikes, deadlock behavior, and scheduling order, then summarizes the findings in reproducible reports.

The emphasis is on disciplined observation: run the scenario, collect logs, compare expected and observed behavior, and document the reasoning. That makes the repository useful as a small reliability-analysis lab rather than a loose set of screenshots.

## Scope

- OOM and memory-limit behavior
- CPU saturation scenarios
- Deadlock observation
- Scheduling-order analysis
- stdout, stderr, process, and application log collection
- Evidence-based written reports

## Repository Layout

```text
.
├── 98_PROCEDURE_MANUAL.md
├── README.md
└── submission/
    ├── agent-app-leak/
    ├── evidence/
    ├── reports/
    ├── screenshots/
    └── tools/
```

## Evidence Model

| Path | Purpose |
| --- | --- |
| `submission/reports/` | Scenario analysis reports |
| `submission/evidence/` | Captured stdout, stderr, monitor logs, and process logs |
| `submission/screenshots/` | Visual command/session evidence |
| `submission/tools/` | Evidence collection and sampling helpers |
| `submission/agent-app-leak/` | Target binary used for analysis |

## Run

```bash
cd submission
cat env-default.sh
./monitor.sh
```

To recollect evidence from the current binary:

```bash
cd submission
./tools/collect_real_evidence.sh
```

## Analysis Notes

- Reports are written from observed logs rather than assumed behavior.
- Scheduling analysis distinguishes direct evidence from inference.
- Scenario outputs are stored separately so results can be compared without rerunning every case.
- The structure favors traceability: each conclusion should point back to a file in `submission/evidence`.
