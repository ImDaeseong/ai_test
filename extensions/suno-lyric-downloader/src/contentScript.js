(function () {
  'use strict';

  const COVER_SELECTOR = 'img[alt="Song Cover Image"].w-full.h-full';
  const lyricsCache = new Map();

  // ── Styles ───────────────────────────────────────────────────────────────────

  function injectStyles() {
    if (document.getElementById('suno-lyric-dl-styles')) return;
    const s = document.createElement('style');
    s.id = 'suno-lyric-dl-styles';
    s.textContent = `
      .suno-lyric-dl-overlay {
        position: absolute;
        bottom: 12px;
        left: 50%;
        transform: translateX(-50%);
        display: flex;
        gap: 8px;
        z-index: 9999;
        pointer-events: auto;
      }
      .suno-lyric-dl-btn {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        height: 2rem;
        padding: 0 12px;
        border-radius: 999px;
        border: none;
        cursor: pointer;
        font-family: ui-sans-serif, "Segoe UI", system-ui, sans-serif;
        font-size: 0.875rem;
        font-weight: 500;
        line-height: 1;
        color: #fff;
        background: rgba(12, 12, 14, 0.72);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        transition: opacity 0.2s cubic-bezier(0.4,0,0.2,1),
                    transform 0.2s cubic-bezier(0.4,0,0.2,1);
        white-space: nowrap;
        user-select: none;
      }
      .suno-lyric-dl-btn:hover { opacity: 0.85; transform: scale(1.04); }
      .suno-lyric-dl-btn:active { transform: scale(0.97); }
      .suno-lyric-dl-btn:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }
      .suno-lyric-dl-btn svg { width: 0.875rem; height: 0.875rem; flex-shrink: 0; }
    `;
    document.head.appendChild(s);
  }

  const DOWNLOAD_SVG = `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2.2" stroke="currentColor">
    <path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3"/>
  </svg>`;

  // ── Auth ─────────────────────────────────────────────────────────────────────

  function getSessionToken() {
    const m = document.cookie.match(/(?:^|;\s*)__session=([^;]+)/);
    return m ? decodeURIComponent(m[1]) : null;
  }

  function getSongIdFromUrl() {
    const m = location.pathname.match(/^\/song\/([^/?#]+)/);
    return m ? m[1] : null;
  }

  // ── Timing Quality ───────────────────────────────────────────────────────────

  function isValidTime(t) {
    return t != null && typeof t === 'number' && isFinite(t) && t >= 0;
  }

  function calcQuality(timings) {
    let validCount = 0;
    let monotonicBreaks = 0;
    let prev;
    for (const item of timings) {
      if (isValidTime(item.start_s) && isValidTime(item.end_s)) validCount++;
      if (isValidTime(item.start_s)) {
        if (prev != null && item.start_s + 0.001 < prev) monotonicBreaks++;
        prev = item.start_s;
      }
    }
    return { validCount, monotonicBreaks };
  }

  function chooseBestSource(aligned) {
    if (!aligned?.length) return 'lines';

    // words 소스: 라인별 words 배열에서 min(start_s)/max(end_s) 추출
    const wordTimings = aligned.map(l => {
      const starts = (l.words ?? []).map(w => w.start_s).filter(isValidTime);
      const ends   = (l.words ?? []).map(w => w.end_s).filter(isValidTime);
      return starts.length && ends.length
        ? { start_s: Math.min(...starts), end_s: Math.max(...ends) }
        : { start_s: isValidTime(l.start_s) ? l.start_s : undefined,
            end_s:   isValidTime(l.end_s)   ? l.end_s   : undefined };
    });

    // lines 소스: 라인의 start_s/end_s 직접 사용
    const lineTimings = aligned.map(l => ({
      start_s: isValidTime(l.start_s) ? l.start_s : undefined,
      end_s:   isValidTime(l.end_s)   ? l.end_s   : undefined,
    }));

    const total = Math.max(aligned.length, 1);
    const wq = calcQuality(wordTimings);
    const lq = calcQuality(lineTimings);
    const wRatio = wq.validCount / total;
    const lRatio = lq.validCount / total;

    const wGood = wRatio >= 0.7 && wq.monotonicBreaks <= 1;
    const lGood = lRatio >= 0.7 && lq.monotonicBreaks <= 1;

    if (wGood && (!lGood || wq.monotonicBreaks <= lq.monotonicBreaks)) return 'words';
    if (lGood || lRatio >= wRatio) return 'lines';
    return 'words';
  }

  // 섹션 지시어 필터링: [Verse 1: ...], (Chorus), （Instrumental） 등
  function isSectionMarker(text) {
    const t = (text ?? '').replace(/\r/g, '').replace(/[​-‍⁠﻿]/g, '').trim();
    return /^\[.*\]$/.test(t) || /^\(.*\)$/.test(t) || /^（.*）$/.test(t);
  }

  function getLineText(l) {
    // 원본과 동일: text → word → words 배열 join 순서로 텍스트 추출
    const t = typeof l.text === 'string' && l.text
      ? l.text
      : typeof l.word === 'string' && l.word
        ? l.word
        : Array.isArray(l.words) && l.words.length
          ? l.words.map(w => (typeof w.text === 'string' ? w.text : w.word ?? '')).join('')
          : '';
    return t.replace(/\r/g, '').replace(/[​-‍⁠﻿]/g, '').trim();
  }

  function extractLines(aligned, source) {
    // 항상 LINE 단위 텍스트 — words는 타이밍(min start_s / max end_s)에만 활용
    return aligned
      .filter(l => {
        const txt = getLineText(l);
        return txt && !isSectionMarker(txt);
      })
      .map(l => {
        const txt = getLineText(l);
        let start_s, end_s;

        if (source === 'words') {
          const starts = (l.words ?? []).map(w => w.start_s).filter(isValidTime);
          const ends   = (l.words ?? []).map(w => w.end_s).filter(isValidTime);
          if (starts.length && ends.length) {
            start_s = Math.min(...starts);
            end_s   = Math.max(...ends);
          } else {
            start_s = isValidTime(l.start_s) ? l.start_s : undefined;
            end_s   = isValidTime(l.end_s)   ? l.end_s   : undefined;
          }
        } else {
          start_s = isValidTime(l.start_s) ? l.start_s : undefined;
          end_s   = isValidTime(l.end_s)   ? l.end_s   : undefined;
        }

        return { text: txt, start_s, end_s };
      });
  }

  // ── Waveform Timing ──────────────────────────────────────────────────────────

  // 선형 보간 퍼센타일 (원본 f 함수와 동일)
  function calcPercentile(arr, p) {
    if (!arr.length) return 0;
    const sorted = [...arr].sort((a, b) => a - b);
    if (p <= 0) return sorted[0];
    if (p >= 1) return sorted[sorted.length - 1];
    const i = (sorted.length - 1) * p;
    const lo = Math.floor(i), hi = Math.ceil(i), frac = i - lo;
    return sorted[lo] * (1 - frac) + sorted[hi] * frac;
  }

  // 5-point 이동 평균 평탄화
  function smoothWaveform(data) {
    return data.map((_, i) => {
      const lo = Math.max(0, i - 2), hi = Math.min(data.length - 1, i + 2);
      let sum = 0;
      for (let j = lo; j <= hi; j++) sum += data[j];
      return sum / (hi - lo + 1);
    });
  }

  // 누적합 배열에서 target 이상인 첫 인덱스 이진 탐색
  function bisectRight(cumArr, target) {
    let lo = 0, hi = cumArr.length - 1;
    while (lo < hi) {
      const mid = (lo + hi) >> 1;
      cumArr[mid] < target ? (lo = mid + 1) : (hi = mid);
    }
    return lo;
  }

  // 파형 에너지 분포를 이용한 타이밍 배분
  // 원본 알고리즘을 그대로 재현:
  //   1. 5-point 이동 평균 평탄화
  //   2. p20/p85 퍼센타일로 신호 임계값 계산
  //   3. 신호 구간(onset~offset) 탐지 + 앞 0.2s / 뒤 0.3s 버퍼
  //   4. 에너지를 power-law 변환(지수 1.25)으로 비선형 가중치 생성
  //   5. 누적합 + 이진 탐색으로 N개 라인 타임스탬프 생성
  //   6. 최소 간격 0.02s 보장 → 초과 시 비례 스케일링
  function waveformDistribute(lines, waveformData, totalDuration) {
    const N = lines.length;
    if (!N || !waveformData?.length) return null;

    const smoothed = smoothWaveform(waveformData);

    const p20 = calcPercentile(smoothed, 0.2);
    const p85 = calcPercentile(smoothed, 0.85);
    const sigThresh = p20 + (p85 - p20) * 0.22;

    const firstOn = smoothed.findIndex(v => v >= sigThresh);
    const lastOnRev = [...smoothed].reverse().findIndex(v => v >= sigThresh);
    const lastOn = lastOnRev >= 0 ? smoothed.length - 1 - lastOnRev : -1;

    if (firstOn < 0 || lastOn <= firstOn) return null;

    const maxIdx = Math.max(smoothed.length - 1, 1);
    const sps = totalDuration / maxIdx; // 샘플당 초
    const preBuf = Math.min(firstOn, Math.max(1, Math.round(0.2 / Math.max(sps, 1e-6))));
    const postBuf = Math.max(1, Math.round(0.3 / Math.max(sps, 1e-6)));
    const winStart = Math.max(0, firstOn - preBuf);
    const winEnd   = Math.min(smoothed.length - 1, lastOn + postBuf);

    if (winEnd - winStart < 8) return null;

    const slice = smoothed.slice(winStart, winEnd + 1);
    const loThresh  = p20 + (p85 - p20) * 0.15;
    const normRange = Math.max(p85 - loThresh, 1e-6);
    const weights   = slice.map(v => 0.005 + Math.pow(Math.max(v - loThresh, 0) / normRange, 1.25));

    const cumSum = [];
    let totalEnergy = 0;
    for (const w of weights) { totalEnergy += w; cumSum.push(totalEnergy); }
    if (totalEnergy <= 0) return null;

    const maxK   = Math.max(weights.length - 1, 1);
    const startT = (winStart / maxIdx) * totalDuration;
    const endT   = (winEnd   / maxIdx) * totalDuration;

    // E[0] = 시작, E[1..N-1] = 계산된 경계, E[N] = 끝 (강제)
    const E = [startT];
    for (let i = 0; i < N; i++) {
      const target = ((i + 1) / N) * totalEnergy;
      const r       = bisectRight(cumSum, target);
      const prevCum = r > 0 ? cumSum[r - 1] : 0;
      const currCum = cumSum[r];
      const interp  = winStart + Math.min(
        r + (currCum > prevCum ? (target - prevCum) / (currCum - prevCum) : 0),
        maxK
      );
      E.push((interp / maxIdx) * totalDuration);
    }
    E[E.length - 1] = endT;

    // 최소 간격 0.02s 보장
    for (let i = 1; i < E.length; i++) {
      if (E[i] < E[i - 1] + 0.02) E[i] = E[i - 1] + 0.02;
    }

    // 초과 시 비례 스케일 후 다시 최소 간격 보장
    if (E[E.length - 1] > totalDuration) {
      const scale = totalDuration / E[E.length - 1];
      for (let i = 0; i < E.length; i++) E[i] *= scale;
      for (let i = 1; i < E.length; i++) {
        if (E[i] < E[i - 1] + 0.02) E[i] = E[i - 1] + 0.02;
      }
    }

    return lines.map((line, i) => ({
      ...line,
      start_s: +E[i].toFixed(3),
      end_s:   +E[i + 1].toFixed(3),
    }));
  }

  // ── Timing Repair ────────────────────────────────────────────────────────────

  function fillMissingTimings(lines, waveformData, totalDuration) {
    const dur = totalDuration || 180;
    const valid = lines.filter(l => l.text?.trim() && !isSectionMarker(l.text));
    if (!valid.length) return valid;

    const allMissing = valid.every(l => !isValidTime(l.start_s));
    if (allMissing) {
      // 파형 데이터가 있으면 에너지 기반 배분 시도, 없으면 선형 배분
      if (waveformData?.length) {
        const result = waveformDistribute(valid, waveformData, dur);
        if (result) return result;
      }
      const step = dur / valid.length;
      return valid.map((l, i) => ({
        ...l,
        start_s: +(i * step).toFixed(3),
        end_s: +((i + 1) * step).toFixed(3),
      }));
    }

    // Fix monotonic breaks, interpolate gaps
    const result = [...valid];
    let prevTime = 0;

    for (let i = 0; i < result.length; i++) {
      const t = result[i].start_s;
      if (t == null || t < 0) {
        // Find next known anchor
        let nextT = dur;
        let nextIdx = result.length;
        for (let j = i + 1; j < result.length; j++) {
          if (result[j].start_s != null && result[j].start_s >= prevTime) {
            nextT = result[j].start_s;
            nextIdx = j;
            break;
          }
        }
        const gapCount = nextIdx - i;
        const step = (nextT - prevTime) / (gapCount + 1);
        for (let k = 0; k < gapCount; k++) {
          result[i + k] = { ...result[i + k], start_s: +(prevTime + step * (k + 1)).toFixed(3) };
        }
        i = nextIdx - 1;
      } else {
        if (t < prevTime) {
          result[i] = { ...result[i], start_s: +(prevTime + 0.05).toFixed(3) };
        }
        prevTime = result[i].start_s;
      }
    }

    // Fill end_s
    for (let i = 0; i < result.length; i++) {
      const next = result[i + 1]?.start_s;
      if (result[i].end_s == null || result[i].end_s <= result[i].start_s) {
        result[i] = { ...result[i], end_s: +(next ?? result[i].start_s + 3).toFixed(3) };
      }
    }

    return result;
  }

  // ── Format Conversion ────────────────────────────────────────────────────────

  function toTimestampLRC(sec) {
    const s = Math.max(0, sec);
    const m = Math.floor(s / 60).toString().padStart(2, '0');
    const rest = (s % 60).toFixed(2).padStart(5, '0');
    return `${m}:${rest}`;
  }

  function toLRC(lines) {
    return lines
      .filter(l => l.text?.trim() && !isSectionMarker(l.text))
      .map(l => `[${toTimestampLRC(l.start_s)}]${l.text}`)
      .join('\n');
  }

  function toTimestampSRT(sec) {
    const s = Math.max(0, sec);
    const h = Math.floor(s / 3600).toString().padStart(2, '0');
    const m = Math.floor((s % 3600) / 60).toString().padStart(2, '0');
    const ss = Math.floor(s % 60).toString().padStart(2, '0');
    const ms = Math.round((s % 1) * 1000).toString().padStart(3, '0');
    return `${h}:${m}:${ss},${ms}`;
  }

  function toSRT(lines) {
    const filtered = lines.filter(l => l.text?.trim() && !isSectionMarker(l.text));
    return filtered
      .map((l, i) => {
        const start = toTimestampSRT(l.start_s);
        const end = toTimestampSRT(l.end_s ?? filtered[i + 1]?.start_s ?? l.start_s + 3);
        return `${i + 1}\n${start} --> ${end}\n${l.text}`;
      })
      .join('\n\n');
  }

  // ── Download ─────────────────────────────────────────────────────────────────

  function triggerDownload(content, filename) {
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  async function fetchSongData(songId) {
    if (lyricsCache.has(songId)) return lyricsCache.get(songId);

    const token = getSessionToken();
    if (!token) throw new Error('Suno 로그인이 필요합니다.');

    const headers = { Authorization: `Bearer ${token}` };
    const [lyricsRes, clipRes] = await Promise.all([
      fetch(`https://studio-api.prod.suno.com/api/gen/${songId}/aligned_lyrics/v2/`, { headers }),
      fetch(`https://studio-api.prod.suno.com/api/clip/${songId}`, { headers }),
    ]);

    if (!lyricsRes.ok) throw new Error(`가사 API 오류: ${lyricsRes.status}`);
    if (!clipRes.ok) throw new Error(`클립 API 오류: ${clipRes.status}`);

    const lyricsData = await lyricsRes.json();
    const clipData = await clipRes.json();
    const data = { lyricsData, clipData };
    lyricsCache.set(songId, data);
    return data;
  }

  async function download(format, songId, btn) {
    if (btn.disabled) return;
    const spanEl = btn.querySelector('span');
    const origText = spanEl?.textContent ?? format.toUpperCase();

    btn.disabled = true;
    if (spanEl) spanEl.textContent = '...';

    try {
      const { lyricsData, clipData } = await fetchSongData(songId);
      const { aligned_lyrics = [], waveform_data } = lyricsData;
      const duration = clipData.duration_s || 180;
      const rawTitle = clipData.title || clipData.id || songId;
      const safeTitle = rawTitle.replace(/[\\/:*?"<>|]/g, '_').slice(0, 100);

      if (!aligned_lyrics.length) {
        alert('이 노래에는 동기화 가사 데이터가 없습니다.');
        return;
      }

      const source = chooseBestSource(aligned_lyrics);
      const rawLines = extractLines(aligned_lyrics, source);
      const lines = fillMissingTimings(rawLines, waveform_data, duration);

      const content = format === 'lrc' ? toLRC(lines) : toSRT(lines);
      triggerDownload(content, `${safeTitle}.${format}`);
    } catch (err) {
      console.error('[Suno Lyric Downloader]', err);
      alert(`다운로드 실패: ${err.message}`);
    } finally {
      btn.disabled = false;
      if (spanEl) spanEl.textContent = origText;
    }
  }

  // ── UI Injection ─────────────────────────────────────────────────────────────

  function createButton(label, onClickFn) {
    const btn = document.createElement('button');
    btn.className = 'suno-lyric-dl-btn';
    btn.innerHTML = `${DOWNLOAD_SVG}<span>${label}</span>`;
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      onClickFn(btn);
    });
    return btn;
  }

  function injectButtons(coverImg) {
    if (coverImg.dataset.sunoLyricDlInjected) return;

    const songId = getSongIdFromUrl();
    if (!songId) return;

    coverImg.dataset.sunoLyricDlInjected = '1';

    const wrapper = coverImg.parentElement;
    if (!wrapper) return;

    const pos = getComputedStyle(wrapper).position;
    if (pos === 'static' || !pos) wrapper.style.position = 'relative';

    wrapper.querySelector('.suno-lyric-dl-overlay')?.remove();

    const overlay = document.createElement('div');
    overlay.className = 'suno-lyric-dl-overlay';
    overlay.appendChild(createButton('LRC', (btn) => download('lrc', songId, btn)));
    overlay.appendChild(createButton('SRT', (btn) => download('srt', songId, btn)));
    wrapper.appendChild(overlay);
  }

  function scanAndInject() {
    injectStyles();
    document.querySelectorAll(COVER_SELECTOR).forEach(injectButtons);
  }

  // ── Observer ─────────────────────────────────────────────────────────────────

  let observer = null;

  function startObserver() {
    observer?.disconnect();
    observer = new MutationObserver(scanAndInject);
    observer.observe(document.body, { childList: true, subtree: true });
    scanAndInject();
  }

  // ── Message Listener ─────────────────────────────────────────────────────────

  chrome.runtime.onMessage.addListener((msg) => {
    if (msg.action === 'URL_CHANGED') {
      lyricsCache.delete(msg.songId);
      // Reset injected markers so buttons re-inject for the new song
      document.querySelectorAll('[data-suno-lyric-dl-injected]').forEach(el => {
        delete el.dataset.sunoLyricDlInjected;
        el.parentElement?.querySelector('.suno-lyric-dl-overlay')?.remove();
      });
      setTimeout(scanAndInject, 600);
    } else if (msg.action === 'FIND_BUTTONS') {
      scanAndInject();
    }
  });

  startObserver();
})();
