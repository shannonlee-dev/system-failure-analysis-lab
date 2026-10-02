# 증거 디렉토리

원본 증거는 장애 시나리오별로 나누어 보관합니다. 리포트는 이 파일들을 근거로 삼아야 합니다.

| 디렉토리 | 목적 |
| --- | --- |
| `boot-failed/` | 시작 실패 출력 |
| `boot-ready/` | 정상 시작과 기본 모니터링 결과 |
| `cpu/` | CPU 제한 및 급상승 분석 증거 |
| `deadlock/` | 멀티스레드 데드락 비교 증거 |
| `oom/` | 메모리 제한 비교 증거 |
| `scheduling/` | 스케줄러 동작 증거 |

`uv run --frozen failure-lab start`로 생성되는 대화형 로그는 `evidence/interactive/`에 저장되며 git 추적 대상에서 제외됩니다.
