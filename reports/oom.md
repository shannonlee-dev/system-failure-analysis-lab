# [장애] 메모리 한계 도달 - MemoryGuard 보호 종료 로그

## 1. 관찰 범위

2026-06-13에 남긴 과거 실행 로그를 현재 저장소의 원본과 대조했다. 새 장애 실험을 실행한 결과가 아니다. `MEMORY_LIMIT=50`과 `128` 모두 정상 기동 뒤 MemoryWorker의 힙 증가와 MemoryGuard 종료 메시지가 남아 있다. 커널 OOM killer가 종료했다는 증거는 없으며, 앱 수준의 한계 도달 기록이다.

## 2. 원본 증거

- [50MB 앱 로그](../evidence/oom/memory-50/agent_app.log), [표준 출력](../evidence/oom/memory-50/stdout.log)
- [128MB 앱 로그](../evidence/oom/memory-128/agent_app.log), [표준 출력](../evidence/oom/memory-128/stdout.log)

현재 원본의 MemoryWorker 기록:

```text
memory-50:
2026-06-13 17:18:44,189 [INFO] [MemoryWorker] Current Heap: 25MB
2026-06-13 17:18:47,223 [INFO] [MemoryWorker] Current Heap: 50MB

memory-128:
2026-06-13 17:18:49,734 [INFO] [MemoryWorker] Current Heap: 25MB
2026-06-13 17:19:04,879 [INFO] [MemoryWorker] Current Heap: 150MB
```

종료 메시지:

```text
MEMORY_LIMIT=50:
[MemoryGuard] Memory limit exceeded (50MB >= 50MB) / (Recommend Over 256MB)
[MemoryGuard] Self-terminating process 16200 to prevent system instability.

MEMORY_LIMIT=128:
[MemoryGuard] Memory limit exceeded (150MB >= 128MB) / (Recommend Over 256MB)
[MemoryGuard] Self-terminating process 16458 to prevent system instability.
```

## 3. 측정 한계

두 실행 모두 모니터 샘플 2개만 남아 있다. [50MB 모니터 출력](../evidence/oom/memory-50/monitor.stdout)과 [128MB 모니터 출력](../evidence/oom/memory-128/monitor.stdout)은 RSS 1.9MB를 기록하고 세 번째 확인에서 TCP 연결 실패로 끝난다. 모니터 PID는 각각 16197·16455로, 앱이 종료 대상으로 기록한 워커 PID 16200·16458과 다르다. 이 자료는 워커의 RSS 증가를 입증하지 못한다. 두 `ps_top.log`도 비어 있고 실제 프로세스 종료 코드는 보존되어 있지 않다.

힙 값은 앱 자체 로그의 수치다. 128MB 구성은 25MB에서 150MB까지 약 15.15초, 50MB 구성은 25MB에서 50MB까지 약 3.03초의 기록을 남겼다. 더 높은 한계에서 더 많은 힙 증가 단계가 관찰되지만, 이를 RSS 측정 또는 커널 수준 메모리 압박 검증으로 해석하지 않는다.

## 4. 조치와 검증 상태

`MEMORY_LIMIT` 증가는 한계 도달을 지연시키는 임시 완화로 해석한다. 할당 증가 패턴을 제거하는 수정은 대상 바이너리의 소스가 없어 검증하지 않았다.

현재 수집기는 포트를 소유한 실제 워커를 선택하고 앱 종료 코드와 수집 실패를 별도 기록한다. 이 변경은 격리된 회귀 테스트로 확인했으며 실제 장애 시나리오는 재실행하지 않았다. 과거 로그에서 확인한 것은 힙 한계 도달과 보호 종료 메시지까지다. RSS 증가·새 수집기의 실호스트 측정·실제 종료 코드 검증은 아직 수행하지 않았다.
