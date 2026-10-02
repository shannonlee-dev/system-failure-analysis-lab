# 프로젝트 구조

```text
system-failure-analysis-lab/
├── src/failure_lab/
│   ├── __main__.py          # 모듈 실행 진입점
│   ├── cli.py               # 인자 파싱과 명령 분기
│   ├── menu.py              # 대화형 메뉴와 종료 정리
│   ├── operations.py        # 환경 편집·수집·분석 명령
│   ├── app.py               # 실험 앱 실행·종료
│   ├── process.py           # 프로세스·포트 조회
│   ├── config.py            # 실험 환경 파일 처리
│   └── cpu_spike/           # 파싱·계산·CSV·보고서·그래프
├── tests/                   # 분석 회귀 테스트와 임시 경로 실행 검사
├── scripts/                 # 수집·샘플링·문법 검사 도구
├── config/                  # 실험 환경 예시
├── assets/                  # 기존 실험 바이너리와 압축 파일
├── evidence/                # 보존한 실험 로그
├── reports/                 # 원인 분석 보고서
├── docs/                    # 구조·사용법
├── .github/                 # 검증·이슈·의존성 갱신 설정
├── pyproject.toml           # 패키지와 명령·개발 도구
├── uv.lock                  # 설치 버전 잠금
└── Makefile                 # 설치·검증·테스트·빌드·실행
```

`uv run --frozen failure-lab`은 실험 실행을, `uv run --frozen cpu-spike`는 저장된 로그 분석을 시작합니다. CPU 분석은 입력·출력 경로를 지정해 기존 증빙과 분리합니다.

운영 자산은 Python 소스와 구분합니다. 실험 명령은 저장소의 `config/`, `scripts/`, `assets/`를 사용하며 Linux 실습 환경이 필요합니다. 앱 실행 없이 수행하는 `make smoke`는 기존 CPU 로그를 임시 디렉토리로 분석합니다.
