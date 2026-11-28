var root = document.getElementById("root");
var button = document.getElementById("increment");
var count = document.getElementById("count");

function incrementCount() {
  count.textContent = Number(count.textContent) + 1;
}

function handleRootClick(event) {
  // root까지 전달된 이벤트가 +1 버튼에서 시작했는지 확인합니다.
  if (event.target === button) {
    incrementCount();
  }
}

// 버튼 대신 부모인 root에 클릭 리스너를 연결합니다.
root.addEventListener("click", handleRootClick);
