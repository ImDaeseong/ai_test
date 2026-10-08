import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {analyzeAudioFile, analyzePcmSamples} from './audio_analysis.mjs';

const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

function pulseTrain({sampleRate, durationSeconds, bpm, firstBeatSeconds}) {
  const samples = new Float32Array(sampleRate * durationSeconds);
  const beatInterval = 60 / bpm;
  for (let beat = firstBeatSeconds; beat < durationSeconds; beat += beatInterval) {
    const start = Math.round(beat * sampleRate);
    const length = Math.round(sampleRate * 0.02);
    for (let index = 0; index < length && start + index < samples.length; index += 1) {
      samples[start + index] = 1 - index / length;
    }
  }
  return samples;
}

function writeMonoWav(file, samples, sampleRate) {
  const dataSize = samples.length * 2;
  const wav = Buffer.alloc(44 + dataSize);
  wav.write('RIFF', 0);
  wav.writeUInt32LE(36 + dataSize, 4);
  wav.write('WAVEfmt ', 8);
  wav.writeUInt32LE(16, 16);
  wav.writeUInt16LE(1, 20);
  wav.writeUInt16LE(1, 22);
  wav.writeUInt32LE(sampleRate, 24);
  wav.writeUInt32LE(sampleRate * 2, 28);
  wav.writeUInt16LE(2, 32);
  wav.writeUInt16LE(16, 34);
  wav.write('data', 36);
  wav.writeUInt32LE(dataSize, 40);
  for (let index = 0; index < samples.length; index += 1) {
    wav.writeInt16LE(Math.round(Math.max(-1, Math.min(1, samples[index])) * 32767), 44 + index * 2);
  }
  fs.writeFileSync(file, wav);
}

test('analyzePcmSamples measures tempo and first beat from audio samples', () => {
  const sampleRate = 4000;
  const result = analyzePcmSamples(
    pulseTrain({sampleRate, durationSeconds: 8, bpm: 120, firstBeatSeconds: 0.25}),
    sampleRate,
  );

  assert.ok(Math.abs(result.bpm - 120) <= 1, `measured BPM: ${result.bpm}`);
  assert.ok(
    Math.abs(result.first_beat_seconds - 0.25) <= 0.03,
    `first beat: ${result.first_beat_seconds}`,
  );
  assert.ok(result.beat_times_seconds.length >= 14);
  assert.ok(
    result.beat_times_seconds.every((value, index, values) => index === 0 || value > values[index - 1]),
  );
});

test('analyzePcmSamples rejects silence instead of inventing a tempo', () => {
  assert.throws(
    () => analyzePcmSamples(new Float32Array(4000 * 4), 4000),
    /beat analysis failed/i,
  );
});

test('analyzePcmSamples rejects deterministic non-periodic noise', () => {
  const samples = new Float32Array(4000 * 8);
  let state = 0x12345678;
  for (let index = 0; index < samples.length; index += 1) {
    state = (1664525 * state + 1013904223) >>> 0;
    samples[index] = (state / 0xffffffff) * 2 - 1;
  }
  assert.throws(() => analyzePcmSamples(samples, 4000), /periodic onset pattern/i);
});

test('analyzeAudioFile decodes a real WAV through ffmpeg', () => {
  const folder = fs.mkdtempSync(path.join(os.tmpdir(), 'ai-anime-beat-'));
  const audioFile = path.join(folder, 'click.wav');
  try {
    const sampleRate = 4000;
    writeMonoWav(
      audioFile,
      pulseTrain({sampleRate, durationSeconds: 8, bpm: 120, firstBeatSeconds: 0.25}),
      sampleRate,
    );
    const result = analyzeAudioFile(audioFile, {sampleRate});
    assert.ok(Math.abs(result.bpm - 120) <= 1, `measured BPM: ${result.bpm}`);
    assert.ok(Math.abs(result.first_beat_seconds - 0.25) <= 0.03);
  } finally {
    fs.rmSync(folder, {recursive: true, force: true});
  }
});

test('import_input prefers measured audio beats over prompt BPM', () => {
  const fixtureRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'ai-anime-import-'));
  try {
    fs.cpSync(path.join(projectRoot, 'scripts'), path.join(fixtureRoot, 'scripts'), {recursive: true});
    fs.mkdirSync(path.join(fixtureRoot, 'input'), {recursive: true});
    fs.writeFileSync(path.join(fixtureRoot, 'input', 'scene_01_intro.png'), 'fixture');
    fs.writeFileSync(
      path.join(fixtureRoot, 'input', 'scene_01_intro.md'),
      '# Intro\nDuration: 8 seconds\nRhythm: 90 BPM\nIntensity: low\n',
    );
    const sampleRate = 4000;
    writeMonoWav(
      path.join(fixtureRoot, 'input', 'song.wav'),
      pulseTrain({sampleRate, durationSeconds: 8, bpm: 120, firstBeatSeconds: 0.25}),
      sampleRate,
    );

    const run = spawnSync(process.execPath, [path.join(fixtureRoot, 'scripts', 'import_input.mjs')], {
      cwd: fixtureRoot,
      encoding: 'utf8',
      shell: false,
    });
    assert.equal(run.status, 0, `${run.stdout}\n${run.stderr}`);

    const source = JSON.parse(
      fs.readFileSync(path.join(fixtureRoot, 'manifests', 'source', 'song_master.json'), 'utf8'),
    );
    const manifest = JSON.parse(
      fs.readFileSync(path.join(fixtureRoot, 'manifests', 'render_manifest.json'), 'utf8'),
    );
    assert.equal(source.bpm_source, 'audio-analysis');
    assert.ok(Math.abs(source.bpm - 120) <= 1);
    assert.equal(source.audio_files[0].file, 'song.wav');
    assert.ok(source.audio_analysis.beat_times_seconds.length >= 14);
    assert.equal(manifest.bpm_source, 'audio-analysis');
    assert.deepEqual(manifest.beat_times_seconds, source.audio_analysis.beat_times_seconds);
    assert.equal(manifest.audio, 'assets/audio/song.wav');
  } finally {
    fs.rmSync(fixtureRoot, {recursive: true, force: true});
  }
});

test('import_input rejects multiple audio files before analysis', () => {
  const fixtureRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'ai-anime-multi-audio-'));
  try {
    fs.cpSync(path.join(projectRoot, 'scripts'), path.join(fixtureRoot, 'scripts'), {recursive: true});
    fs.mkdirSync(path.join(fixtureRoot, 'input'), {recursive: true});
    fs.writeFileSync(path.join(fixtureRoot, 'input', 'scene_01_intro.png'), 'fixture');
    fs.writeFileSync(path.join(fixtureRoot, 'input', 'scene_01_intro.md'), '# Intro\n');
    fs.writeFileSync(path.join(fixtureRoot, 'input', 'one.wav'), 'fixture');
    fs.writeFileSync(path.join(fixtureRoot, 'input', 'two.mp3'), 'fixture');

    const run = spawnSync(process.execPath, [path.join(fixtureRoot, 'scripts', 'import_input.mjs')], {
      cwd: fixtureRoot,
      encoding: 'utf8',
      shell: false,
    });
    assert.equal(run.status, 1);
    assert.match(run.stderr, /Only one input audio file is allowed/);
  } finally {
    fs.rmSync(fixtureRoot, {recursive: true, force: true});
  }
});

test('import_input rejects audio and scene duration mismatch', () => {
  const fixtureRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'ai-anime-duration-'));
  try {
    fs.cpSync(path.join(projectRoot, 'scripts'), path.join(fixtureRoot, 'scripts'), {recursive: true});
    fs.mkdirSync(path.join(fixtureRoot, 'input'), {recursive: true});
    fs.writeFileSync(path.join(fixtureRoot, 'input', 'scene_01_intro.png'), 'fixture');
    fs.writeFileSync(
      path.join(fixtureRoot, 'input', 'scene_01_intro.md'),
      '# Intro\nDuration: 4 seconds\nRhythm: 90 BPM\n',
    );
    writeMonoWav(
      path.join(fixtureRoot, 'input', 'song.wav'),
      pulseTrain({sampleRate: 4000, durationSeconds: 8, bpm: 120, firstBeatSeconds: 0.25}),
      4000,
    );

    const run = spawnSync(process.execPath, [path.join(fixtureRoot, 'scripts', 'import_input.mjs')], {
      cwd: fixtureRoot,
      encoding: 'utf8',
      shell: false,
    });
    assert.equal(run.status, 1);
    assert.match(run.stderr, /audio duration .* does not match scene duration/i);
  } finally {
    fs.rmSync(fixtureRoot, {recursive: true, force: true});
  }
});
