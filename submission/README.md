# 2026 Main 1-2 Submission

리소스 장애 분석 과제의 제출 산출물입니다. 분석 대상 애플리케이션 실행 결과, 관찰 로그, 스크린샷, 사고 보고서를 함께 보관합니다.

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
| `agent-app-leak/` | 분석 대상 실행 파일 |
| `evidence/oom/` | 메모리 제한 조건별 OOM 증거 로그 |
| `evidence/cpu/` | CPU 제한과 spike 관찰 로그 |
| `evidence/deadlock/` | 멀티스레드 조건별 deadlock 증거 로그 |
| `evidence/scheduling/` | 스케줄링 추론용 실행 로그 |
| `reports/` | GitHub Issue 형식의 분석 보고서 |
| `screenshots/` | 명령 실행과 상태 확인 이미지 |
| `tools/` | 샘플링 및 분석 보조 스크립트 |

## Run

```bash
cd 2026-main-1-2/submission
cat env-default.sh
./monitor.sh
```

## Reports

- `reports/oom.md`
- `reports/cpu.md`
- `reports/deadlock.md`
- `reports/scheduling.md`

## Notes

- 증거 수집은 실행 로그와 시스템 관찰을 기준으로 했으며, 디컴파일이나 리버스 엔지니어링은 수행하지 않았습니다.
- 증거 로그는 `tools/collect_real_evidence.sh`로 `agent-app-leak` 바이너리를 실제 실행해 다시 수집했습니다.
