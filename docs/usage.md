# 사용법

이 프로젝트는 하나의 CLI로 대상 앱 실행, 모니터링, 증거 수집, CPU 분석, 문법 검사를 수행합니다.

## 실행

대화형 메뉴:

```bash
uv run --frozen failure-lab
```

스크립트형 명령:

```bash
uv run --frozen failure-lab start
uv run --frozen failure-lab stop
uv run --frozen failure-lab edit-env
uv run --frozen failure-lab monitor
uv run --frozen failure-lab sample-cpu
uv run --frozen failure-lab collect
uv run --frozen failure-lab analyze-cpu
uv run --frozen failure-lab check
```

## 주요 명령

| 명령 | 설명 |
| --- | --- |
| `start` | `config/env-default.sh`를 읽어 대상 앱을 실행합니다. |
| `stop` | 대상 앱과 포트 리스너를 정리합니다. |
| `edit-env` | 기본 환경 변수를 대화형으로 수정합니다. |
| `monitor` | 현재 실행 중인 앱을 대상으로 `scripts/monitor.sh`를 실행합니다. |
| `sample-cpu` | 짧은 간격으로 CPU 사용률을 샘플링합니다. |
| `collect` | 시나리오별 증거를 다시 수집합니다. |
| `analyze-cpu` | CPU 샘플 로그에서 급상승 구간을 분석합니다. |
| `check` | 쉘 스크립트와 파이썬 파일 문법을 검사합니다. |

## 산출물

| 경로 | 설명 |
| --- | --- |
| `evidence/` | 실행 결과와 모니터링 로그 |
| `evidence/cpu/spike/` | CPU 샘플, CSV, 그래프, 분석 리포트 |
| `reports/` | 최종 장애 분석 리포트 |
| `screenshots/` | 보조 캡처 이미지 |

## 메모

- `uv run --frozen failure-lab start`의 대화형 실행 로그는 `evidence/interactive/`에 저장됩니다.
- CPU 그래프는 `matplotlib`이 설치되어 있을 때만 생성됩니다.
- 리포트는 관찰된 사실과 추론을 구분해서 작성합니다.
