import {spawnSync} from 'node:child_process';

const MIN_BPM = 60;
const MAX_BPM = 200;

function roundTime(value) {
  return Number(value.toFixed(4));
}

/** Measures a steady beat grid from mono PCM samples. */
export function analyzePcmSamples(samples, sampleRate) {
  if (!(samples instanceof Float32Array) || samples.length === 0 || sampleRate <= 0) {
    throw new Error('Beat analysis failed: invalid PCM input.');
  }

  const hopSize = Math.max(1, Math.round(sampleRate * 0.01));
  const envelope = [];
  let previousEnergy = 0;
  for (let start = 0; start < samples.length; start += hopSize) {
    let energy = 0;
    const end = Math.min(samples.length, start + hopSize);
    for (let index = start; index < end; index += 1) {
      energy += Math.abs(samples[index]);
    }
    energy /= Math.max(1, end - start);
    envelope.push(Math.max(0, energy - previousEnergy));
    previousEnergy = energy;
  }

  let peak = 0;
  for (const value of envelope) peak = Math.max(peak, value);
  if (!Number.isFinite(peak) || peak < 1e-6) {
    throw new Error('Beat analysis failed: no usable onsets detected.');
  }

  const minLag = Math.max(1, Math.floor((60 / MAX_BPM) / 0.01));
  const maxLag = Math.min(envelope.length - 1, Math.ceil((60 / MIN_BPM) / 0.01));
  const envelopeMean = envelope.reduce((sum, value) => sum + value, 0) / envelope.length;
  const centeredEnvelope = envelope.map((value) => value - envelopeMean);
  const scores = [];
  let bestScore = -Infinity;
  for (let lag = minLag; lag <= maxLag; lag += 1) {
    let numerator = 0;
    let leftEnergy = 0;
    let rightEnergy = 0;
    for (let index = lag; index < envelope.length; index += 1) {
      const left = centeredEnvelope[index];
      const right = centeredEnvelope[index - lag];
      numerator += left * right;
      leftEnergy += left * left;
      rightEnergy += right * right;
    }
    const score = numerator / Math.max(Number.EPSILON, Math.sqrt(leftEnergy * rightEnergy));
    scores.push({lag, score});
    bestScore = Math.max(bestScore, score);
  }

  if (!(bestScore >= 0.2)) {
    throw new Error('Beat analysis failed: no periodic onset pattern detected.');
  }

  const selected = scores.find(({score}) => score >= bestScore * 0.98);
  const periodFrames = selected.lag;
  const periodSeconds = periodFrames * 0.01;
  const bpm = 60 / periodSeconds;

  let bestPhase = 0;
  let bestPhaseScore = -Infinity;
  for (let phase = 0; phase < periodFrames; phase += 1) {
    let score = 0;
    for (let index = phase; index < envelope.length; index += periodFrames) {
      score += envelope[index];
    }
    if (score > bestPhaseScore) {
      bestPhase = phase;
      bestPhaseScore = score;
    }
  }

  const durationSeconds = samples.length / sampleRate;
  const firstBeatSeconds = bestPhase * 0.01;
  const beatTimes = [];
  for (let time = firstBeatSeconds; time < durationSeconds; time += periodSeconds) {
    beatTimes.push(roundTime(time));
  }

  return {
    bpm: Number(bpm.toFixed(2)),
    first_beat_seconds: roundTime(firstBeatSeconds),
    beat_times_seconds: beatTimes,
    duration_seconds: roundTime(durationSeconds),
    confidence: Number(bestScore.toFixed(3)),
    method: 'pcm-onset-autocorrelation-v1',
  };
}

/** Decodes an audio file with ffmpeg and measures its steady beat grid. */
export function analyzeAudioFile(audioPath, {sampleRate = 22050, spawn = spawnSync} = {}) {
  const result = spawn(
    'ffmpeg',
    ['-v', 'error', '-i', audioPath, '-ac', '1', '-ar', String(sampleRate), '-f', 'f32le', 'pipe:1'],
    {encoding: null, maxBuffer: 512 * 1024 * 1024, shell: false},
  );

  if (result.error) {
    throw new Error(`Beat analysis failed: ffmpeg could not start (${result.error.message}).`);
  }
  if (result.status !== 0) {
    const detail = result.stderr?.toString('utf8').trim() || `exit ${result.status}`;
    throw new Error(`Beat analysis failed: ffmpeg decode error (${detail}).`);
  }
  if (!result.stdout || result.stdout.length < 4) {
    throw new Error('Beat analysis failed: ffmpeg returned no PCM audio.');
  }

  const view = new Float32Array(
    result.stdout.buffer,
    result.stdout.byteOffset,
    Math.floor(result.stdout.byteLength / 4),
  );
  return analyzePcmSamples(new Float32Array(view), sampleRate);
}
