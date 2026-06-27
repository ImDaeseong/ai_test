import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  sceneNum,
  sectionName,
  extractTitle,
  extractBpm,
  extractDuration,
  extractIntensity,
  extractCameraDirection,
  DEFAULT_DURATION_SECONDS,
} from './parsers.mjs';

// ── sceneNum ──────────────────────────────────────────────────────────────────

test('sceneNum: scene_01_intro → 1', () => {
  assert.equal(sceneNum('scene_01_intro'), 1);
});

test('sceneNum: scene_08_outro → 8', () => {
  assert.equal(sceneNum('scene_08_outro'), 8);
});

test('sceneNum: 패턴 불일치 → 999 (정렬 끝으로 밀림)', () => {
  assert.equal(sceneNum('character_reference_prompt'), 999);
});

// ── sectionName ───────────────────────────────────────────────────────────────

test('sectionName: 언더스코어를 공백으로 변환', () => {
  assert.equal(sectionName('scene_01_pre_chorus'), 'pre chorus');
});

test('sectionName: 패턴 불일치 → base 그대로 반환', () => {
  assert.equal(sectionName('character_reference_prompt'), 'character_reference_prompt');
});

// ── extractTitle ──────────────────────────────────────────────────────────────

test('extractTitle: 마크다운 H1 제목 추출', () => {
  assert.equal(extractTitle('# Scene 01 - Intro\n본문'), 'Scene 01 - Intro');
});

test('extractTitle: 제목 없으면 null', () => {
  assert.equal(extractTitle('본문만 있는 경우'), null);
});

// ── extractBpm ────────────────────────────────────────────────────────────────

test('extractBpm: 숫자 BPM 추출', () => {
  assert.equal(extractBpm('90 BPM: measured motion'), 90);
  assert.equal(extractBpm('At 174 BPM, fast driving drums'), 174);
});

test('extractBpm: 대소문자 무관', () => {
  assert.equal(extractBpm('120 bpm'), 120);
});

test('extractBpm: BPM 없으면 null', () => {
  assert.equal(extractBpm('no tempo info'), null);
});

// ── extractDuration ────────────────────────────────────────────────────────────

test('extractDuration: duration_seconds 패턴 추출', () => {
  assert.equal(extractDuration('duration_seconds: 45'), 45);
  assert.equal(extractDuration('duration_seconds = 30.5'), 30.5);
});

test('extractDuration: duration 단위 패턴 추출', () => {
  assert.equal(extractDuration('duration: 20 seconds'), 20);
  assert.equal(extractDuration('duration: 15s'), 15);
});

test('extractDuration: 패턴 없으면 기본값 반환', () => {
  assert.equal(extractDuration('내용 없음'), DEFAULT_DURATION_SECONDS);
});

// ── extractIntensity ──────────────────────────────────────────────────────────

test('extractIntensity: intensity low 추출', () => {
  assert.equal(extractIntensity('intensity low'), 'low');
});

test('extractIntensity: intensity: high 추출', () => {
  assert.equal(extractIntensity('Musical timing: 90 BPM, intensity: high'), 'high');
});

test('extractIntensity: intensity = medium 추출', () => {
  assert.equal(extractIntensity('intensity = medium'), 'medium');
});

test('extractIntensity: emotional peak 추출', () => {
  assert.equal(extractIntensity('intensity emotional peak'), 'emotional peak');
});

test('extractIntensity: 없으면 빈 문자열', () => {
  assert.equal(extractIntensity('no intensity info'), '');
});

// ── extractCameraDirection ────────────────────────────────────────────────────

test('extractCameraDirection: Camera motion: 패턴 추출', () => {
  const content = 'Camera motion: slow push-in that reveals the prop; composition stays wide';
  assert.equal(extractCameraDirection(content), 'slow push-in that reveals the prop');
});

test('extractCameraDirection: Camera direction: 패턴 추출', () => {
  assert.equal(extractCameraDirection('Camera direction: tracking shot follows subject'), 'tracking shot follows subject');
});

test('extractCameraDirection: Camera: 패턴 추출 (짧은 형식)', () => {
  assert.equal(extractCameraDirection('Camera: wide establishing shot'), 'wide establishing shot');
});

test('extractCameraDirection: 없으면 빈 문자열', () => {
  assert.equal(extractCameraDirection('no camera info here'), '');
});
