let showAnswers = false;
let currentPack = null;

function render(pack) {
  const title = document.getElementById('title');
  const sheet = document.getElementById('sheet');
  title.textContent = pack.title || 'Reading V1';
  sheet.innerHTML = '';
  (pack.items || []).forEach((item, index) => {
    const block = document.createElement('article');
    block.className = 'question';
    const q = document.createElement('p');
    q.textContent = `${index + 1}. ${item.q}`;
    const a = document.createElement('p');
    a.className = 'answer';
    a.textContent = `Answer: ${item.a}`;
    a.hidden = !showAnswers;
    block.append(q, a);
    sheet.appendChild(block);
  });
}

async function loadPack() {
  const response = await fetch('d.json');
  currentPack = await response.json();
  render(currentPack);
}

document.getElementById('loadBtn').addEventListener('click', loadPack);
document.getElementById('toggleBtn').addEventListener('click', () => {
  showAnswers = !showAnswers;
  document.getElementById('toggleBtn').textContent = showAnswers ? '隱藏答案' : '顯示答案';
  if (currentPack) render(currentPack);
});
document.getElementById('printBtn').addEventListener('click', () => window.print());

loadPack().catch(() => {
  document.getElementById('sheet').textContent = '題目載入失敗';
});
