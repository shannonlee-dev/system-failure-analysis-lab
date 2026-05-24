# [Bug] OOM 크래시 - 힙 증가가 MEMORY_LIMIT에 도달하면 MemoryGuard가 에이전트를 종료함

## 1. Description (현상 설명)

`agent-app-leak`는 non-root 사용자로 실행했고, 필요한 `AGENT_HOME`, 키 파일, 로그 디렉터리, 고정 포트 `15034`를 제공했다. OOM 케이스에서는 프로세스가 정상적으로 시작한 뒤 메모리 워커가 힙 사용량을 증가시켜 구성된 `MEMORY_LIMIT`에 도달했다.

두 번의 실행을 비교했다:

- 이전: `MEMORY_LIMIT=50`
- 이후: `MEMORY_LIMIT=128`

`128` MB 실행은 MemoryGuard가 종료하기 전까지 더 오래 살아남았고 더 많은 모니터 샘플을 남겼다.

## 2. Evidence & Logs (증거 자료)

원본 증거:

- `submission/evidence/oom/memory-50/stdout.log`
- `submission/evidence/oom/memory-50/agent_app.log`
- `submission/evidence/oom/memory-128/stdout.log`
- `submission/evidence/oom/memory-128/agent_app.log`

MemoryWorker 로그에서 힙 증가가 확인됐다:

```text
memory-50:
2026-05-19 13:42:04,677 [INFO] [MemoryWorker] Current Heap: 25MB
2026-05-19 13:42:07,690 [INFO] [MemoryWorker] Current Heap: 50MB

memory-128:
2026-05-19 13:42:10,590 [INFO] [MemoryWorker] Current Heap: 25MB
2026-05-19 13:42:25,753 [INFO] [MemoryWorker] Current Heap: 150MB
```

MemoryGuard 종료 로그:

```text
MEMORY_LIMIT=50:
[MemoryGuard] Memory limit exceeded (50MB >= 50MB)
[MemoryGuard] Self-terminating process 12052 to prevent system instability.

MEMORY_LIMIT=128:
[MemoryGuard] Memory limit exceeded (150MB >= 128MB)
[MemoryGuard] Self-terminating process 12222 to prevent system instability.
```

## 3. Root Cause Analysis (원인 분석)

에이전트는 시간 경과에 따라 힙 메모리를 할당한다. `50` MB 실행에서는 RSS가 약 `20.8MB`에서 `45.8MB`까지 증가했고, `128` MB 실행에서는 종료 전에 `95.8MB`까지 증가했다. 프로세스는 부팅에서 실패하지 않았고, 힙이 설정된 한계를 넘은 뒤 애플리케이션 수준 MemoryGuard에 의해 종료됐다.

시스템 수준의 위험은 무제한 힙 증가가 물리 메모리를 압박해 결국 다른 프로세스에 영향을 줄 수 있다는 점이다. MemoryGuard는 구성된 한계를 넘으면 에이전트를 종료해 더 넓은 불안정을 방지한다.

## 4. Workaround & Verification (조치 및 검증)

우회 방법:

- `MEMORY_LIMIT` 증가는 임시 완화로만 사용한다.
- 한계를 올려도 누수 패턴은 제거되지 않으므로 RSS 증가 모니터링을 계속한다.

이전 및 이후:

- `MEMORY_LIMIT=50`: 모니터 샘플 3개, MemoryGuard가 `50MB >= 50MB`에서 종료.
- `MEMORY_LIMIT=128`: 모니터 샘플 7개, MemoryGuard가 `150MB >= 128MB`에서 종료.

검증 결과: PASS. 더 높은 한계가 종료를 지연시켜 더 많은 힙 증가를 관측했지만, 동일한 MemoryGuard 정책이 프로세스를 여전히 중지시켰다.
