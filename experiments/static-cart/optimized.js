var itemCount = 0;
var totalPrice = 0;

function renderSummary() {
  document.getElementById("summary").textContent =
    "상품 " + itemCount + "개, 합계 " + totalPrice + "원";
}

function addCoffee() {
  itemCount += 1;
  totalPrice += 4500;
  renderSummary();
}

function addSandwich() {
  itemCount += 1;
  totalPrice += 6500;
  renderSummary();
}

function resetCart() {
  itemCount = 0;
  totalPrice = 0;
  renderSummary();
}

function toggleReceipt() {
  var receipt = document.getElementById("receipt");
  receipt.hidden = !receipt.hidden;
  receipt.textContent = "결제 예정 금액: " + totalPrice + "원";
}

function neverUsedAdminDiscount() {}

window.addEventListener("DOMContentLoaded", function () {
  document
    .getElementById("coffeeButton")
    .addEventListener("click", addCoffee);

  document
    .getElementById("sandwichButton")
    .addEventListener("click", addSandwich);

  document
    .getElementById("resetButton")
    .addEventListener("click", resetCart);

  document
    .getElementById("receiptButton")
    .addEventListener("click", toggleReceipt);

  renderSummary();
});
