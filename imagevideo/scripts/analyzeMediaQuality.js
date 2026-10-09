import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {fileURLToPath, pathToFileURL} from 'node:url';
import {createRequire} from 'node:module';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const require = createRequire(import.meta.url);

function installedBinary(packageName, fallback) {
  try {
    return require(packageName).path;
  } catch {
    return fallback;
  }
}

/** Convert ffmpeg detector output into bounded black, silence, and freeze durations. */
export function parseQualityLog(log, durationSeconds) {
  const sum = (pattern) => [...log.matchAll(pattern)].reduce((total, match) => total + Number(match[1]), 0);
  const duration = Math.max(Number(durationSeconds) || 0, 0.001);
  const seconds = {
    black: sum(/black_duration:([0-9.]+)/g),
    silence: sum(/silence_duration:\s*([0-9.]+)/g),
    freeze: sum(/freeze_duration:\s*([0-9.]+)/g)
  };
  return {seconds, ratios: Object.fromEntries(Object.entries(seconds).map(([key, value]) => [key, Math.min(value / duration, 1)]))};
}

/** Classify objective detector findings without pretending to decide artistic merit. */
export function classifyQuality(metrics, policy) {
  const failures = [];
  const warnings = [];
  for (const [kind, limit] of Object.entries(policy.failureRatios ?? {})) {
    if ((metrics.ratios[kind] ?? 0) > limit) failures.push(`${kind} ratio exceeds failure limit ${limit}.`);
  }
  for (const [kind, limit] of Object.entries(policy.warningRatios ?? {})) {
    if ((metrics.ratios[kind] ?? 0) > limit) warnings.push(`${kind} ratio exceeds warning limit ${limit}.`);
  }
  return {status: failures.length ? 'fail' : warnings.length ? 'hold' : 'pass', failures, warnings};
}

function main() {
  const [mediaArg, outputArg] = process.argv.slice(2);
  if (!mediaArg || !outputArg) {
    console.error('Usage: node scripts/analyzeMediaQuality.js <media.mp4> <quality-report.json>');
    process.exitCode = 1;
    return;
  }
  const mediaPath = path.resolve(ROOT, mediaArg);
  const outputPath = path.resolve(ROOT, outputArg);
  const probe = spawnSync(installedBinary('@ffprobe-installer/ffprobe', 'ffprobe'), ['-v', 'error', '-show_entries', 'format=duration', '-of', 'default=nw=1:nk=1', mediaPath], {encoding: 'utf8', shell: false});
  const durationSeconds = Number(probe.stdout?.trim());
  if (probe.status !== 0 || !Number.isFinite(durationSeconds) || durationSeconds <= 0) {
    console.error(probe.error?.message || probe.stderr?.trim() || 'ffprobe could not determine media duration.');
    process.exitCode = 1;
    return;
  }
  const scan = spawnSync(installedBinary('@ffmpeg-installer/ffmpeg', 'ffmpeg'), ['-hide_banner', '-i', mediaPath, '-vf', 'blackdetect=d=0.5:pix_th=0.10,freezedetect=n=-50dB:d=2', '-af', 'silencedetect=n=-50dB:d=2', '-f', 'null', '-'], {encoding: 'utf8', shell: false, maxBuffer: 20 * 1024 * 1024});
  if (scan.status !== 0) {
    console.error(scan.error?.message || scan.stderr?.trim() || 'ffmpeg quality scan failed.');
    process.exitCode = 1;
    return;
  }
  const policy = JSON.parse(fs.readFileSync(path.join(ROOT, 'quality-policy.json'), 'utf8'));
  const metrics = parseQualityLog(scan.stderr, durationSeconds);
  const classification = classifyQuality(metrics, policy);
  const report = {
    schemaVersion: 1,
    mediaPath: path.relative(ROOT, mediaPath).replaceAll('\\', '/'),
    mediaSha256: crypto.createHash('sha256').update(fs.readFileSync(mediaPath)).digest('hex'),
    durationSeconds,
    ...metrics,
    ...classification
  };
  fs.mkdirSync(path.dirname(outputPath), {recursive: true});
  fs.writeFileSync(outputPath, `${JSON.stringify(report, null, 2)}\n`, 'utf8');
  console.log(`Quality analysis ${report.status.toUpperCase()}: ${outputArg}`);
  if (report.status === 'fail') process.exitCode = 1;
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) main();
