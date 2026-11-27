# 버튼 클릭 후보 추가: 변경 코드와 검증 결과

2026-11-18. 원본 Muzeel 기준선을 보존하고, 별도 실험 사본에서 버튼 후보 수집만 보완했다. 직접 연결·이벤트 위임 두 최소 예제를 다시 실행했고, 원본·계측본·최적화본 총 6개 대상에서 버튼 기능을 확인했다.

## 변경 위치와 코드

Muzeel의 `browser_interaction_bot/HTMLDocumentUtil.py`에 있는 `dfs()`에서 기존 `for listener in listeners:` 반복문 직후에 아래 코드를 추가했다.

```python
if root.name == "button" and not any(
    listener["type"] == "click" for listener in listeners
):
    self.event_list.append(Event("click", xpath))
```

- `root`는 재귀 순회 중인 현재 DOM 요소다. HTML의 `id="root"`만을 가리키지 않는다.
- `root.name == "button"`: 현재 요소가 실제 `<button>`인지 검사한다.
- `not any(...)`: 이미 직접 연결된 native click 리스너가 있으면 새 후보를 넣지 않는다. 기존 리스너 조회·후보 등록은 유지한다.
- `Event("click", xpath)`: 해당 버튼 위치에 대한 클릭 행동을 Python 후보 목록에 추가한다. 페이지 JavaScript에 리스너를 연결하지 않는다.
- 기존 DOM 순회를 재사용하며 버튼마다 새 후보는 최대 1개다. 모든 이벤트 종류와 모든 자식을 조합하지 않는다.

패치 원본: `experiments/event-listener-examples/button-candidate-variant/HTMLDocumentUtil.py`, 정확한 diff: 같은 폴더의 `button-candidates.patch`.

## 원본과 수정본 비교

| 항목 | 직접 연결: 원본 Muzeel | 직접 연결: 버튼 후보 추가 | 위임: 원본 Muzeel | 위임: 버튼 후보 추가 |
|---|---:|---:|---:|---:|
| 최초 이벤트 후보 | 1 | 1 | 1 | 2 |
| 관측 / 계측 함수 | 1 / 1 | 1 / 1 | 1 / 2 | 2 / 2 |
| 제거한 함수 본문 | 0 | 0 | 1 | 0 |
| 처리 JS 크기 | 333 bytes | 333 bytes | 477 bytes | 531 bytes |
| 버튼 3번 클릭 후 숫자 | 3 | 3 | 0 | 3 |
| Muzeel 처리 시간 | 21.40초 | 21.34초 | 21.36초 | 30.89초 |

위임 예제에서 원본 Muzeel은 root만 클릭했으나, 추가 버전의 trace에는 root와 버튼 클릭이 모두 있다. `handleRootClick`과 `incrementCount`가 모두 관측돼 증가 함수가 유지됐다. 직접 연결 예제에는 후보가 중복 추가되지 않았다.

추가 버전의 두 출력 JS는 각각 입력 JS와 SHA-256이 동일하다. 이 예제에는 두 함수 모두 필요하므로 0% 감소가 올바른 결과다. 관측 수만으로 판정하지 않고 같은 Chrome 150/iPhone X 조건에서 각 대상을 새 세션으로 열어 root 빈 공간 클릭 후 0 유지, 버튼 3회 클릭 후 3을 확인했다. 실제 HTTP 응답의 JS 해시도 파일과 대조했다.

시간은 단일 실행 기록이며 정밀 성능 벤치마크가 아니다. 이번 위임 예제에서는 후보 1개 추가로 탐색 비용이 증가했다. 실제 사이트의 버튼 수에 따른 비용은 별도 측정이 필요하다.

## 실행 분리와 검증 범위

- 원본 upstream의 69개 파일과 기존 기준선 실행은 보존했다.
- 수정 실행 사본의 원본 대비 변경은 `config.py`와 `browser_interaction_bot/HTMLDocumentUtil.py` 두 개다. 예제 HTML·JS, 함수 계측·제거 규칙은 유지했다.
- 기존 실행 도우미는 변경하지 않고 별도 복사본 `button-candidate-variant/launcher.py`를 만들었다. 이 복사본은 지정한 패치의 적용·해시 검사·변경 파일 목록 보고를 지원한다. 도우미 diff는 `launcher-changes.patch`에 있다.
- `optimize.py`에는 `--button-candidates` 선택지를 추가했다. 기본 동작은 기존 원본 Muzeel이고, 변형 실행은 `muzeel-button-candidates/`에 분리했다.
- 검증 스크립트에는 실행 폴더와 기대 결과를 선택하는 옵션을 추가했다. 기존 기준선 결과 파일은 덮어쓰지 않았다.
- 이번 규칙은 DOM 순회에서 만나는 실제 `<button>`에만 적용한다. 특정 root의 위임 리스너와 자식의 관계를 분석하는 규칙은 아니다. ARIA 역할의 커스텀 버튼, 입력 포커스, 새 DOM 수집, 상태별 재탐색은 이 패치에 포함하지 않았다.
- 효과는 이 두 최소 예제에서 확인한 것이다. 아직 Async React 전체의 기능 회복을 검증한 결과는 아니다.

## 새 실행과 증거

- 직접 연결: `muzeel-button-candidates/direct/runs/terminal-20261118-143148-21de2c/`.
- 위임: `muzeel-button-candidates/delegated/runs/terminal-20261118-143236-627ec4/`.
- 독립 검사: `experiments/event-listener-examples/results-buttons-20261118/comparison.json` 및 대상별 PNG.
- 원본 기준선 검사: `experiments/event-listener-examples/results-20261118/comparison.json`.
- 새 보기용 사이트: `results-buttons-20261118/sites/`의 `direct-original`, `direct-optimized`, `delegated-original`, `delegated-optimized`.

새 실행 명령:

```bash
cd "/Users/jeong-yunje/Documents/ChatGPT/실전산학/experiments/event-listener-examples"
/Users/jeong-yunje/Documents/muzeel-reproduction/.venv/bin/python optimize.py --example direct --button-candidates
/Users/jeong-yunje/Documents/muzeel-reproduction/.venv/bin/python optimize.py --example delegated --button-candidates
```
