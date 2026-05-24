# 2026 Main 1-2

2026 메인 1-2 과제 산출물입니다. 제공된 `agent-app-leak` 애플리케이션을 실제 실행해 OOM, CPU spike, deadlock, scheduling 동작을 관찰하고 증거와 보고서를 정리했습니다.

## 참고 사항

증거 로그는 현재 저장된 `submission/agent-app-leak/agent-app-leak` 바이너리를 실행해 다시 수집했습니다. 스케줄링 로그 역시 실제 앱의 정상 모니터링 경로에서 나온 FCFS 형태의 작업 완료 순서를 기준으로 갱신했습니다.

## Structure

```text
2026-main-1-2/
├── 98_PROCEDURE_MANUAL.md
├── README.md
└── submission/
    ├── agent-app-leak/
    ├── evidence/
    ├── reports/
    ├── screenshots/
    └── tools/
```

## Contents

| Path | Summary |
| --- | --- |
| `submission/reports/` | CPU, OOM, deadlock, scheduling 분석 보고서 |
| `submission/evidence/` | 실험별 stdout, stderr, monitor, process 로그 |
| `submission/screenshots/` | 명령 실행 및 상태 확인 스크린샷 |
| `submission/tools/` | CPU spike 분석과 샘플링 보조 도구 |
| `submission/agent-app-leak/` | 제공 또는 확보된 분석 대상 바이너리 |

## Run

기본 환경값을 확인한 뒤 모니터링 스크립트를 실행합니다.

```bash
cd 2026-main-1-2/submission
cat env-default.sh
./monitor.sh
```

## Notes

- 기존 `mission1_2/` 래퍼 폴더는 제거하고 과제 루트에서 바로 README와 제출물을 확인할 수 있게 정리했습니다.
- `submission/tools/collect_real_evidence.sh`를 사용하면 현재 바이너리 기준 증거 로그를 다시 수집할 수 있습니다.
