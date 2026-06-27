import { test } from 'node:test';
import assert from 'node:assert/strict';
import { formatTimestamp, isValidTimestamp } from './timecode.js';

test('formatTimestamp: 0초 → 00:00:00.000', () => {
  assert.equal(formatTimestamp(0), '00:00:00.000');
});

test('formatTimestamp: 정수 초 변환', () => {
  assert.equal(formatTimestamp(60), '00:01:00.000');
  assert.equal(formatTimestamp(3600), '01:00:00.000');
  assert.equal(formatTimestamp(3661), '01:01:01.000');
});

test('formatTimestamp: 소수점 초 (밀리초 반영)', () => {
  assert.equal(formatTimestamp(1.5), '00:00:01.500');
  assert.equal(formatTimestamp(0.001), '00:00:00.001');
  assert.equal(formatTimestamp(59.999), '00:00:59.999');
});

test('formatTimestamp: 음수 입력 시 예외 발생', () => {
  assert.throws(() => formatTimestamp(-1), /Invalid timestamp/);
});

test('formatTimestamp: NaN 입력 시 예외 발생', () => {
  assert.throws(() => formatTimestamp(NaN), /Invalid timestamp/);
});

test('isValidTimestamp: 올바른 형식 통과', () => {
  assert.equal(isValidTimestamp('00:00:00.000'), true);
  assert.equal(isValidTimestamp('01:23:45.678'), true);
  assert.equal(isValidTimestamp('99:59:59.999'), true);
});

test('isValidTimestamp: 잘못된 형식 거부', () => {
  assert.equal(isValidTimestamp('invalid'), false);
  assert.equal(isValidTimestamp('1:00:00.000'), false);
  assert.equal(isValidTimestamp('00:00:00'), false);
  assert.equal(isValidTimestamp(''), false);
  assert.equal(isValidTimestamp(null), false);
});

test('isValidTimestamp: 범위 초과 거부 (분/초 ≥ 60)', () => {
  assert.equal(isValidTimestamp('00:60:00.000'), false);
  assert.equal(isValidTimestamp('00:00:60.000'), false);
});
