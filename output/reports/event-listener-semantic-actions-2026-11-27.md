# 조작 요소 후보 추가와 클릭 행동 중복 제거 실험

이 보고서는 a~z·a~f 검색 확장 이전의 초기 실행을 기록한다.
이후 코드와 최종 React·Vue 결과는 [전체 발전 과정](muzeel-exploration-evolution-2026-11-27.md)에 있다.

2026-11-27. 원본 Muzeel과 기존 버튼 후보 실험은 보존했다. 별도 실행 사본에서 조작 요소 후보 수집과 클릭 계열 행동 중복 제거를 적용하고, 코드 제거 후 독립 브라우저 검사까지 수행했다.

## 변경

- 버튼·링크·역할이 지정된 버튼/탭·입력창·선택 컨트롤을 의미 기반 후보로 추가하고 우선 실행한다. 현재 숨김·비활성·inert·ARIA 비활성 요소는 새 후보에서 제외하고, 이전 행동 경로를 재생한 뒤 새로 나타난 조작 요소를 수집한다.
- 입력은 포커스 후 지우고 입력하며 select는 다른 활성 옵션을 선택한다. range·number는 키보드로 한 단계 조절한다.
- 같은 XPath의 click/mousedown/mouseup과 같은 종류의 중복 리스너 후보를 합친다. 더블클릭·드래그는 유지한다.
- HTMLDocumentUtil.py, DefaultEventHandler.py, ChromeExecution.py를 변경했다. 계측기·제거 규칙은 그대로다. 각 run의 설정과 해시에 적용한 소스를 기록했다.

실제 React 검사에서 기존 XPath 생성기가 클래스 이름 안의 따옴표를 처리하지 못하는 문제를 발견했다. XPath 리터럴과 CDP에 전달하는 JavaScript 문자열의 인코딩을 수정하고 React를 재실행했다. 수정 전 진단 실행은 first-attempts.json에 보존하고, 아래 표에는 수정 후 실행을 사용한다. React의 변화는 두 정책과 이 요소 식별 수정의 결합 결과이며 각각의 효과를 분리한 결과는 아니다.

## 전체 파이프라인 측정

시간은 completed_sites_record에 기록된 Muzeel 처리 시간이다. launcher의 준비·수집·집계 전체 시간과 구분한다. 각 조건 한 번의 실행이며 정밀 성능 벤치마크가 아니다.

| 대상 | 정책 | 최초 후보 | 관측 / 계측 일반 함수 | 제거 범위 | Muzeel 시간 | JS 전 → 후 |
|---|---|---:|---:|---:|---:|---:|
| controls | semantic-dedup | 12 | 14 / 15 | 1 | 125.03초 | 2,131 → 2,107 bytes |
| controls | semantic | 15 | 14 / 15 | 1 | 153.45초 | 2,131 → 2,107 bytes |
| direct | semantic-dedup | 1 | 1 / 1 | 0 | 21.37초 | 333 → 333 bytes |
| delegated | semantic-dedup | 2 | 2 / 2 | 0 | 30.73초 | 531 → 531 bytes |
| react | semantic-dedup | 101 | 597 / 1155 | 475 | 226.78초 | 338,463 → 248,225 bytes |
| react | original | 143 | 505 / 1155 | 557 | 271.17초 | 338,463 → 233,157 bytes |

semantic은 의미 기반 후보만, semantic-dedup은 의미 기반 후보와 클릭 중복 제거를 함께 적용한다. original은 실행 설정 외의 upstream 알고리즘을 변경하지 않는다.

## 독립 기능 검사

새 서버·브라우저 세션에서 원본·계측본·제거본을 각각 검사했다. HTTP로 제공한 JS의 SHA-256을 실제 파일과 대조했다. React는 기존 6개 시나리오를 재사용했다.

| 대상 | 정책 | 원본 | 계측본 | 제거본 |
|---|---|---:|---:|---:|
| controls | semantic-dedup | 9/9 | 9/9 | 9/9 |
| controls | semantic | 9/9 | 9/9 | 9/9 |
| direct | semantic-dedup | 2/2 | 2/2 | 2/2 |
| delegated | semantic-dedup | 2/2 | 2/2 | 2/2 |
| react | semantic-dedup | 6/6 | 6/6 | 2/6 |
| react | original | 6/6 | 6/6 | 1/6 |

후보 수집·행동 실행 브라우저 검사 16개도 통과했다. 위임된 입력·선택·버튼, 숨김/비활성 제외, 메뉴 뒤 요소 재발견, 더블클릭·드래그 분리, 숫자 컨트롤 한 단계 조절을 확인했다.

## React에서 남은 실패

React 검사에서 자동화 도구가 Navigation API의 완료를 오래 기다린 첫 시도는 validation-navigation-first-attempt에 보존했다. 최종 React 검사는 pageLoadStrategy=none으로 문서 전환 후 실제 URL·목록·입력 상태를 기다리고 명령별 시간 제한을 적용했다. 원본·계측본·처리본에 동일한 검사 기준을 적용했다.

| 시나리오 | 원본 Muzeel 제거본 | 수정 Muzeel 제거본 |
|---|---|---|
| initial-list | 통과 | 통과 |
| search | 실패 | 실패 |
| complete-tab-empty | 실패 | 통과 |
| complete-and-filter | 실패 | 실패 |
| delayed-search | 실패 | 실패 |
| login | 실패 | 실패 |

수정 제거본은 검색어와 URL이 갱신되어도 검색 결과 검사가 실패했다. 완료 버튼으로 체크 표시가 생기고 Complete에서 완료 항목 1개를 표시하는 단계는 동작했으나, 이어지는 In Progress 필터 검사까지는 통과하지 못했다. 로그인도 실패했다. 정확한 미관측·제거 함수 원인은 이 실험에서 확정하지 않는다.

## 해석과 한계

- 후보 수 감소와 기능 보존을 별도로 평가한다. 함수 관측 수는 전체 함수·분기·사용자 기능 커버리지가 아니다.
- 기존 native 후보는 보존한다. 따라서 미지원 native 이벤트 후보가 남아 있을 수 있다.
- 원본 클릭 실행기의 추가 클릭 시도는 유지하므로 후보 수와 실제 마우스 클릭 횟수는 다르다.
- 상태별 재탐색·커버리지 기반 우선순위·AI 선택은 구현하지 않았다. 같은 XPath에서 상태나 데이터에 따라 달라지는 경로가 누락될 수 있다.
- 표본은 이번 최소 예제와 Async React의 고정 입력이다. 통과한 검사 밖의 기능 안전성을 보장하지 않는다.

- 최소 예제의 속도 비교는 XPath 인용부호 수정 전의 ID 기반 예제 실행이다. 최종 인용부호 처리는 별도 브라우저 검사와 React 재실행으로 검증했다. 모든 실행의 소스 해시는 각 run에 보존했다.

## 증거와 실행

- 코드와 정확한 패치: experiments/event-listener-examples/semantic-action-variant/ 및 semantic-actions.patch.
- 원본 upstream 69개 파일의 해시는 보존했다. 각 실행의 preexisting_database_rows_unchanged 및 제거 범위/관측 로그 일치 여부를 summary.json에 남겼다.
- 실행 및 독립 검사: experiments/event-listener-examples/semantic-action-variant/suite-20261127-170242/results.json 및 validation/results.json.
- 재현: 기존 가상환경 Python으로 run.py --target controls --policy semantic-dedup 또는 run.py --target react --policy semantic-dedup 실행. 모든 실행은 새 폴더를 만든다.
