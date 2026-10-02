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
| `evidence/cpu/spike/` | 보존한 과거 CPU 샘플, CSV, 그래프 |
| `.runtime/collections/run-*/` | 새 시나리오 증거와 실행 메타데이터 |
| `.runtime/cpu-samples/run-*/` | 새 CPU 샘플 로그 |
| `.runtime/cpu-analysis/` | 기본 CSV·그래프·분석 리포트 출력 |
| `reports/` | 최종 장애 분석 리포트 |
| `screenshots/` | 보조 캡처 이미지 |

## 메모

- `uv run --frozen failure-lab start`의 대화형 실행 로그는 `evidence/interactive/`에 저장됩니다.
- CPU 그래프는 `matplotlib`이 설치되어 있을 때만 생성됩니다.
- 리포트는 관찰된 사실과 추론을 구분해서 작성합니다.

`collect --output 새디렉토리`, `sample-cpu --output 새로그파일`로 출력 경로를 지정할 수 있습니다. 기존 디렉토리·파일에는 기록하지 않습니다. 새 수집 결과의 `exit-status.txt`는 앱 종료 코드, READY 확인, 모니터·프로세스 샘플 실패, 수집기가 종료했는지를 구분합니다. 수집기는 수집 실패가 있으면 비정상 종료하지만, OOM 같은 실험 대상 앱의 비정상 종료 자체는 별도 코드로 보존합니다. `run-metadata.txt`는 수집 시각·플랫폼·대상 바이너리 해시를 기록합니다. 과거 증거에는 이 기록이 없으므로 새 메타데이터를 소급해서 붙이지 않습니다.

모니터는 지정한 런처 PID의 자손 중 TCP 포트를 소유한 워커를 선택합니다. 런처 PID가 없을 때는 agent 프로세스인 포트 소유자만 허용합니다. 조회 권한이 부족하거나 해당 워커가 없으면 측정을 실패로 처리합니다.

`cpu-spike`는 기본적으로 기존 출력 파일을 거부합니다. 결과를 재생성할 때는 새 `--csv`, `--report`, `--plot` 경로를 지정하거나 기존 분석 출력 교체에 `--overwrite`를 사용합니다. 입력 로그와 출력 경로는 같을 수 없습니다.
