import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  isValidTime,
  calcQuality,
  chooseBestSource,
  isSectionMarker,
  getLineText,
  calcPercentile,
  smoothWaveform,
  bisectRight,
} from './lyricUtils.js';

// ── isValidTime ───────────────────────────────────────────────────────────────

test('isValidTime: 양수 유한 숫자 → true', () => {
  assert.equal(isValidTime(0), true);
  assert.equal(isValidTime(1.5), true);
  assert.equal(isValidTime(100), true);
});

test('isValidTime: null/undefined/NaN/Infinity/음수 → false', () => {
  assert.equal(isValidTime(null), false);
  assert.equal(isValidTime(undefined), false);
  assert.equal(isValidTime(NaN), false);
  assert.equal(isValidTime(Infinity), false);
  assert.equal(isValidTime(-1), false);
});

// ── calcQuality ───────────────────────────────────────────────────────────────

test('calcQuality: 유효한 타이밍 → validCount 카운트', () => {
  const timings = [
    { start_s: 0, end_s: 1 },
    { start_s: 1, end_s: 2 },
    { start_s: 2, end_s: 3 },
  ];
  const { validCount, monotonicBreaks } = calcQuality(timings);
  assert.equal(validCount, 3);
  assert.equal(monotonicBreaks, 0);
});

test('calcQuality: 역방향 타임스탬프 → monotonicBreaks 감지', () => {
  const timings = [
    { start_s: 5, end_s: 6 },
    { start_s: 1, end_s: 2 },
  ];
  const { monotonicBreaks } = calcQuality(timings);
  assert.equal(monotonicBreaks, 1);
});

test('calcQuality: 빈 배열 → 0/0', () => {
  const { validCount, monotonicBreaks } = calcQuality([]);
  assert.equal(validCount, 0);
  assert.equal(monotonicBreaks, 0);
});

// ── chooseBestSource ──────────────────────────────────────────────────────────

test('chooseBestSource: 빈 배열 → lines', () => {
  assert.equal(chooseBestSource([]), 'lines');
  assert.equal(chooseBestSource(null), 'lines');
});

test('chooseBestSource: words 없으면 line 타임스탬프 fallback → words 우선 반환', () => {
  const aligned = Array.from({ length: 5 }, (_, i) => ({
    start_s: i,
    end_s: i + 1,
    text: `line ${i}`,
  }));
  assert.equal(chooseBestSource(aligned), 'words');
});

test('chooseBestSource: word 타임스탬프 순서 이상 > line 순서 정상 → lines 반환', () => {
  // word timestamps에 단조성 위반이 많아 line이 더 좋은 케이스
  const aligned = [
    { start_s: 0, end_s: 1, words: [{ start_s: 0, end_s: 0.5 }] },
    { start_s: 1, end_s: 2, words: [{ start_s: 2, end_s: 2.5 }] },
    { start_s: 2, end_s: 3, words: [{ start_s: 1, end_s: 1.5 }] }, // word 역방향
    { start_s: 3, end_s: 4, words: [{ start_s: 3, end_s: 3.5 }] },
    { start_s: 4, end_s: 5, words: [{ start_s: 4, end_s: 4.5 }] },
  ];
  assert.equal(chooseBestSource(aligned), 'lines');
});

test('chooseBestSource: words 타임스탬프가 더 좋으면 words 반환', () => {
  const aligned = Array.from({ length: 5 }, (_, i) => ({
    start_s: undefined,
    end_s: undefined,
    text: `line ${i}`,
    words: [{ start_s: i, end_s: i + 0.5 }, { start_s: i + 0.5, end_s: i + 1 }],
  }));
  assert.equal(chooseBestSource(aligned), 'words');
});

// ── isSectionMarker ───────────────────────────────────────────────────────────

test('isSectionMarker: [Chorus] → true', () => {
  assert.equal(isSectionMarker('[Chorus]'), true);
  assert.equal(isSectionMarker('[Verse 1]'), true);
});

test('isSectionMarker: (Instrumental) → true', () => {
  assert.equal(isSectionMarker('(Instrumental)'), true);
});

test('isSectionMarker: 일반 가사 → false', () => {
  assert.equal(isSectionMarker('안녕하세요'), false);
  assert.equal(isSectionMarker('I love you'), false);
});

// ── getLineText ───────────────────────────────────────────────────────────────

test('getLineText: text 필드 우선 반환', () => {
  assert.equal(getLineText({ text: '안녕', word: '다른값' }), '안녕');
});

test('getLineText: text 없으면 word 반환', () => {
  assert.equal(getLineText({ word: '반갑습니다' }), '반갑습니다');
});

test('getLineText: words 배열에서 텍스트 join', () => {
  const l = { words: [{ text: '안' }, { text: '녕' }] };
  assert.equal(getLineText(l), '안녕');
});

test('getLineText: 빈 객체 → 빈 문자열', () => {
  assert.equal(getLineText({}), '');
});

// ── calcPercentile ────────────────────────────────────────────────────────────

test('calcPercentile: 빈 배열 → 0', () => {
  assert.equal(calcPercentile([], 0.5), 0);
});

test('calcPercentile: p=0 → 최솟값', () => {
  assert.equal(calcPercentile([3, 1, 2], 0), 1);
});

test('calcPercentile: p=1 → 최댓값', () => {
  assert.equal(calcPercentile([3, 1, 2], 1), 3);
});

test('calcPercentile: p=0.5 → 중앙값 (선형 보간)', () => {
  assert.equal(calcPercentile([1, 2, 3], 0.5), 2);
});

// ── smoothWaveform ────────────────────────────────────────────────────────────

test('smoothWaveform: 길이 유지', () => {
  const data = [1, 2, 3, 4, 5];
  assert.equal(smoothWaveform(data).length, 5);
});

test('smoothWaveform: 단일 값 → 그대로 반환', () => {
  assert.deepEqual(smoothWaveform([7]), [7]);
});

test('smoothWaveform: 5-point 이동 평균 (중간 값)', () => {
  const data = [0, 0, 10, 0, 0];
  const result = smoothWaveform(data);
  assert.equal(result[2], 2);
});

// ── bisectRight ───────────────────────────────────────────────────────────────

test('bisectRight: target 이상인 첫 인덱스 반환', () => {
  assert.equal(bisectRight([1, 3, 5, 7], 3), 1);
  assert.equal(bisectRight([1, 3, 5, 7], 4), 2);
});

test('bisectRight: target이 모든 값보다 크면 마지막 인덱스', () => {
  assert.equal(bisectRight([1, 2, 3], 10), 2);
});

test('bisectRight: target이 모든 값보다 작으면 0', () => {
  assert.equal(bisectRight([5, 6, 7], 0), 0);
});
