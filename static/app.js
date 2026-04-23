const sentences = [];

function escapeHtml(str) {
  const div = document.createElement('div');
  div.appendChild(document.createTextNode(str));
  return div.innerHTML;
}

function renderList() {
  const list = document.getElementById('sentence-list');
  const empty = document.getElementById('empty-msg');
  list.innerHTML = '';
  if (sentences.length === 0) {
    empty.style.display = 'block';
    return;
  }
  empty.style.display = 'none';
  sentences.forEach((text, i) => {
    const li = document.createElement('li');
    li.innerHTML = `
      <span class="num">${i + 1}.</span>
      <span class="text">${escapeHtml(text)}</span>
      <button class="remove-btn" aria-label="Remove sentence ${i + 1}">✕</button>
    `;
    li.querySelector('.remove-btn').addEventListener('click', () => removeSentence(i));
    list.appendChild(li);
  });
}

function addSentence() {
  const input = document.getElementById('sentence-input');
  const text = input.value.trim();
  if (!text) return;
  sentences.push(text);
  input.value = '';
  input.focus();
  renderList();
  clearResult();
}

function removeSentence(index) {
  sentences.splice(index, 1);
  renderList();
  clearResult();
}

function clearResult() {
  document.getElementById('audio-player').classList.add('hidden');
  document.getElementById('download-link').classList.add('hidden');
  setStatus('');
}

async function generate() {
  if (sentences.length === 0) {
    setStatus('Add at least one sentence first.', true);
    return;
  }

  const btn = document.getElementById('generate-btn');
  btn.disabled = true;
  btn.textContent = 'Generating…';
  setStatus(`Processing ${sentences.length} sentence${sentences.length !== 1 ? 's' : ''}…`);
  clearResult();

  const payload = {
    sentences,
    repetitions: parseInt(document.getElementById('repetitions').value, 10),
    pause_per_word: parseFloat(document.getElementById('pause-per-word').value),
    voice: document.getElementById('voice').value,
    model: document.getElementById('quality').value,
    accent: document.getElementById('accent').value,
  };

  try {
    const response = await fetch('/api/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({ error: 'Unknown error' }));
      throw new Error(err.error || 'Generation failed');
    }

    const blob = await response.blob();
    const url = URL.createObjectURL(blob);

    const player = document.getElementById('audio-player');
    player.src = url;
    player.classList.remove('hidden');

    const link = document.getElementById('download-link');
    link.href = url;
    link.classList.remove('hidden');

    setStatus('Done!');
  } catch (err) {
    setStatus(err.message, true);
  } finally {
    btn.disabled = false;
    btn.textContent = 'Generate Audio File';
  }
}

function setStatus(msg, isError = false) {
  const el = document.getElementById('status');
  el.textContent = msg;
  el.className = isError ? 'status error' : 'status';
}

// Enter key (without Shift) submits sentence
document.getElementById('sentence-input').addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    addSentence();
  }
});

document.getElementById('add-btn').addEventListener('click', addSentence);
document.getElementById('generate-btn').addEventListener('click', generate);

// Show "waking up" notice if health check takes more than 3s (Render free tier cold start)
(async () => {
  const timer = setTimeout(() => {
    document.getElementById('server-status').classList.remove('hidden');
  }, 3000);
  try {
    await fetch('/api/health');
  } finally {
    clearTimeout(timer);
    document.getElementById('server-status').classList.add('hidden');
  }
})();

// Register service worker for PWA installability
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/sw.js');
}

renderList();
