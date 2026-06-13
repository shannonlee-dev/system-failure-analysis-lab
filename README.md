# 시스템 장애 분석 랩

`agent-app-leak` 대상 앱의 장애를 재현하고 분석하는 프로젝트입니다. 메모리 압박, CPU 급상승, 데드락, 스케줄링 동작을 시나리오별로 수집하고, 원본 증거와 분석 리포트를 분리해 보관합니다.

## 디렉토리 구조

```text
.
├── main.py
├── lab/
├── config/
├── assets/
├── scripts/
├── tools/
├── evidence/
├── reports/
├── screenshots/
├── docs/
└── README.md
```

자세한 구조 규칙은 `docs/structure.md`를 참고하세요.

## 빠른 실행

```bash
python3 main.py
```

자주 쓰는 명령:

```bash
python3 main.py start
python3 main.py stop
python3 main.py edit-env
python3 main.py monitor
python3 main.py sample-cpu
python3 main.py collect
python3 main.py analyze-cpu
python3 main.py check
```

## 주요 경로

| 경로 | 설명 |
| --- | --- |
| `main.py` | 사용자용 CLI 진입점 |
| `lab/` | CLI 구현 코드 |
| `config/` | 기본 실행 환경 |
| `assets/` | 분석 대상 앱 바이너리와 압축 파일 |
| `scripts/` | 모니터링 및 증거 수집 스크립트 |
| `tools/` | 분석 보조 도구 |
| `evidence/` | 표준 출력, 표준 에러, 모니터 로그, 프로세스 로그 |
| `reports/` | 시나리오별 분석 리포트 |
| `screenshots/` | 터미널/명령 실행 캡처 |
| `docs/` | 구조와 사용법 문서 |

## 원칙

- 실행 진입점은 `main.py`로 고정합니다.
- 원본 증거는 `evidence/`에, 해석과 결론은 `reports/`에 둡니다.
- 각 리포트의 결론은 가능한 한 `evidence/`의 실제 파일을 근거로 연결합니다.
