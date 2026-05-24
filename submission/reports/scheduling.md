# [Analysis] 스케줄링 추론 - 실제 앱 로그 기준 FCFS 패턴

## 1. 로그 관찰 개요

정상 모니터링 경로에서 `Thread-A`, `Thread-B`, `Thread-C`가 등록되었고, 실제 실행 로그에서는 하나의 작업이 `100%`까지 완료된 뒤 다음 작업이 시작됐다. 중간 선점이나 재개 로그는 발생하지 않았다.

## 2. Evidence & Logs (증거 자료)

원본 증거:

- `submission/evidence/scheduling/round-robin/stdout.log`
- `submission/evidence/scheduling/round-robin/agent_app.log`

로그 발췌:

```text
2026-05-19 13:41:56,409 [INFO] [Thread-B] Task Started. Calculating... (20%)
2026-05-19 13:41:56,613 [INFO] [Thread-B] Task Completed. (100%)
2026-05-19 13:41:56,665 [INFO] [Thread-C] Task Started. Calculating... (20%)
2026-05-19 13:41:56,869 [INFO] [Thread-C] Task Completed. (100%)
2026-05-19 13:41:56,920 [INFO] [Thread-A] Task Started. Calculating... (20%)
2026-05-19 13:41:57,124 [INFO] [Thread-A] Task Completed. (100%)
```

## 3. 패턴 분석 및 결론

관찰된 순서는 `Thread-B -> Thread-C -> Thread-A`였고, 각 작업은 시작 후 완료까지 연속 실행됐다. 이는 작업을 큐에서 하나씩 꺼내 완료한 뒤 다음 작업으로 넘어가는 FCFS 패턴과 가장 가깝다.

세 가지 후보를 기준으로 비교하면 다음과 같다.

### Round-Robin 여부

Round-Robin은 각 작업에 일정한 time quantum을 부여하고, 작업이 끝나지 않았더라도 일정 시간이 지나면 다음 작업으로 넘기는 방식이다. 따라서 로그에는 다음과 같은 패턴이 나타나는 것이 자연스럽다.

```text
Thread-B 일부 실행
Thread-C 일부 실행
Thread-A 일부 실행
Thread-B 재개
Thread-C 재개
Thread-A 재개
```

또는 `Preempted`, `Resumed`처럼 실행이 중간에 끊기고 다시 이어지는 흔적이 보여야 한다. 하지만 실제 로그에서는 `Thread-B`가 `20%`에서 시작한 뒤 `100%` 완료까지 연속 실행되고, 그 다음에야 `Thread-C`가 시작된다. `Thread-C`, `Thread-A`도 동일하게 시작 후 완료까지 끊기지 않는다. 따라서 Round-Robin으로 보기 어렵다.

### Priority 여부

Priority 스케줄링은 각 작업의 우선순위를 기준으로 실행 순서를 결정한다. 이 경우 로그나 설정에서 우선순위 값, 우선순위 큐, 높은 우선순위 작업의 선점 같은 근거가 확인되어야 한다.

현재 로그에는 `Thread-A`, `Thread-B`, `Thread-C`가 등록되었다는 정보만 있고, 각 스레드의 priority 값이나 우선순위 비교 로그는 없다. 또한 특정 작업이 우선순위 때문에 다른 작업을 선점하는 모습도 없다. 실행 순서가 `B -> C -> A`였다는 사실만으로는 Priority라고 판단할 근거가 부족하다.

### FCFS 여부

FCFS는 먼저 선택된 작업을 완료할 때까지 실행하고, 그 작업이 끝난 뒤 다음 작업을 실행하는 방식이다. 실제 로그는 이 패턴과 일치한다.

```text
Thread-B 시작 -> Thread-B 완료
Thread-C 시작 -> Thread-C 완료
Thread-A 시작 -> Thread-A 완료
```

각 작업 사이에 중간 전환이 없고, 한 작업이 `100%` 완료된 뒤 다음 작업이 시작된다. 따라서 관찰 가능한 로그만 기준으로 하면 세 후보 중 FCFS가 가장 논리적으로 타당하다.

검증 결과: PASS. 스케줄링 증거는 실제 `agent-app-leak` 실행 결과와 대응된다.
