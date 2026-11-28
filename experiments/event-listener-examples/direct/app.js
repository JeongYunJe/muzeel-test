var root = document.getElementById("root");
var button = document.getElementById("increment");
var count = document.getElementById("count");

function incrementCount() {
  count.textContent = Number(count.textContent) + 1;
}

// 버튼 자체에 클릭 리스너를 연결합니다.
button.addEventListener("click", incrementCount);
