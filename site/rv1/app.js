let showAnswers = false;
let currentPack = null;

const LOCAL_RAZ_PACK_URL = 'http://127.0.0.1:8781/api/pack?limit=10';

function normalizePack(pack, source) {
  return {
    title: source === 'local-api' ? 'Reading V1 Local RAZ' : (pack.title || 'Reading V1'),
    items: pack.items || [],
  };
}

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

async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}

async function loadPack() {
  try {
    const apiPack = await fetchJson(LOCAL_RAZ_PACK_URL);
    if ((apiPack.items || []).length > 0) {
      currentPack = normalizePack(apiPack, 'local-api');
      render(currentPack);
      return;
    }
  } catch (error) {
    // Local RAZ API is optional. Fall back to checked-in static sample data.
  }
  const staticPack = await fetchJson('d.json');
  currentPack = normalizePack(staticPack, 'static');
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
