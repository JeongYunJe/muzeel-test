var root = document.getElementById('root');
function incrementCount() { document.getElementById('count').textContent = Number(document.getElementById('count').textContent) + 1; }
function searchChanged(value) { document.getElementById('search-result').textContent = value; }
function checkboxChanged(value) { document.getElementById('check-result').textContent = value ? 'on' : 'off'; }
function choiceChanged(value) { document.getElementById('choice-result').textContent = value; }
function customClicked() { document.getElementById('custom-result').textContent = '1'; }
function tabClicked() { document.getElementById('tab-result').textContent = 'selected'; }
function notesChanged(value) { document.getElementById('notes-result').textContent = value; }
function editorChanged(value) { document.getElementById('editor-result').textContent = value; }
function menuOpened() { document.getElementById('panel').hidden = false; }
function revealedClicked() { document.getElementById('revealed-result').textContent = '1'; }
function unusedFunction() { return 'never called'; }
function rootClick(event) {
  if (event.target.id === 'increment') incrementCount();
  if (event.target.id === 'custom') customClicked();
  if (event.target.id === 'tab') tabClicked();
  if (event.target.id === 'menu') menuOpened();
  if (event.target.id === 'revealed') revealedClicked();
}
function rootInput(event) {
  if (event.target.id === 'search') searchChanged(event.target.value);
  if (event.target.id === 'notes') notesChanged(event.target.value);
  if (event.target.id === 'editor') editorChanged(event.target.textContent);
}
function rootChange(event) {
  if (event.target.id === 'check') checkboxChanged(event.target.checked);
  if (event.target.id === 'choice') choiceChanged(event.target.value);
}
function rootMouse(event) { root.dataset.lastMouseType = event.type; }
root.addEventListener('click', rootClick);
root.addEventListener('click', rootMouse, true);
root.addEventListener('input', rootInput);
root.addEventListener('change', rootChange);
root.addEventListener('mousedown', rootMouse);
root.addEventListener('mouseup', rootMouse);
