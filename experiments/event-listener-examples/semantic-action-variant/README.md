# Muzeel 조작 요소와 검색 상태 탐색

2026년 11월 27일 수정한 탐색 코드다. 원본의 직접 리스너 수집에 실제 조작 요소,
클릭 후보 중복 제거, 검색 입력과 삭제를 추가한다. 함수 계측과 미관측 함수 본문
제거 규칙은 유지한다.

전체 과정과 측정은 [발전 과정 보고서](../../../output/reports/muzeel-exploration-evolution-2026-11-27.md)에 있다.

## 최신 동작

- button, 링크, 버튼·탭 역할, 텍스트 입력, textarea, contenteditable,
  checkbox/radio, select, range/number를 후보로 수집한다. 새 후보는 표시·활성
  상태와 inert·ARIA 비활성 상태를 확인한다.
- 같은 XPath의 click/mousedown/mouseup과 같은 종류의 중복 리스너를 합친다.
  더블클릭과 드래그는 분리한다. 기존 native 후보는 유지한다.
- 이전 경로 재생 후 새로 보이는 컨트롤을 수집한다. 중복 키는 `(행동, XPath)`다.
  동일 요소의 모든 상태를 재탐색하는 정책은 아니다.
- 검색창은 input type=search, role=searchbox 또는 placeholder의 search·검색으로
  식별한다. `fill:a`부터 `fill:z`까지 독립 행동 26개를 만든다.
  기존 큐가 끝부터 소비하므로 실제 첫 시도는 z부터 a다. 행동 사이 새로고침은 유지한다.
- `search-cycle:a-f`는 한 페이지에서 a 입력, 삭제, b 입력, 삭제를 f까지 이어간다.
  선택 후 Backspace로 React 입력 이벤트를 발생시킨다. 입력과 삭제 뒤 각각 50ms,
  마지막 삭제 뒤 500ms 쉰다. 묶음 안에는 새로고침·로딩 완료 대기가 없다.
  마지막 500ms도 완료를 보장하지 않는다.
- 일반 fill은 샘플 입력, select는 다른 활성 옵션, range/number는 한 단계 키보드
  조절을 사용한다. 기존 클릭 실행기의 추가 클릭은 유지하므로 후보 수와 클릭 수는 다르다.

## 파일

| 파일 | 역할 |
|---|---|
| `HTMLDocumentUtil.py` | 조작 요소 분류, XPath 인용, 후보 우선순위와 중복 제거 |
| `DefaultEventHandler.py` | 입력·선택·수치 조절 및 a~f 연속 입력·삭제 |
| `ChromeExecution.py` | 기존 큐와 재생을 유지하며 새 컨트롤 수집 |
| `run.py` | 원본·수정 정책과 React·Vue 선택, 새 실행 사본 준비 |
| `semantic-actions.patch` | 원본에서 최신 세 파일로 가는 전체 패치 |
| `history/` | 실제 실행 사본에서 복원한 네 단계 순차 패치 |
| `source-sha256.json` | 원본과 최신 세 파일의 해시 |
| `evidence/` | 시간·관측 수·파일 해시·검사 결과 요약 |
| `archive_results.py` | 로컬 보존 실행에서 패치와 요약 재추출 |
| `controls/` | 위임된 여러 조작 요소를 가진 최소 예제 |

## 원본에 패치 적용

기준은 `https://github.com/comnetsAD/Muzeel.git`의
`3dcce3ae78240855015748b5b536deb21a79d721`이다.
원본 해시는 `../../async-react-muzeel-original/UPSTREAM.json`에 있다.
별도 upstream 체크아웃에 절대 경로를 지정한다.

```bash
git -C /path/to/Muzeel apply --check /absolute/path/to/semantic-actions.patch
git -C /path/to/Muzeel apply /absolute/path/to/semantic-actions.patch
```

`history/`의 01, 02, 03, 04 패치를 순서대로 적용해도 같은 세 파일이 된다.
패치는 탐색 세 파일만 바꾼다. Chrome·프록시·DB 실행 환경 준비는 별도다.

## 기존 로컬 환경에서 실행

저장소 루트에서 기존 Muzeel 가상환경 Python을 사용한다.

```bash
python experiments/event-listener-examples/semantic-action-variant/run.py --target react --policy semantic-dedup
python experiments/event-listener-examples/semantic-action-variant/run.py --target vue --policy semantic-dedup
```

`original`은 원본 탐색, `semantic`은 조작 요소와 검색 행동 추가,
`semantic-dedup`은 여기에 클릭 후보 중복 제거를 적용한다.
direct, delegated, controls 대상도 지원한다.

실행기는 함께 보관한 `../button-candidate-variant/launcher.py`를 재사용한다.
정확한 실험 실행에는 다음 기존 로컬 입력과 환경이 필요하다.

- `experiments/async-react-muzeel-original/upstream/` 원본 체크아웃
- React의 `site-es2017/`, Vue의 `experiments/async-vue-muzeel-original/site-es2017/`
  고정 입력과 각 `input-manifest.json`
- 앱 Node 의존성, 고정 Chrome 150 브라우저·드라이버
- Python 의존성, mitmproxy, MySQL과 로컬 DB 설정

브라우저·node_modules·캐시·DB 설정·전체 run 디렉터리는 커밋하지 않는다.
clone만으로 당시 실험 환경이 완성되지는 않는다. `archive_results.py`도 보존한
run 디렉터리가 있는 원래 로컬 작업공간에서 사용한다.

## 검증 범위

초기 컨트롤 검사 16개와 작은 예제 검사는 a~z·a~f 추가 이전 버전의 결과다.
당시 소스 해시와 범위는 `evidence/initial-validation.json`에 있다.
초기 결과를 최신 코드의 재검사 결과로 해석하지 않는다.

최신 React에는 빠른 검색 반복, 키보드 탭 이동, 로그인 경로 회귀가 남았다.
취소 콜백 하나를 복원한 실험은 별도 최적화 복사본의 진단이다.
최신 탐색 코드에 해당 함수를 강제 보존하는 정책은 넣지 않았다.
최신 Vue는 요청대로 기능 검사 없이 생성·서빙했다.
17개 조건부 제거 후보도 분석 결과이며 새로운 제거 정책으로 구현하지 않았다.
