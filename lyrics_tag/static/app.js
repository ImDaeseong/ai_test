'use strict';

const MAX_SEGMENTS = 5000;
const MAX_TEXT_LENGTH = 1000;

let segments = [];
let selectedIdx = -1;
let audioObjectUrl = null;

const audioInput = document.getElementById('audio-input');
const dropZone = document.getElementById('drop-zone');
const fileInfo = document.getElementById('file-info');
const loadBtn = document.getElementById('load-btn');
const lyricsInputEl = document.getElementById('lyrics-input');
const playerSection = document.getElementById('player-section');
const audioPlayer = document.getElementById('audio-player');
const currentTimeEl = document.getElementById('current-time');
const durationEl = document.getElementById('duration');
const lyricsSection = document.getElementById('lyrics-section');
const lyricsList = document.getElementById('lyrics-list');
const downloadLrcBtn = document.getElementById('download-lrc-btn');
const resetTimesBtn = document.getElementById('reset-times-btn');
const timedCountEl = document.getElementById('timed-count');

function fmtTime(sec) {
  if (!Number.isFinite(sec)) return '0:00.000';
  const minutes = Math.floor(sec / 60);
  const seconds = (sec % 60).toFixed(3).padStart(6, '0');
  return `${minutes}:${seconds}`;
}

function lrcTag(sec) {
  if (sec === null || !Number.isFinite(sec)) return '[--:--.---]';
  const minutes = Math.floor(sec / 60);
  const seconds = sec % 60;
  return `[${String(minutes).padStart(2, '0')}:${seconds.toFixed(3).padStart(6, '0')}]`;
}

function parseLyrics(text) {
  const lines = text
    .split('\n')
    .map(line => line.trim())
    .filter(Boolean);

  if (lines.length > MAX_SEGMENTS) {
    throw new Error(`가사는 최대 ${MAX_SEGMENTS}줄까지 입력할 수 있습니다.`);
  }

  const tooLongIndex = lines.findIndex(line => line.length > MAX_TEXT_LENGTH);
  if (tooLongIndex >= 0) {
    throw new Error(`${tooLongIndex + 1}번째 줄이 너무 깁니다. 줄당 최대 ${MAX_TEXT_LENGTH}자까지 입력할 수 있습니다.`);
  }

  return lines;
}

async function readErrorMessage(response) {
  try {
    const data = await response.json();
    return data.error || '요청 처리에 실패했습니다.';
  } catch {
    return '요청 처리에 실패했습니다.';
  }
}

function handleFile(file) {
  if (!file) return;

  if (audioObjectUrl) URL.revokeObjectURL(audioObjectUrl);
  audioObjectUrl = URL.createObjectURL(file);

  fileInfo.classList.remove('error');
  fileInfo.textContent = `선택: ${file.name} (${(file.size / 1024 / 1024).toFixed(1)} MB)`;
  audioPlayer.src = audioObjectUrl;
  currentTimeEl.textContent = fmtTime(0);
  durationEl.textContent = fmtTime(0);
  playerSection.hidden = false;
  updateLoadBtn();
}

function updateLoadBtn() {
  const hasAudio = Boolean(audioObjectUrl);
  const hasLyrics = lyricsInputEl.value.trim().length > 0;
  loadBtn.disabled = !(hasAudio && hasLyrics);
}

function updateTimedCount() {
  const count = segments.filter(s => s.start !== null).length;
  timedCountEl.textContent = `${count} / ${segments.length} 완료`;
}

function renderLyrics() {
  lyricsList.replaceChildren();

  segments.forEach((segment, index) => {
    const row = document.createElement('div');
    const timeTag = document.createElement('span');
    const lyricText = document.createElement('span');

    row.className = 'lyric-row';
    row.dataset.idx = String(index);
    if (segment.start !== null) row.classList.add('timed');

    timeTag.className = 'time-tag';
    timeTag.textContent = lrcTag(segment.start);

    lyricText.className = 'lyric-text';
    lyricText.textContent = segment.text;

    row.append(timeTag, lyricText);
    row.addEventListener('click', () => stampTime(index));
    lyricsList.appendChild(row);
  });
  updateTimedCount();
}

function updateRow(index) {
  const row = lyricsList.querySelector(`.lyric-row[data-idx="${index}"]`);
  if (!row) return;

  const segment = segments[index];
  row.querySelector('.time-tag').textContent = lrcTag(segment.start);
  row.classList.toggle('timed', segment.start !== null);
}

function selectRow(index) {
  if (index < 0 || index >= segments.length) return;

  document.querySelectorAll('.lyric-row.selected').forEach(el => el.classList.remove('selected'));

  const row = lyricsList.querySelector(`.lyric-row[data-idx="${index}"]`);
  if (row) {
    row.classList.add('selected');
    row.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  }
  selectedIdx = index;
}

function stampTime(index) {
  if (index < 0 || index >= segments.length) return;

  segments[index].start = Number(audioPlayer.currentTime.toFixed(3));
  updateRow(index);
  updateTimedCount();
  selectRow(Math.min(index + 1, segments.length - 1));
}

function highlightAudioActive() {
  const currentTime = audioPlayer.currentTime;
  let active = -1;

  for (let i = segments.length - 1; i >= 0; i--) {
    if (segments[i].start !== null && currentTime >= segments[i].start) {
      active = i;
      break;
    }
  }

  document.querySelectorAll('.lyric-row.audio-active').forEach(el => el.classList.remove('audio-active'));
  if (active >= 0) {
    const row = lyricsList.querySelector(`.lyric-row[data-idx="${active}"]`);
    if (row) row.classList.add('audio-active');
  }
}

dropZone.addEventListener('click', () => audioInput.click());
audioInput.addEventListener('change', () => handleFile(audioInput.files[0]));
dropZone.addEventListener('dragover', event => {
  event.preventDefault();
  dropZone.classList.add('dragover');
});
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
dropZone.addEventListener('drop', event => {
  event.preventDefault();
  dropZone.classList.remove('dragover');
  handleFile(event.dataTransfer.files[0]);
});

lyricsInputEl.addEventListener('input', updateLoadBtn);

loadBtn.addEventListener('click', () => {
  try {
    const lines = parseLyrics(lyricsInputEl.value);
    if (lines.length === 0) return;

    segments = lines.map(text => ({ text, start: null }));
    renderLyrics();
    lyricsSection.hidden = false;
    selectRow(0);
  } catch (error) {
    alert(error.message);
  }
});

audioPlayer.addEventListener('timeupdate', () => {
  currentTimeEl.textContent = fmtTime(audioPlayer.currentTime);
  highlightAudioActive();
});

audioPlayer.addEventListener('loadedmetadata', () => {
  durationEl.textContent = fmtTime(audioPlayer.duration);
});

audioPlayer.addEventListener('error', () => {
  fileInfo.textContent = '오디오 파일을 불러올 수 없습니다.';
  fileInfo.classList.add('error');
  playerSection.hidden = true;
});

document.addEventListener('keydown', event => {
  const tagName = event.target.tagName;
  if (tagName === 'INPUT' || tagName === 'TEXTAREA') return;

  if (event.code === 'Space') {
    event.preventDefault();
    stampTime(selectedIdx);
  } else if (event.code === 'ArrowDown') {
    event.preventDefault();
    selectRow(selectedIdx + 1);
  } else if (event.code === 'ArrowUp') {
    event.preventDefault();
    selectRow(selectedIdx - 1);
  } else if (event.code === 'KeyP') {
    event.preventDefault();
    if (audioPlayer.paused) audioPlayer.play();
    else audioPlayer.pause();
  } else if (event.code === 'ArrowLeft') {
    event.preventDefault();
    audioPlayer.currentTime = Math.max(0, audioPlayer.currentTime - 2);
  } else if (event.code === 'ArrowRight') {
    event.preventDefault();
    audioPlayer.currentTime = Math.min(audioPlayer.duration || 0, audioPlayer.currentTime + 2);
  }
});

downloadLrcBtn.addEventListener('click', async () => {
  const timed = segments
    .filter(segment => segment.start !== null)
    .sort((a, b) => a.start - b.start);

  if (timed.length === 0) {
    alert('타임태그가 입력된 줄이 없습니다.');
    return;
  }

  const originalText = downloadLrcBtn.textContent;
  downloadLrcBtn.disabled = true;
  downloadLrcBtn.textContent = '처리 중...';

  try {
    const response = await fetch('/download_lrc', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        segments: timed.map(segment => ({ start: segment.start, text: segment.text })),
      }),
    });

    if (!response.ok) throw new Error(await readErrorMessage(response));

    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = 'lyrics.lrc';
    document.body.appendChild(anchor);
    anchor.click();
    document.body.removeChild(anchor);
    URL.revokeObjectURL(url);
  } catch (error) {
    alert(error.message);
  } finally {
    downloadLrcBtn.disabled = false;
    downloadLrcBtn.textContent = originalText;
  }
});

resetTimesBtn.addEventListener('click', () => {
  if (!confirm('모든 타임태그를 초기화할까요?')) return;

  segments.forEach(segment => {
    segment.start = null;
  });
  renderLyrics();
  selectRow(0);
});
