# Failure Analysis Submission

This directory contains the executable target, collected evidence, screenshots, tools, and scenario reports for the system failure analysis lab.

## Structure

```text
submission/
├── agent-app-leak/
├── evidence/
├── reports/
├── screenshots/
├── tools/
├── env-default.sh
└── monitor.sh
```

## Contents

| Path | Summary |
| --- | --- |
| `reports/` | CPU, memory, deadlock, and scheduling analysis |
| `evidence/` | Scenario logs and process output |
| `screenshots/` | Supporting terminal/session captures |
| `tools/` | Evidence collection and sampling scripts |
| `agent-app-leak/` | Analysis target binary |

## Run

```bash
cat env-default.sh
./monitor.sh
```

## Recollect Evidence

```bash
./tools/collect_real_evidence.sh
```

## Notes

- Evidence is organized by scenario so each report can be checked against raw output.
- Logs are intentionally kept with the submission to preserve the reasoning trail.
- Reports should distinguish observed behavior from inferred causes.
