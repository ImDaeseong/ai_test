import { test } from 'node:test';
import assert from 'node:assert/strict';
import { validatePlannerInput, validateProductionPlan, ALLOWED_ASPECT_RATIOS } from './validation.js';

// ── validatePlannerInput ───────────────────────────────────────────────────────

test('validatePlannerInput: 유효한 최소 입력 → 오류 없음', () => {
  const errors = validatePlannerInput({ lyrics: '안녕하세요' });
  assert.deepEqual(errors, []);
});

test('validatePlannerInput: null 입력 → 오류 반환', () => {
  const errors = validatePlannerInput(null);
  assert.ok(errors.length > 0);
});

test('validatePlannerInput: 빈 lyrics → 오류 반환', () => {
  const errors = validatePlannerInput({ lyrics: '' });
  assert.ok(errors.some(e => e.includes('lyrics')));
});

test('validatePlannerInput: 허용된 aspect_ratio → 오류 없음', () => {
  for (const ratio of ALLOWED_ASPECT_RATIOS) {
    const errors = validatePlannerInput({ lyrics: '가사', aspect_ratio: ratio });
    assert.deepEqual(errors, []);
  }
});

test('validatePlannerInput: 허용되지 않은 aspect_ratio → 오류 반환', () => {
  const errors = validatePlannerInput({ lyrics: '가사', aspect_ratio: '4:3' });
  assert.ok(errors.some(e => e.includes('aspect_ratio')));
});

test('validatePlannerInput: duration_per_line 0 이하 → 오류 반환', () => {
  const errors = validatePlannerInput({ lyrics: '가사', duration_per_line: 0 });
  assert.ok(errors.some(e => e.includes('duration_per_line')));
});

test('validatePlannerInput: 양수 duration_per_line → 오류 없음', () => {
  const errors = validatePlannerInput({ lyrics: '가사', duration_per_line: 3.5 });
  assert.deepEqual(errors, []);
});

// ── validateProductionPlan ─────────────────────────────────────────────────────

test('validateProductionPlan: null 입력 → 오류 반환', () => {
  const errors = validateProductionPlan(null);
  assert.ok(errors.length > 0);
});

test('validateProductionPlan: segments 없음 → 오류 반환', () => {
  const errors = validateProductionPlan({});
  assert.ok(errors.some(e => e.includes('segments')));
});

test('validateProductionPlan: 유효한 플랜 → 오류 없음', () => {
  const plan = {
    segments: [
      { id: 1, start: '00:00:01.000', end: '00:00:03.000', lyric: '가사' }
    ]
  };
  const errors = validateProductionPlan(plan);
  assert.deepEqual(errors, []);
});

test('validateProductionPlan: ID 순서 오류 → 오류 반환', () => {
  const plan = {
    segments: [
      { id: 2, start: '00:00:01.000', end: '00:00:03.000', lyric: '가사' }
    ]
  };
  const errors = validateProductionPlan(plan);
  assert.ok(errors.some(e => e.includes('sequential')));
});

test('validateProductionPlan: 잘못된 타임스탬프 → 오류 반환', () => {
  const plan = {
    segments: [
      { id: 1, start: 'invalid', end: '00:00:03.000', lyric: '가사' }
    ]
  };
  const errors = validateProductionPlan(plan);
  assert.ok(errors.some(e => e.includes('start')));
});
