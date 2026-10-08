function updateStatus(message) {
  document.getElementById("status").textContent = message;
}

function handleInitialClick() {
  updateStatus("기본 버튼 실행");

  if (!document.getElementById("dynamicButton")) {
    var button = document.createElement("button");
    button.id = "dynamicButton";
    button.textContent = "동적으로 생성된 버튼";
    button.addEventListener("click", handleDynamicClick);
    document.getElementById("dynamicArea").appendChild(button);
  }
}

function handleDynamicClick() {}

function toggleMenu() {
  var menu = document.getElementById("menu");
  menu.hidden = !menu.hidden;
  updateStatus("메뉴 상태 변경");
}

function handleMenuItem() {
  updateStatus("메뉴 항목 실행");
}

function handleInput() {}

function neverCalledFunction() {}

window.addEventListener("DOMContentLoaded", function () {
  document
    .getElementById("initialButton")
    .addEventListener("click", handleInitialClick);

  document
    .getElementById("menuButton")
    .addEventListener("click", toggleMenu);

  document
    .getElementById("menuItem")
    .addEventListener("click", handleMenuItem);

  document
    .getElementById("nameInput")
    .addEventListener("input", handleInput);
});
