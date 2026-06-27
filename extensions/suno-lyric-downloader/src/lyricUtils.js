/**
 * lyricUtils.js — contentScript.js 내 순수 함수 추출본
 *
 * contentScript.js는 Chrome 확장 IIFE 구조로 번들링 없이 직접 배포되므로
 * ES module import를 사용할 수 없다. 이 파일은 동일 로직을 단위 테스트 가능한
 * ES 모듈로 분리한 것이다. contentScript.js의 해당 함수를 변경할 때
 * 이 파일도 함께 업데이트해야 한다.
 */

export function isValidTime(t) {
  return t != null && typeof t === 'number' && isFinite(t) && t >= 0;
}

export function calcQuality(timings) {
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

export function chooseBestSource(aligned) {
  if (!aligned?.length) return 'lines';

  const wordTimings = aligned.map(l => {
    const starts = (l.words ?? []).map(w => w.start_s).filter(isValidTime);
    const ends   = (l.words ?? []).map(w => w.end_s).filter(isValidTime);
    return starts.length && ends.length
      ? { start_s: Math.min(...starts), end_s: Math.max(...ends) }
      : { start_s: isValidTime(l.start_s) ? l.start_s : undefined,
          end_s:   isValidTime(l.end_s)   ? l.end_s   : undefined };
  });

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

export function isSectionMarker(text) {
  const t = (text ?? '').replace(/\r/g, '').replace(/[​-‍⁠﻿]/g, '').trim();
  return /^\[.*\]$/.test(t) || /^\(.*\)$/.test(t) || /^（.*）$/.test(t);
}

export function getLineText(l) {
  const t = typeof l.text === 'string' && l.text
    ? l.text
    : typeof l.word === 'string' && l.word
      ? l.word
      : Array.isArray(l.words) && l.words.length
        ? l.words.map(w => (typeof w.text === 'string' ? w.text : w.word ?? '')).join('')
        : '';
  return t.replace(/\r/g, '').replace(/[​-‍⁠﻿]/g, '').trim();
}

export function calcPercentile(arr, p) {
  if (!arr.length) return 0;
  const sorted = [...arr].sort((a, b) => a - b);
  if (p <= 0) return sorted[0];
  if (p >= 1) return sorted[sorted.length - 1];
  const i = (sorted.length - 1) * p;
  const lo = Math.floor(i), hi = Math.ceil(i), frac = i - lo;
  return sorted[lo] * (1 - frac) + sorted[hi] * frac;
}

export function smoothWaveform(data) {
  return data.map((_, i) => {
    const lo = Math.max(0, i - 2), hi = Math.min(data.length - 1, i + 2);
    let sum = 0;
    for (let j = lo; j <= hi; j++) sum += data[j];
    return sum / (hi - lo + 1);
  });
}

export function bisectRight(cumArr, target) {
  let lo = 0, hi = cumArr.length - 1;
  while (lo < hi) {
    const mid = (lo + hi) >> 1;
    cumArr[mid] < target ? (lo = mid + 1) : (hi = mid);
  }
  return lo;
}
