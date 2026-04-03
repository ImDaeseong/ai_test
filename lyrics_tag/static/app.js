'use strict';

// ── State ──────────────────────────────────────────────────────────────────
let segments = [];      // [{id, start, end, text, userStart}]
let selectedIdx = -1;
let audioBlob = null;

// ── DOM refs ───────────────────────────────────────────────────────────────
const audioInput       = document.getElementById('audio-input');
const dropZone         = document.getElementById('drop-zone');
const fileInfo         = document.getElementById('file-info');
const transcribeBtn    = document.getElementById('transcribe-btn');
const statusEl         = document.getElementById('status');
const playerSection    = document.getElementById('player-section');
const audioPlayer      = document.getElementById('audio-player');
const currentTimeEl    = document.getElementById('current-time');
const durationEl       = document.getElementById('duration');
const lyricsSection    = document.getElementById('lyrics-section');
const lyricsList       = document.getElementById('lyrics-list');
const downloadLrcBtn   = document.getElementById('download-lrc-btn');
const resetTimesBtn    = document.getElementById('reset-times-btn');
const lyricsInputEl    = document.getElementById('lyrics-input');

// ── Helpers ────────────────────────────────────────────────────────────────
function fmtTime(sec) {
  const m = Math.floor(sec / 60);
  const s = (sec % 60).toFixed(3).padStart(6, '0');
  return `${m}:${s}`;
}

function lrcTag(sec) {
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return `[${String(m).padStart(2, '0')}:${s.toFixed(2).padStart(5, '0')}]`;
}

// ── File handling ──────────────────────────────────────────────────────────
function handleFile(file) {
  if (!file) return;
  audioBlob = file;
  fileInfo.textContent = `선택: ${file.name} (${(file.size / 1024 / 1024).toFixed(1)} MB)`;
  transcribeBtn.disabled = false;

  const url = URL.createObjectURL(file);
  audioPlayer.src = url;
  playerSection.hidden = false;
}

dropZone.addEventListener('click', () => audioInput.click());
audioInput.addEventListener('change', () => handleFile(audioInput.files[0]));

dropZone.addEventListener('dragover', e => {
  e.preventDefault();
  dropZone.classList.add('dragover');
});
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
dropZone.addEventListener('drop', e => {
  e.preventDefault();
  dropZone.classList.remove('dragover');
  handleFile(e.dataTransfer.files[0]);
});

// ── Transcribe ─────────────────────────────────────────────────────────────
transcribeBtn.addEventListener('click', async () => {
  if (!audioBlob) return;
  transcribeBtn.disabled = true;
  statusEl.textContent = 'Whisper 전사 중... (파일 크기에 따라 수십 초 소요)';

  const fd = new FormData();
  fd.append('audio', audioBlob);
  const lyricsText = lyricsInputEl ? lyricsInputEl.value.trim() : '';
  if (lyricsText) fd.append('lyrics', lyricsText);

  try {
    const res = await fetch('/transcribe', { method: 'POST', body: fd });
    const data = await res.json();
    if (data.error) throw new Error(data.detail ? `${data.error}\n\n${data.detail}` : data.error);

    segments = data.segments.map(s => ({ ...s, userStart: null }));
    const modeLabel = data.mode === 'aligned' ? '가사 정렬' : '자동 전사';
    statusEl.textContent = `${modeLabel} 완료: ${segments.length}개 세그먼트`;
    renderLyrics();
    lyricsSection.hidden = false;
    selectRow(0);
  } catch (err) {
    statusEl.textContent = '오류: ' + err.message;
    transcribeBtn.disabled = false;
  }
});

// ── Render ─────────────────────────────────────────────────────────────────
function renderLyrics() {
  lyricsList.innerHTML = '';
  segments.forEach((seg, i) => {
    const row = document.createElement('div');
    row.className = 'lyric-row';
    row.dataset.idx = i;

    const t = seg.userStart !== null ? seg.userStart : seg.start;
    const hasTimed = seg.userStart !== null;

    row.innerHTML = `
      <span class="time-tag">${lrcTag(t)}</span>
      <span class="lyric-text">${escHtml(seg.text)}</span>
    `;
    if (hasTimed) row.classList.add('timed');

    row.addEventListener('click', () => selectRow(i));
    lyricsList.appendChild(row);
  });
}

function updateRow(i) {
  const row = lyricsList.querySelector(`.lyric-row[data-idx="${i}"]`);
  if (!row) return;
  const seg = segments[i];
  const t = seg.userStart !== null ? seg.userStart : seg.start;
  row.querySelector('.time-tag').textContent = lrcTag(t);
  if (seg.userStart !== null) row.classList.add('timed');
  else row.classList.remove('timed');
}

function selectRow(i) {
  if (i < 0 || i >= segments.length) return;
  document.querySelectorAll('.lyric-row.selected')
    .forEach(el => el.classList.remove('selected'));
  const row = lyricsList.querySelector(`.lyric-row[data-idx="${i}"]`);
  if (row) {
    row.classList.add('selected');
    row.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  }
  selectedIdx = i;
}

function escHtml(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

// ── Audio time display ─────────────────────────────────────────────────────
audioPlayer.addEventListener('timeupdate', () => {
  currentTimeEl.textContent = fmtTime(audioPlayer.currentTime);
  highlightAudioActive();
});
audioPlayer.addEventListener('loadedmetadata', () => {
  durationEl.textContent = fmtTime(audioPlayer.duration);
});

function highlightAudioActive() {
  const ct = audioPlayer.currentTime;
  let active = -1;
  for (let i = segments.length - 1; i >= 0; i--) {
    const t = segments[i].userStart !== null ? segments[i].userStart : segments[i].start;
    if (ct >= t) { active = i; break; }
  }
  document.querySelectorAll('.lyric-row.audio-active')
    .forEach(el => el.classList.remove('audio-active'));
  if (active >= 0) {
    const row = lyricsList.querySelector(`.lyric-row[data-idx="${active}"]`);
    if (row) row.classList.add('audio-active');
  }
}

// ── Keyboard ───────────────────────────────────────────────────────────────
document.addEventListener('keydown', e => {
  const tag = e.target.tagName;
  if (tag === 'INPUT' || tag === 'TEXTAREA') return;

  if (e.code === 'Space') {
    e.preventDefault();
    if (selectedIdx >= 0) {
      segments[selectedIdx].userStart = parseFloat(audioPlayer.currentTime.toFixed(3));
      updateRow(selectedIdx);
    }
  }

  if (e.code === 'Enter') {
    e.preventDefault();
    selectRow(selectedIdx + 1);
  }

  if (e.code === 'KeyP') {
    e.preventDefault();
    if (audioPlayer.paused) audioPlayer.play();
    else audioPlayer.pause();
  }

  if (e.code === 'ArrowLeft') {
    e.preventDefault();
    audioPlayer.currentTime = Math.max(0, audioPlayer.currentTime - 2);
  }

  if (e.code === 'ArrowRight') {
    e.preventDefault();
    audioPlayer.currentTime = Math.min(audioPlayer.duration || 0,
                                        audioPlayer.currentTime + 2);
  }
});

// ── Download LRC ───────────────────────────────────────────────────────────
downloadLrcBtn.addEventListener('click', async () => {
  const payload = segments.map(s => ({
    start: s.userStart !== null ? s.userStart : s.start,
    text: s.text
  }));

  const res = await fetch('/download_lrc', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ segments: payload })
  });

  if (!res.ok) { alert('LRC 생성 실패'); return; }

  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'lyrics.lrc';
  a.click();
  URL.revokeObjectURL(url);
});

// ── Reset times ────────────────────────────────────────────────────────────
resetTimesBtn.addEventListener('click', () => {
  if (!confirm('모든 타이밍을 초기화할까요?')) return;
  segments.forEach(s => { s.userStart = null; });
  renderLyrics();
  selectRow(0);
});
