/* ══════════════════════════════════════════════════════
   AI Music Producer — Client Logic
   ══════════════════════════════════════════════════════ */

'use strict';

// ── DOM refs ──────────────────────────────────────────────────────────────
const form         = document.getElementById('analyzeForm');
const promptInput  = document.getElementById('promptInput');
const promptHint   = document.getElementById('promptHint');
const analyzeBtn   = document.getElementById('analyzeBtn');
const loadSampleBtn= document.getElementById('loadSampleBtn');
const uploadZone   = document.getElementById('uploadZone');
const audioInput   = document.getElementById('audioInput');
const fileBadge    = document.getElementById('fileBadge');
const fileNameText = document.getElementById('fileNameText');
const removeFile   = document.getElementById('removeFile');

const stateEmpty    = document.getElementById('stateEmpty');
const stateProgress = document.getElementById('stateProgress');
const stateError    = document.getElementById('stateError');
const stateResult   = document.getElementById('stateResult');

const progressFill  = document.getElementById('progressFill');
const progressPct   = document.getElementById('progressPct');
const progressLabel = document.getElementById('progressLabel');
const parsedPreview = document.getElementById('parsedPreview');
const errorMsg      = document.getElementById('errorMsg');
const retryBtn      = document.getElementById('retryBtn');
const trackHero     = document.getElementById('trackHero');

const downloadBar   = document.getElementById('downloadBar');

// Step indicators
const steps = {
  parse:  document.getElementById('si-parse'),
  report: document.getElementById('si-report'),
  sheet:  document.getElementById('si-sheet'),
  visual: document.getElementById('si-visual'),
};

// ── State ──────────────────────────────────────────────────────────────────
let currentJobId = null;
let currentResult = null;
let activeTab = 'overview';

// ── Utility ───────────────────────────────────────────────────────────────
function show(el)  { el.classList.remove('hidden'); }
function hide(el)  { el.classList.add('hidden'); }

function showState(which) {
  [stateEmpty, stateProgress, stateError, stateResult].forEach(hide);
  show(which);
}

function escHtml(str) {
  return String(str)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function copyText(text, btn) {
  navigator.clipboard.writeText(text).then(() => {
    const orig = btn.textContent;
    btn.textContent = '복사됨!';
    btn.classList.add('copied');
    setTimeout(() => { btn.textContent = orig; btn.classList.remove('copied'); }, 1800);
  });
}

// ── LilyPond syntax highlight (simple) ───────────────────────────────────
function highlightLilyPond(code) {
  return escHtml(code)
    .replace(/(\\[a-zA-Z]+)/g, '<span class="ly-command">$1</span>')
    .replace(/(%.+)/g, '<span class="ly-comment">$1</span>')
    .replace(/"([^"]*)"/g, '"<span class="ly-string">$1</span>"');
}

// ── File Upload ───────────────────────────────────────────────────────────
uploadZone.addEventListener('click', () => audioInput.click());

uploadZone.addEventListener('dragover', e => {
  e.preventDefault();
  uploadZone.classList.add('drag-over');
});
uploadZone.addEventListener('dragleave', () => uploadZone.classList.remove('drag-over'));
uploadZone.addEventListener('drop', e => {
  e.preventDefault();
  uploadZone.classList.remove('drag-over');
  const file = e.dataTransfer.files[0];
  if (file) setAudioFile(file);
});

audioInput.addEventListener('change', () => {
  if (audioInput.files[0]) setAudioFile(audioInput.files[0]);
});

removeFile.addEventListener('click', () => {
  audioInput.value = '';
  hide(fileBadge);
});

function setAudioFile(file) {
  const allowed = ['.mp3','.wav','.flac','.ogg','.m4a'];
  const ext = '.' + file.name.split('.').pop().toLowerCase();
  if (!allowed.includes(ext)) {
    alert(`지원하지 않는 형식입니다: ${ext}\n지원 형식: ${allowed.join(', ')}`);
    return;
  }
  // Transfer to the actual hidden input (for drag-drop)
  try {
    const dt = new DataTransfer();
    dt.items.add(file);
    audioInput.files = dt.files;
  } catch(_) { /* DataTransfer not supported in all browsers */ }
  fileNameText.textContent = file.name;
  show(fileBadge);
}

// ── Load Sample ───────────────────────────────────────────────────────────
loadSampleBtn.addEventListener('click', async () => {
  loadSampleBtn.textContent = '불러오는 중...';
  loadSampleBtn.disabled = true;
  try {
    const res = await fetch('/api/sample');
    if (res.ok) {
      promptInput.value = await res.text();
      promptInput.focus();
      updatePromptHint();
    }
  } catch(e) { /* ignore */ }
  loadSampleBtn.textContent = '샘플 불러오기';
  loadSampleBtn.disabled = false;
});

// ── Prompt hint ──────────────────────────────────────────────────────────
function updatePromptHint() {
  const text = promptInput.value;
  const lines = text.split('\n').length;
  const sectionMatches = (text.match(/\[(Verse|Chorus|Pre-Chorus|Post-Chorus|Bridge|Intro|Outro|Rap|Hook|Drop|Interlude|Breakdown)/gi) || []).length;
  promptHint.textContent = sectionMatches
    ? `${lines}줄 · ${sectionMatches}개 섹션 감지됨`
    : lines > 1 ? `${lines}줄` : '';
}
promptInput.addEventListener('input', updatePromptHint);

// ── Form Submit ───────────────────────────────────────────────────────────
form.addEventListener('submit', async (e) => {
  e.preventDefault();

  const prompt = promptInput.value.trim();
  if (!prompt) {
    promptInput.focus();
    promptInput.style.borderColor = 'var(--error)';
    setTimeout(() => promptInput.style.borderColor = '', 1500);
    return;
  }

  analyzeBtn.disabled = true;
  analyzeBtn.querySelector('.btn-label').textContent = '분석 중...';
  showState(stateProgress);
  resetProgress();

  const fd = new FormData();
  fd.append('prompt', prompt);
  if (audioInput.files[0]) fd.append('audio', audioInput.files[0]);

  try {
    const res  = await fetch('/api/analyze', { method: 'POST', body: fd });
    const data = await res.json();

    if (data.error) { showError(data.error); return; }

    currentJobId = data.job_id;
    listenSSE(data.job_id);
  } catch (err) {
    showError('서버와 통신할 수 없습니다: ' + err.message);
  }
});

retryBtn.addEventListener('click', () => {
  showState(stateEmpty);
  analyzeBtn.disabled = false;
  analyzeBtn.querySelector('.btn-label').textContent = '분석 시작';
});

// ── SSE ───────────────────────────────────────────────────────────────────
function listenSSE(jobId) {
  const es = new EventSource(`/api/stream/${jobId}`);
  let terminated = false;

  es.onmessage = (e) => {
    const msg = JSON.parse(e.data);

    if (msg.type === 'ping') return;

    if (msg.type === 'step') {
      setProgress(msg.pct, msg.label);
      updateStepIndicators(msg.pct);
    }
    if (msg.type === 'parsed') {
      document.getElementById('ppTitle').textContent = msg.title;
      document.getElementById('ppGenre').textContent = msg.genre;
      document.getElementById('ppBpm').textContent = msg.bpm;
      document.getElementById('ppKey').textContent = msg.key;
      show(parsedPreview);
    }
    if (msg.type === 'warn') {
      console.warn('[warn]', msg.message);
    }
    if (msg.type === 'done') {
      terminated = true;
      es.close();
      setProgress(100, '완료!');
      currentResult = msg.result;
      setTimeout(() => renderResults(msg.result), 400);
    }
    if (msg.type === 'error') {
      terminated = true;
      es.close();
      showError(msg.message);
    }
  };

  es.onerror = () => {
    if (terminated) return;
    es.close();
    showError('연결이 끊겼습니다. 서버를 확인하세요.');
  };
}

// ── Progress helpers ─────────────────────────────────────────────────────
function resetProgress() {
  setProgress(0, '분석 준비 중...');
  hide(parsedPreview);
  Object.values(steps).forEach(s => { s.classList.remove('active','done'); });
}

function setProgress(pct, label) {
  progressFill.style.width = pct + '%';
  progressPct.textContent = Math.round(pct) + '%';
  progressLabel.textContent = label;
}

function updateStepIndicators(pct) {
  const thresholds = { parse: 20, report: 55, sheet: 70, visual: 90 };
  Object.entries(thresholds).forEach(([key, threshold]) => {
    const el = steps[key];
    if (pct >= threshold + 10) {
      el.classList.remove('active'); el.classList.add('done');
    } else if (pct >= threshold) {
      el.classList.remove('done'); el.classList.add('active');
    }
  });
}

// ── Error ─────────────────────────────────────────────────────────────────
function showError(msg) {
  errorMsg.textContent = msg;
  showState(stateError);
  analyzeBtn.disabled = false;
  analyzeBtn.querySelector('.btn-label').textContent = '분석 시작';
}

// ── Render Results ────────────────────────────────────────────────────────
function renderResults(result) {
  analyzeBtn.disabled = false;
  analyzeBtn.querySelector('.btn-label').textContent = '분석 시작';

  renderHero(result.metadata, result.audio_stats);
  renderOverview(result);
  renderReport(result.report_html);
  renderSheet(result.lilypond_code);
  renderVisual(result.visual);
  renderDownloads(result.files, result.job_id);

  showState(stateResult);
  switchTab('overview');
}

// ── Hero ──────────────────────────────────────────────────────────────────
function renderHero(m, audio) {
  const genres = (m.genre || []).map(g => `<span class="tag tag-genre">${escHtml(g)}</span>`).join('');
  const moods  = (m.mood  || []).map(g => `<span class="tag tag-mood">${escHtml(g)}</span>`).join('');

  const bpmDisplay = audio ? `${audio.bpm} <small style="font-size:.6em;color:var(--text-dim)">(검출)</small>` : m.bpm;
  const keyDisplay = audio ? `${audio.key} <small style="font-size:.6em;color:var(--text-dim)">(검출)</small>` : m.key;

  trackHero.innerHTML = `
    <div style="flex:1;min-width:0">
      <div class="hero-title">${escHtml(m.title)}</div>
      <div class="hero-artist">${escHtml(m.artist)}</div>
      <div class="hero-tags">${genres}${moods}</div>
    </div>
    <div class="hero-stats">
      <div class="stat-item"><div class="stat-val">${bpmDisplay}</div><div class="stat-lbl">BPM</div></div>
      <div class="stat-item"><div class="stat-val">${keyDisplay}</div><div class="stat-lbl">Key</div></div>
      <div class="stat-item"><div class="stat-val">${escHtml(m.time_signature)}</div><div class="stat-lbl">Time</div></div>
      <div class="stat-item"><div class="stat-val">${m.total_sections}</div><div class="stat-lbl">Sections</div></div>
      <div class="stat-item"><div class="stat-val">${m.total_lines}</div><div class="stat-lbl">Lines</div></div>
      ${audio ? `<div class="stat-item"><div class="stat-val">${audio.duration}</div><div class="stat-lbl">Duration</div></div>` : ''}
    </div>
  `;
}

// ── Overview Tab ──────────────────────────────────────────────────────────
function renderOverview(result) {
  const m = result.metadata;

  const kvRow = (k, v) => `
    <div class="ov-kv">
      <span class="ov-key">${k}</span>
      <span class="ov-val">${v}</span>
    </div>`;

  // Track info card
  const infoCard = `
    <div class="ov-card">
      <div class="ov-card-title">트랙 정보</div>
      ${kvRow('Language', escHtml(m.language))}
      ${kvRow('Vocal Style', escHtml((m.vocal_style||[]).join(', ') || 'N/A'))}
      ${kvRow('Instruments', escHtml((m.instruments||[]).join(', ') || 'N/A'))}
      ${kvRow('Total Words', m.total_lines + ' lines')}
    </div>`;

  // Chord progression card
  const chordPills = (m.chord_progression||[])
    .map(c => `<span class="chord-pill">${escHtml(c)}</span>`).join('');
  const chordCard = `
    <div class="ov-card">
      <div class="ov-card-title">코드 진행</div>
      <div class="chord-pills">${chordPills || '<span style="color:var(--text-dim)">N/A</span>'}</div>
    </div>`;

  // Audio stats card (if available)
  const audioCard = result.audio_stats ? `
    <div class="ov-card">
      <div class="ov-card-title">오디오 분석 (실측)</div>
      ${kvRow('Detected BPM', result.audio_stats.bpm)}
      ${kvRow('Detected Key', result.audio_stats.key)}
      ${kvRow('Duration', result.audio_stats.duration)}
      ${kvRow('Dynamic Range', result.audio_stats.dynamic_range + ' dB')}
      ${kvRow('Spectral Centroid', result.audio_stats.spectral_centroid + ' Hz')}
    </div>` : '';

  // Timeline table
  const timelineRows = (result.timeline || []).map(t => `
    <tr>
      <td style="color:var(--text-dim)">${t.idx}</td>
      <td style="font-weight:600;color:var(--text-bright)">${escHtml(t.name)}</td>
      <td>${t.start}</td>
      <td>${t.end}</td>
      <td>${t.duration}</td>
      <td>${t.lines}</td>
      <td><span class="energy-pill energy-${t.energy.replace('-','')}">${t.energy}</span></td>
    </tr>`).join('');

  const timelineCard = `
    <div class="ov-card" style="grid-column:1/-1">
      <div class="ov-card-title">섹션 타임라인</div>
      <table class="timeline-table">
        <thead><tr>
          <th>#</th><th>섹션</th><th>시작</th><th>끝</th><th>길이</th><th>라인</th><th>에너지</th>
        </tr></thead>
        <tbody>${timelineRows}</tbody>
      </table>
    </div>`;

  document.getElementById('overviewContent').innerHTML = `
    <div class="overview-grid">
      ${infoCard}${chordCard}${audioCard}${timelineCard}
    </div>`;
}

// ── Report Tab ────────────────────────────────────────────────────────────
function renderReport(html) {
  document.getElementById('reportContent').innerHTML = html || '<p style="color:var(--text-dim)">리포트를 생성할 수 없습니다.</p>';
}

// ── Sheet Music Tab ───────────────────────────────────────────────────────
function renderSheet(code) {
  if (!code) {
    document.getElementById('sheetContent').innerHTML = '<p style="color:var(--text-dim)">악보 코드를 생성할 수 없습니다.</p>';
    return;
  }

  const highlighted = highlightLilyPond(code);

  document.getElementById('sheetContent').innerHTML = `
    <div class="sheet-info">
      <span>&#9834;</span>
      <span>LilyPond .ly 파일 — <code>lilypond song.ly</code> 명령으로 PDF/PNG 악보를 렌더링할 수 있습니다.
      <a href="https://lilypond.org/download.html" target="_blank" rel="noopener">LilyPond 다운로드 →</a></span>
    </div>
    <div class="code-block-wrap">
      <button class="copy-btn" id="copyLyBtn">복사</button>
      <div class="code-block">
        <pre><code>${highlighted}</code></pre>
      </div>
    </div>`;

  document.getElementById('copyLyBtn').addEventListener('click', function() {
    copyText(code, this);
  });
}

// ── Visual Tab ────────────────────────────────────────────────────────────
function renderVisual(v) {
  if (!v) {
    document.getElementById('visualContent').innerHTML = '<p style="color:var(--text-dim)">비주얼 프롬프트를 생성할 수 없습니다.</p>';
    return;
  }

  // Palette
  const swatches = (v.palette || []).map(c => {
    const isHex = /^#/.test(c);
    const bg = isHex ? c : '#444';
    const hex = isHex ? c : c;
    return `<div class="swatch">
      <div class="swatch-circle" style="background:${bg}"></div>
      <div class="swatch-hex">${escHtml(hex)}</div>
    </div>`;
  }).join('');

  // Album art
  const albumArt = v.album_art_prompt ? `
    <div class="section-heading">앨범 커버 프롬프트 (Midjourney / DALL·E / Stable Diffusion)</div>
    <div class="prompt-box" id="albumArtBox">
      <div class="prompt-box-label">Album Art Prompt</div>
      <div id="albumArtText">${escHtml(v.album_art_prompt)}</div>
      <button class="copy-btn" id="copyAlbumBtn" style="position:static;margin-top:0.6rem;display:inline-block">복사</button>
    </div>` : '';

  // Video scenes
  const scenes = (v.video_scenes || []).map(sc => `
    <div class="scene-card">
      <div class="scene-section">[${escHtml(sc.section || '')}]</div>
      <div class="scene-prompt">${escHtml(sc.prompt || '')}</div>
      <div class="scene-meta">
        ${sc.camera ? `<span><span class="scene-meta-key">Camera:</span> ${escHtml(sc.camera)}</span>` : ''}
        ${sc.color  ? `<span><span class="scene-meta-key">Grade:</span> ${escHtml(sc.color)}</span>` : ''}
      </div>
    </div>`).join('');

  // Style guide
  const sg = v.style_guide || {};
  const styleItems = Object.entries(sg).map(([k, val]) => `
    <div class="style-item">
      <div class="style-key">${escHtml(k)}</div>
      <div class="style-val">${escHtml(String(val))}</div>
    </div>`).join('');

  // Keyword map
  const kwRows = Object.entries(v.keyword_map || {}).map(([kw, vis]) => `
    <div class="kw-row">
      <span class="kw-word">${escHtml(kw)}</span>
      <span class="kw-vis">${escHtml(vis)}</span>
    </div>`).join('');

  document.getElementById('visualContent').innerHTML = `
    <div class="theme-badge">&#127775; ${escHtml(v.theme)}</div>
    <div class="section-heading">컬러 팔레트</div>
    <div class="palette-row">${swatches}</div>
    ${albumArt}
    <div class="section-heading">영상 씬 프롬프트 (Runway / Kling / Pika)</div>
    <div class="scene-grid">${scenes}</div>
    ${styleItems ? `<div class="section-heading">스타일 가이드 (릴스/쇼츠)</div><div class="style-grid">${styleItems}</div>` : ''}
    ${kwRows ? `<div class="section-heading">키워드 → 비주얼 요소 매핑</div><div class="kw-grid">${kwRows}</div>` : ''}
  `;

  const copyAlbumBtn = document.getElementById('copyAlbumBtn');
  if (copyAlbumBtn) {
    copyAlbumBtn.addEventListener('click', function() {
      copyText(v.album_art_prompt, this);
    });
  }
}

// ── Downloads ─────────────────────────────────────────────────────────────
const FILE_LABELS = {
  'report.md': '&#128202; report.md',
  'visual_prompts.md': '&#127912; visual_prompts.md',
};

function renderDownloads(files, jobId) {
  if (!files || !files.length) { hide(downloadBar); return; }

  downloadBar.innerHTML = '<span style="font-size:.72rem;color:var(--text-dim);margin-right:.3rem">다운로드:</span>' +
    files.map(f => {
      const label = FILE_LABELS[f] || ('&#128196; ' + escHtml(f));
      return `<a class="btn-dl" href="/api/download/${jobId}/${encodeURIComponent(f)}" download="${escHtml(f)}">${label}</a>`;
    }).join('');
  show(downloadBar);
}

// ── Tab Switching ─────────────────────────────────────────────────────────
document.addEventListener('click', (e) => {
  const tab = e.target.closest('.tab');
  if (!tab || !tab.dataset.tab) return;
  switchTab(tab.dataset.tab);
});

function switchTab(name) {
  activeTab = name;
  document.querySelectorAll('.tab').forEach(t => t.classList.toggle('active', t.dataset.tab === name));
  document.querySelectorAll('.tab-panel').forEach(p => {
    const isActive = p.id === `tab-${name}`;
    p.classList.toggle('active', isActive);
    p.classList.toggle('hidden', !isActive);
  });
}
