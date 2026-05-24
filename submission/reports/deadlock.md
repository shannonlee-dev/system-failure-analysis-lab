# [Bug] 데드락 - 동시 작업자가 서로의 리소스를 무기한 대기함

## 1. Description (현상 설명)

데드락 케이스는 제공된 바이너리를 `MULTI_THREAD_ENABLE=true`로 실행해 재현했다. 에이전트는 정상적으로 부팅되고 PID는 유지됐지만, 두 작업자가 각각 하나의 리소스를 점유한 뒤 다른 리소스를 기다리면서 진행이 멈췄다.

비교 실행에서는 `MULTI_THREAD_ENABLE=false`를 사용했고, 정상 모니터링 경로가 선택되어 WAITING/BLOCKED 로그 없이 스케줄러 작업이 완료됐다.

## 2. Evidence & Logs (증거 자료)

원본 증거:

- `submission/evidence/deadlock/multi-true/stdout.log`
- `submission/evidence/deadlock/multi-true/agent_app.log`
- `submission/evidence/deadlock/multi-true/thread_samples.log`
- `submission/evidence/deadlock/multi-false/stdout.log`
- `submission/evidence/deadlock/multi-false/agent_app.log`
- `submission/evidence/deadlock/multi-false/thread_samples.log`

마지막 블로킹 로그:

```text
[Worker-Thread-1] Need resource [Socket_Pool_B] to finish job.
[Worker-Thread-2] Need resource [Shared_Memory_A] to write logs.
[Worker-Thread-1] WAITING for [Socket_Pool_B]... (Status: BLOCKED)
[Worker-Thread-2] WAITING for [Shared_Memory_A]... (Status: BLOCKED)
```

## 3. Root Cause Analysis (원인 분석)

로그는 순환 대기를 보여준다:

- 작업자 1이 `Shared_Memory_A`를 보유하고 `Socket_Pool_B`를 대기.
- 작업자 2가 `Socket_Pool_B`를 보유하고 `Shared_Memory_A`를 대기.

이는 데드락의 핵심 패턴(상호 배제, 점유-대기, 관찰된 흐름에서의 비선점, 순환 대기)을 충족한다. 작업자가 막혀 있었기 때문에 CPU와 메모리는 대부분 유휴 상태였다.

## 4. Workaround & Verification (조치 및 검증)

우회 방법:

- 동시 잠금 경로를 피하려면 `MULTI_THREAD_ENABLE=false`로 설정한다.
- 영구 해결을 위해 공유 리소스를 전역적으로 일관된 순서로 잠그거나 잠금 획득에 타임아웃/백오프를 적용한다.

이전 및 이후:

- `MULTI_THREAD_ENABLE=true`: WAITING/BLOCKED 로그가 발생했고 로그 크기 변화가 멈춤.
- `MULTI_THREAD_ENABLE=false`: 앱이 `Healthy System Monitoring`을 선택했고 WAITING/BLOCKED 로그 없이 스케줄러 작업이 완료됨.

검증 결과: PASS. true/false 비교로 재현 가능한 데드락과 명확한 회피 경로가 확인됐다.
