import { test } from 'node:test';
import assert from 'node:assert/strict';
import { parseLrc, parseSrt, parseLyrics } from './parsers.js';

// ── parseLrc ──────────────────────────────────────────────────────────────────

const LRC_BASIC = `[00:01.00]첫 번째 가사
[00:04.50]두 번째 가사
[00:08.00]세 번째 가사
`;

test('parseLrc: 기본 파싱 — 3개 라인 반환', () => {
  const result = parseLrc(LRC_BASIC);
  assert.equal(result.lines.length, 3);
  assert.equal(result.source, 'lrc');
});

test('parseLrc: lyric 텍스트 추출', () => {
  const { lines } = parseLrc(LRC_BASIC);
  assert.equal(lines[0].text, '첫 번째 가사');
  assert.equal(lines[1].text, '두 번째 가사');
});

test('parseLrc: start 타임 정확성 (초 단위)', () => {
  const { lines } = parseLrc(LRC_BASIC);
  assert.equal(lines[0].start, 1.0);
  assert.equal(lines[1].start, 4.5);
});

test('parseLrc: end ≥ start + 0.35', () => {
  const { lines } = parseLrc(LRC_BASIC);
  for (const line of lines) {
    assert.ok(line.end >= line.start + 0.35, `end(${line.end}) should be >= start(${line.start}) + 0.35`);
  }
});

test('parseLrc: durationSeconds는 마지막 end 이상', () => {
  const result = parseLrc(LRC_BASIC);
  const maxEnd = Math.max(...result.lines.map(l => l.end));
  assert.ok(result.durationSeconds >= maxEnd);
});

test('parseLrc: BOM 제거 후 정상 파싱', () => {
  const lrc = '﻿[00:01.00]BOM 가사\n';
  const { lines } = parseLrc(lrc);
  assert.equal(lines.length, 1);
  assert.equal(lines[0].text, 'BOM 가사');
});

test('parseLrc: 빈 입력 → 빈 lines', () => {
  const { lines } = parseLrc('');
  assert.equal(lines.length, 0);
});

// ── parseSrt ──────────────────────────────────────────────────────────────────

const SRT_BASIC = `1
00:00:01,000 --> 00:00:03,000
안녕하세요

2
00:00:04,000 --> 00:00:06,500
반갑습니다
`;

test('parseSrt: 기본 파싱 — 2개 라인 반환', () => {
  const result = parseSrt(SRT_BASIC);
  assert.equal(result.lines.length, 2);
  assert.equal(result.source, 'srt');
});

test('parseSrt: start/end 타임 정확성', () => {
  const { lines } = parseSrt(SRT_BASIC);
  assert.equal(lines[0].start, 1.0);
  assert.equal(lines[0].end, 3.0);
});

test('parseSrt: lyric 텍스트 추출', () => {
  const { lines } = parseSrt(SRT_BASIC);
  assert.equal(lines[0].text, '안녕하세요');
  assert.equal(lines[1].text, '반갑습니다');
});

test('parseSrt: durationSeconds는 최소 10초 이상', () => {
  const result = parseSrt(SRT_BASIC);
  assert.ok(result.durationSeconds >= 10);
});

test('parseSrt: 빈 입력 → 빈 lines', () => {
  const { lines } = parseSrt('');
  assert.equal(lines.length, 0);
});

// ── parseLyrics ────────────────────────────────────────────────────────────────

test('parseLyrics: LRC 우선 파싱', () => {
  const result = parseLyrics({ lrc: LRC_BASIC, srt: SRT_BASIC });
  assert.equal(result.source, 'lrc');
});

test('parseLyrics: LRC 없으면 SRT 파싱', () => {
  const result = parseLyrics({ srt: SRT_BASIC });
  assert.equal(result.source, 'srt');
});

test('parseLyrics: LRC가 빈 문자열이면 SRT로 폴백', () => {
  const result = parseLyrics({ lrc: '', srt: SRT_BASIC });
  assert.equal(result.source, 'srt');
});

test('parseLyrics: 둘 다 없으면 예외 발생', () => {
  assert.throws(() => parseLyrics({}), /No timed lyric lines/);
});
