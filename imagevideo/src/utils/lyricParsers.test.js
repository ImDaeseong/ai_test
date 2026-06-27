import { test } from 'node:test';
import assert from 'node:assert/strict';
import { parseSrt, parseLrc } from './lyricParsers.js';

// ── parseSrt ──────────────────────────────────────────────────────────────────

const SRT_BASIC = `1
00:00:01,000 --> 00:00:03,000
안녕하세요

2
00:00:04,000 --> 00:00:06,500
반갑습니다
`;

test('parseSrt: 기본 파싱 — 2개 세그먼트 반환', () => {
  const segments = parseSrt(SRT_BASIC);
  assert.equal(segments.length, 2);
});

test('parseSrt: start/end 타임스탬프 형식 확인', () => {
  const [seg] = parseSrt(SRT_BASIC);
  assert.match(seg.start, /^\d{2}:\d{2}:\d{2}\.\d{3}$/);
  assert.match(seg.end, /^\d{2}:\d{2}:\d{2}\.\d{3}$/);
});

test('parseSrt: lyric 텍스트 추출', () => {
  const segments = parseSrt(SRT_BASIC);
  assert.equal(segments[0].lyric, '안녕하세요');
  assert.equal(segments[1].lyric, '반갑습니다');
});

test('parseSrt: duration 계산 (end - start)', () => {
  const [seg] = parseSrt(SRT_BASIC);
  assert.equal(seg.duration, 2);
});

test('parseSrt: 빈 문자열 → 빈 배열', () => {
  assert.deepEqual(parseSrt(''), []);
});

test('parseSrt: end ≤ start 세그먼트 건너뜀', () => {
  const invalid = `1
00:00:05,000 --> 00:00:03,000
역방향
`;
  assert.deepEqual(parseSrt(invalid), []);
});

// ── parseLrc ──────────────────────────────────────────────────────────────────

const LRC_BASIC = `[00:01.00]첫 번째 가사
[00:04.50]두 번째 가사
[00:08.00]세 번째 가사
`;

test('parseLrc: 기본 파싱 — 3개 세그먼트 반환', () => {
  const segments = parseLrc(LRC_BASIC);
  assert.equal(segments.length, 3);
});

test('parseLrc: lyric 텍스트 추출', () => {
  const segments = parseLrc(LRC_BASIC);
  assert.equal(segments[0].lyric, '첫 번째 가사');
  assert.equal(segments[1].lyric, '두 번째 가사');
});

test('parseLrc: start 타임스탬프 형식 확인', () => {
  const [seg] = parseLrc(LRC_BASIC);
  assert.match(seg.start, /^\d{2}:\d{2}:\d{2}\.\d{3}$/);
});

test('parseLrc: end는 다음 start와 같거나 최소 0.25초 이후', () => {
  const [first, second] = parseLrc(LRC_BASIC);
  assert.ok(first.duration >= 0.25);
  assert.equal(second.start, first.end);
});

test('parseLrc: 빈 문자열 → 빈 배열', () => {
  assert.deepEqual(parseLrc(''), []);
});

test('parseLrc: 메타데이터 태그([ar:...]) 건너뜀', () => {
  const lrc = `[ar:Artist]
[al:Album]
[00:01.00]실제 가사
`;
  const segments = parseLrc(lrc);
  assert.equal(segments.length, 1);
  assert.equal(segments[0].lyric, '실제 가사');
});

test('parseLrc: BOM 제거 후 파싱', () => {
  const lrc = '﻿[00:01.00]BOM 포함 가사\n';
  const segments = parseLrc(lrc);
  assert.equal(segments.length, 1);
  assert.equal(segments[0].lyric, 'BOM 포함 가사');
});
