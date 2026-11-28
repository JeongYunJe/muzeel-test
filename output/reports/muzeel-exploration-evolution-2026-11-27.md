# Muzeel 탐색 알고리즘 발전 과정과 최적화 결과

2026년 11월 27일 수정한 탐색 코드와 React·Vue 결과를 정리한다.
직접 리스너만 찾던 탐색에 조작 요소와 검색 행동을 추가해 React의 관측 일반 함수는
505개에서 613개, Vue는 333개에서 365개로 늘었다. 최신 React에도 회귀가 남아 있어
전체 기능 보존을 달성한 상태는 아니다.

코드는 [semantic-action-variant](../../experiments/event-listener-examples/semantic-action-variant/)에 있다.
원본 Muzeel과 기존 버튼 후보 실험은 보존했다. React·Vue 앱 소스를 고쳐서
회귀를 감추는 방식은 사용하지 않았다.

## 출발점과 변경 범위

원본은 DOM에서 각 요소의 직접 리스너를 조회하고, 발견한 이벤트에 정해진 행동을
실행한다. React처럼 root에 이벤트가 위임되면 root 리스너는 보이지만 실제 하위
검색창·탭·버튼을 충분히 조작하지 못했다. 기존 버튼 후보 실험은 이를 작은 예제로
확인한 선행 작업이다.

이번 변경은 후보 수집과 행동 실행에 한정된다. 함수 진입 로그 계측과
미관측 함수 본문을 비우는 제거 규칙은 유지했다. 기준 원본은 comnetsAD/Muzeel의
`3dcce3ae78240855015748b5b536deb21a79d721`이다.

## 실제 코드의 발전

### 조작 요소 후보와 중복 제거

`HTMLDocumentUtil.py`에 button, 링크, 버튼·탭 역할, 입력·선택 컨트롤 분류를
추가했다. 표시·활성 상태를 확인하고 숨김·inert·ARIA 비활성 요소를 새 후보에서
제외했다. native 후보는 유지하고 조작 요소 후보를 먼저 소비하도록 정렬했다.

같은 XPath의 click, mousedown, mouseup은 click으로 합쳤다. 같은 종류의
capture/bubble 리스너 중복도 합치되 더블클릭·드래그는 분리했다.
모든 root 이벤트를 모든 자식과 조합하는 후보 폭증을 피하기 위한 선택이다.

`DefaultEventHandler.py`에는 포커스 후 입력, select의 다른 활성 옵션 선택,
range·number의 한 단계 키보드 조절을 추가했다. range 중앙을 클릭해 큰 지연값을
선택하는 일을 피했다. 기존 클릭 실행기의 추가 클릭은 유지하므로 후보 수와
물리적 클릭 수는 일치하지 않는다.

`ChromeExecution.py`는 기존 큐·새로고침·이전 행동 재생을 유지하면서 부모 경로
재생 후 새 조작 요소를 수집한다. 중복 키는 `(행동, XPath)`다.
상태 해시나 분기 커버리지에 따른 재탐색은 구현하지 않았다.

첫 React 실행 사본과 원본의 차이는
[`01-react-semantic-before-xpath.patch`](../../experiments/event-listener-examples/semantic-action-variant/history/01-react-semantic-before-xpath.patch)에 있다.
이 단계에서는 일반 함수 581개를 관측했다.

### XPath 인용 오류 수정

클래스에 따옴표가 들어간 Tailwind 요소에서 XPath가 깨져 강의 버튼을 놓쳤다.
XPath 리터럴은 작은따옴표·큰따옴표·concat으로 구성하고, CDP에 넘기는 JavaScript
문자열은 JSON 인코딩하도록 수정했다. 관측 함수가 581개에서 597개로 늘었다.

실행 사본 사이 차이는
[`02-react-semantic-xpath.patch`](../../experiments/event-listener-examples/semantic-action-variant/history/02-react-semantic-xpath.patch)에 있다.
초기 컨트롤 검사 16개와 작은 direct/delegated/controls 예제 검사는 이 시기 결과다.
React 초기 제거본의 기존 6개 검사는 원본 Muzeel 1/6, 수정 Muzeel 2/6이었다.
관측 증가만으로 검색·로그인 기능이 보존되지는 않았다.

### a부터 z 개별 검색

기존 fill의 `ABCD`는 결과가 없어 일치 결과를 추가하는 검색 함수와 기존 목록에서
특정 항목만 남기는 React 갱신 경로를 실행하지 못했다. 별도 진단에서 해당 함수의
삭제를 확인했다.

검색창에 `fill:a`부터 `fill:z`까지 독립 행동 26개를 추가했다. type=search,
role=searchbox 또는 placeholder의 search·검색으로 대상을 식별한다.
기존 큐를 유지하므로 독립 행동 사이에는 새로고침이 있고 실제 첫 시도는 z부터 a다.
관측 함수는 597개에서 606개가 됐다.

실제 코드 차이는
[`03-react-search-az.patch`](../../experiments/event-listener-examples/semantic-action-variant/history/03-react-search-az.patch)다.

### a부터 f 연속 입력과 삭제

독립 검색만으로는 같은 문서에서 화면 전환이 겹치는 상태를 충분히 다루지 못했다.
기존 26개를 유지하면서 `search-cycle:a-f` 행동 하나를 추가했다.

```text
a 입력 → 전체 삭제 → b 입력 → 전체 삭제 → … → f 입력 → 전체 삭제
```

묶음 안에서는 새로고침하지 않는다. 선택 후 Backspace로 지워 React의 입력 이벤트를
발생시킨다. 입력·삭제 뒤 각각 50ms, 마지막 삭제 뒤 500ms 쉰다.
이는 로딩 완료를 확인하는 대기가 아니다. 관측 함수는 606개에서 613개,
Muzeel 시간은 407.69초에서 429.91초로 변했다.

차이는 [`04-react-search-az-af.patch`](../../experiments/event-listener-examples/semantic-action-variant/history/04-react-search-az-af.patch)에 있다.
이 단계가 최신 core 탐색 알고리즘이다.

### 같은 정책을 Vue 변환 예제에 적용

`run.py`에 vue 대상을 추가하고 기존 Vue manifest에서 JavaScript 경로를 읽도록 했다.
core 세 파일은 React와 같은 버전이다. Vue 앱 소스나 결과 함수를 수작업으로 고치지
않았다. 최신 Vue는 사용자 요청대로 기능 검사 없이 최적화하고 서버로 제공했다.

## 최적화 결과

React는 동일한 338,463바이트 입력과 일반 함수 1,155개를 사용했다.
Chrome 150.0.7871.124, iPhone X 프리셋이다.
시간은 `completed_sites_record`의 Muzeel 처리 시간이며 준비·집계·서버 시작은 제외한다.
조건별 1회 측정이므로 정밀 성능 벤치마크로 일반화하지 않는다.

| React 단계 | 최초 후보 | 관측 함수 | 삭제 본문 범위 | 시간 | 결과 JS 바이트 |
|---|---:|---:|---:|---:|---:|
| 원본 Muzeel | 143 | 505 | 557 | 271.17초 | 233,157 |
| 조작 후보·중복 제거, XPath 수정 전 | 93 | 581 | 483 | 161.44초 | 246,517 |
| XPath 인용 수정 | 101 | 597 | 475 | 226.78초 | 248,225 |
| a~z 개별 검색 추가 | 126 | 606 | 468 | 407.69초 | 249,537 |
| a~f 입력·삭제 추가 | 127 | 613 | 464 | 429.91초 | 250,660 |

원본 대비 최종 관측은 108개, 시간은 약 158.74초 증가했다. 더 많은 함수를 보존해
결과 JS도 커졌다. 최신 크기 감소율은 25.94%다. 초기 정책에는 후보 선택·행동·중복
제거·XPath 변경이 함께 들어가 각각의 독립 효과를 이 표만으로 분리할 수 없다.

Vue는 동일한 142,956바이트 입력과 일반 함수 583개를 사용했다.
브라우저·프리셋은 같지만 원본은 11월 12일, 수정본은 11월 27일 측정이다.

| Vue 단계 | 최초 후보 | 관측 함수 | 삭제 본문 범위 | 시간 | 결과 JS 바이트 |
|---|---:|---:|---:|---:|---:|
| 원본 Muzeel | 19 | 333 | 230 | 140.34초 | 116,148 |
| 최신 탐색 정책 | 47 | 365 | 198 | 300.98초 | 122,802 |

관측은 32개, 시간은 약 160.65초 증가했다. 최신 크기 감소율은 14.10%다.
이번 Vue 출력의 기능 보존 여부는 검사하지 않았다.
정확한 값·입력/출력 SHA-256·실행 경로·실행 당시 core 해시는
[`optimization-history.json`](../../experiments/event-listener-examples/semantic-action-variant/evidence/optimization-history.json)에 있다.

## 최신 React에서 확인한 회귀

Chrome 158 데스크톱에서 원본과 최신 출력에 동일한 11개 시나리오를 적용했고
원본은 모두 통과했다. 최적화본의 초기 실패 중 완료 버튼 관련 두 건은 화면 전환 후
700ms 기다린 클릭에서 양쪽 모두 통과해 회귀 목록에서 제외했다.

| 종류 | 조작 | 최신 출력 결과 |
|---|---|---|
| 빠른 검색 반복 | 입력·전체 삭제를 30ms 대기와 함께 반복 | 로딩 유지, React #177·null.name 오류; 독립 실행 3/3 재현 |
| 키보드 탭 이동 | All에 포커스 후 ArrowRight, End, Space | 첫 방향키에서 All에 포커스가 남음 |
| 로그인 경로 | /login 직접 열기 | Email/password 폼과 Login 버튼 없음 |

일반 검색·지우기, 완료/취소와 필터, 검색 결과에서 완료 처리, 뒤로/앞으로 가기,
직접 검색 URL은 확인한 범위에서 동작했다. 지연 중 검색 교체는 마지막 결과가 맞아도
React 오류가 남는 경우가 있어 빠른 입력 회귀와 함께 기록했다.
관측 수는 모든 사용자 기능·입력·타이밍의 커버리지가 아니다.

## 삭제 함수 분석과 진단 복원

원본과 해시가 같은 빌드를 소스맵과 함께 재현해 원래 파일에 연결했다.
최신 React의 미관측 일반 함수는 542개다. 부모 본문과 함께 사라지는 내부 일반 함수
78개를 중복 제거하면 실제 비운 본문 범위는 464곳이다.

| 소속 | 삭제 본문 범위 |
|---|---:|
| React DOM | 353 |
| React | 35 |
| React Scheduler | 10 |
| 앱 코드 | 20 |
| Radix UI | 9 |
| fast-fuzzy | 5 |
| Base64 보조 코드 | 30 |
| 빌드 보조 코드 | 2 |

키보드 관련 getDirectionAwareKey, getFocusIntent, focusFirst, wrapArray와
앱의 Login·LoginForm·로그인 요청·미리 읽기 경로가 삭제 목록에 포함됐다.

빠른 검색에서는 `waitForCommitToBeReady`가 반환하는 취소 콜백의 삭제를 확인했다.
이 콜백은 취소 시 대기 중인 commit 콜백과 타이머를 정리한다.

```js
state.unsuspend = null;
clearTimeout(stylesheetTimer);
clearTimeout(imgTimer);
```

별도 복사본에서 원본 위치 226540의 이 본문 하나만 복원하자 동일 빠른 검색 검사가
결과 1개·pending 해제·오류 없음으로 통과했다. 취소 후 남은 비동기 완료 작업이
오래된 화면 갱신을 수행하는 것이 이 재현 사례의 원인이다.
진단용 복원이며 최신 탐색 코드나 출력에 직접 반영하지 않았다.

현재 앱 옵션과 Chrome 158을 고정하면 조건상 선택되지 않는 본문 17개,
950바이트도 분류했다. Node Buffer 구현, 환경별 fallback, 미사용 검색 옵션 경로다.
이 분류를 새 제거 정책으로 구현하지는 않았다. compareItemsInsertOrder는
기본 검색 동점 처리에서도 쓰이므로 이름만 보고 안전하게 분류하지 않았다.

## 커밋 범위와 현재 한계

최신 core 세 파일, 실행 어댑터, 공용 launcher, 최소 예제, 전체·단계별 패치,
원본/수정 해시와 작은 근거 JSON을 포함한다. 앱 의존성·브라우저·전체 캐시·DB 설정은
제외한다. 패치는 기준 upstream에 적용 가능하지만 정확한 재실행에는 README의
고정 입력과 실행 환경이 필요하다.

현재 구현은 조작 후보·XPath·a~z·a~f 확장까지다. 취소 콜백 강제 보존,
키보드·로그인 전용 탐색, 상태별 전체 재탐색, 커버리지 기반 입력 선택은 아직 없다.

- [초기 컨트롤과 React 검사](../../experiments/event-listener-examples/semantic-action-variant/evidence/initial-validation.json)
- [작은 예제 실험](../../experiments/event-listener-examples/semantic-action-variant/evidence/fixture-results.json)
- [최신 React 검사와 재확인](../../experiments/event-listener-examples/semantic-action-variant/evidence/latest-react-validation.json)
- [삭제 함수 분류와 취소 콜백 복원](../../experiments/event-listener-examples/semantic-action-variant/evidence/deleted-functions-summary.json)
- [17개 조건부 제거 후보](../../experiments/event-listener-examples/semantic-action-variant/evidence/conditional-removal-candidates.json)

초기 검사 결과는 당시 소스 해시에 해당한다. 이번 커밋 정리 중 최적화나 브라우저
기능 검사를 새로 실행하지 않았다.
