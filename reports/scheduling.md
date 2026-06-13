# [분석] 스케줄링 추론 - 실제 앱 로그 기준 Round-Robin 실행 패턴

## 1. 로그 관찰 개요

정상 모니터링 경로에서 `Thread-A`, `Thread-B`, `Thread-C`가 등록되었고, 실제 실행 로그에서는 세 작업이 한 번에 끝까지 실행되지 않았다. 각 작업은 `40%`, `80%` 지점에서 `Preempted` 상태로 저장된 뒤, 다음 순서에서 `Resumed` 되어 이어서 실행됐다.

등록 및 실행은 다음 순서로 관찰됐다.

```text
Thread-A -> Thread-B -> Thread-C
Thread-A -> Thread-B -> Thread-C
Thread-A -> Thread-B -> Thread-C
```

이는 작업마다 일정 실행 구간을 부여하고, 완료되지 않은 작업은 다음 라운드에서 다시 실행하는 방식이다. 따라서 현재 로그는 **선점형 Round-Robin 스케줄링**으로 해석하는 것이 가장 타당하다.

## 2. 증거 자료

원본 증거:

- `evidence/scheduling/round-robin/stdout.log`
- `evidence/scheduling/round-robin/agent_app.log`
- `evidence/scheduling/round-robin/stderr.log`

환경 및 등록 로그:

```text
MEMORY_LIMIT=512MB, CPU_MAX_OCCUPY=10%, MULTI_THREAD_ENABLE=False
[Scheduler] Registered Tasks: ['Thread-A', 'Thread-B', 'Thread-C']
```

스케줄링 로그 발췌:

```text
2026-06-13 17:18:35,933 [INFO] [Thread-A] Task Started. Calculating... (20%)
2026-06-13 17:18:36,036 [INFO] [Thread-A] Preempted. Progress saved at (40%)
2026-06-13 17:18:36,087 [INFO] [Thread-B] Task Started. Calculating... (20%)
2026-06-13 17:18:36,190 [INFO] [Thread-B] Preempted. Progress saved at (40%)
2026-06-13 17:18:36,241 [INFO] [Thread-C] Task Started. Calculating... (20%)
2026-06-13 17:18:36,342 [INFO] [Thread-C] Preempted. Progress saved at (40%)
2026-06-13 17:18:36,393 [INFO] [Thread-A] Resumed. Calculating... (60%)
2026-06-13 17:18:36,496 [INFO] [Thread-A] Preempted. Progress saved at (80%)
2026-06-13 17:18:36,547 [INFO] [Thread-B] Resumed. Calculating... (60%)
2026-06-13 17:18:36,649 [INFO] [Thread-B] Preempted. Progress saved at (80%)
2026-06-13 17:18:36,699 [INFO] [Thread-C] Resumed. Calculating... (60%)
2026-06-13 17:18:36,801 [INFO] [Thread-C] Preempted. Progress saved at (80%)
2026-06-13 17:18:36,852 [INFO] [Thread-A] Resumed. Calculating... (100%)
2026-06-13 17:18:36,902 [INFO] [Thread-B] Resumed. Calculating... (100%)
2026-06-13 17:18:36,953 [INFO] [Thread-C] Resumed. Calculating... (100%)
2026-06-13 17:18:37,004 [INFO] [Scheduler] All tasks completed.
```

## 3. 패턴 분석 및 결론

관찰된 핵심 패턴은 다음과 같다.

```text
1라운드: A 20% -> 40%, preempt
1라운드: B 20% -> 40%, preempt
1라운드: C 20% -> 40%, preempt

2라운드: A 60% -> 80%, preempt
2라운드: B 60% -> 80%, preempt
2라운드: C 60% -> 80%, preempt

3라운드: A 100%
3라운드: B 100%
3라운드: C 100%
```

각 작업은 독점적으로 완료될 때까지 실행되지 않고, 일정 진행률에 도달하면 저장 후 다음 작업으로 넘어간다. 로그에 `Preempted`와 `Resumed`가 명시적으로 나타나므로 선점이 실제로 발생했다고 볼 수 있다.

따라서 현재 스케줄러는 하나의 작업을 끝까지 실행하는 비선점형 방식이 아니라, 준비된 작업들을 순서대로 순환시키는 방식으로 동작한다.

## 4. 후보별 검토

### Round-Robin 여부

Round-Robin은 각 작업에 실행 기회를 나누어 부여하고, 작업이 끝나지 않으면 다음 순서에서 이어서 실행한다. 현재 로그는 이 조건과 직접 대응한다.

```text
Thread-A 일부 실행 -> 선점
Thread-B 일부 실행 -> 선점
Thread-C 일부 실행 -> 선점
Thread-A 재개 -> 선점
Thread-B 재개 -> 선점
Thread-C 재개 -> 선점
Thread-A/B/C 완료
```

`Preempted`, `Progress saved`, `Resumed` 로그가 모두 존재하므로 Round-Robin 판단 근거가 충분하다.

### FCFS 여부

FCFS라면 먼저 등록된 작업이 완료될 때까지 실행되고, 그 다음 작업이 시작되는 흐름이 자연스럽다.

```text
Thread-A 완료 -> Thread-B 완료 -> Thread-C 완료
```

하지만 실제 로그에서는 `Thread-A`가 `40%`에서 선점된 뒤 `Thread-B`, `Thread-C`로 넘어간다. 작업이 완료되기 전에 다음 작업으로 전환되므로 FCFS라고 보기 어렵다.

### Priority 여부

Priority 스케줄링이라면 우선순위가 높은 작업이 먼저 선택되거나, 특정 작업이 반복적으로 앞서 실행되는 패턴이 나타날 수 있다. 그러나 현재 로그에서는 등록 순서와 동일하게 `Thread-A`, `Thread-B`, `Thread-C`가 순환 실행된다.

또한 특정 작업이 우선순위 때문에 끝까지 먼저 완료되는 것이 아니라, 모든 작업이 동일한 방식으로 `40%`, `80%`에서 선점된다. 따라서 Priority 기반 실행으로 판단할 직접 근거는 없다.

## 5. 최종 결론

현재 로그는 Round-Robin 실행 패턴을 명확히 보여준다. `Thread-A`, `Thread-B`, `Thread-C`가 순서대로 실행되고, 각 작업은 완료 전 `Preempted` 된 뒤 다음 라운드에서 `Resumed` 된다.

따라서 세 후보 중 가장 타당한 해석은 다음과 같다.

```text
Preemptive Round-Robin Scheduling
```

검증 결과: 통과. 스케줄링 증거는 실제 `agent-app` 실행 결과와 대응되며, 관찰 가능한 로그 기준으로 FCFS나 Priority보다 Round-Robin으로 해석하는 것이 가장 타당하다.
