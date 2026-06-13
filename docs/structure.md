# 프로젝트 구조

이 저장소는 재현 가능한 시스템 장애 분석 랩으로 구성되어 있습니다.

```text
.
├── README.md
├── main.py
├── lab/
│   ├── app.py
│   ├── cli.py
│   ├── commands.py
│   ├── config.py
│   ├── constant.py
│   ├── process.py
│   ├── runner.py
│   └── ui.py
├── config/
├── assets/
├── scripts/
├── tools/
│   ├── cpu_spike_analyzer.py
│   └── cpu_spike/
├── evidence/
├── reports/
├── screenshots/
└── docs/
    ├── structure.md
    └── usage.md
```

## 경계

| 경로 | 역할 |
| --- | --- |
| `README.md` | 프로젝트 개요와 빠른 실행 안내 |
| `main.py` | 안정적인 사용자 CLI 진입점 |
| `lab/constant.py` | 프로젝트 경로와 공통 상수 |
| `lab/` | 앱 실행, 환경 편집, 프로세스 관리, CLI 메뉴 구현 |
| `config/` | 기본 실행 환경 |
| `assets/` | 대상 앱 바이너리와 압축 파일 |
| `scripts/` | 시나리오 실행 및 모니터링 스크립트 |
| `tools/` | 분석 도구와 실행 wrapper |
| `tools/cpu_spike/` | CPU 급상승 분석기의 세부 모듈 |
| `evidence/` | 시나리오별 원본 증거 |
| `reports/` | 사람이 읽는 분석 리포트 |
| `screenshots/` | 시각 자료 |
| `docs/` | 유지보수용 문서 |

## 규칙

- 사용자 명령은 `main.py`를 통해 실행합니다.
- 경로와 환경 키는 `lab/constant.py`에서 관리합니다.
- 쉘 기반 워크플로는 `scripts/`에 둡니다.
- 파이썬 분석 로직은 기능별 패키지로 나누고, 기존 실행 파일은 wrapper로 유지합니다.
- 원본 증거와 분석 리포트는 섞지 않습니다.
- 생성 캐시는 `.gitignore`에 추가하고 커밋하지 않습니다.
