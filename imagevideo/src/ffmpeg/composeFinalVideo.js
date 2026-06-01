import fs from 'node:fs/promises';
import {accessSync} from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import {spawn} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {discoverInputFiles} from '../utils/inputDiscovery.js';

const DEFAULT_VIDEO = 'output/rendered_typography_video.mp4';
const DEFAULT_SUBTITLES = 'output/subtitles.ass';
const DEFAULT_OUTPUT = 'output/lyric_video.mp4';
const DEFAULT_LOG = 'output/logs/ffmpeg.log';
const DEFAULT_PLAN = 'output/production_plan.json';

async function main() {
  try {
    const args = parseArgs(process.argv.slice(2));
    const paths = await resolveInputs(args);

    await validateInputs(paths);
    await fs.mkdir(path.dirname(paths.output), {recursive: true});
    await fs.mkdir(path.dirname(paths.log), {recursive: true});

    const command = buildFfmpegCommand(paths);
    await writeLog(paths.log, [
      `Started: ${new Date().toISOString()}`,
      `Command: ffmpeg ${command.args.map(quoteArg).join(' ')}`,
      ''
    ].join('\n'));

    await runFfmpeg(command.args, paths.log);
    await validateOutput(paths.output);

    await appendLog(paths.log, `\nCompleted: ${new Date().toISOString()}\nOutput: ${paths.output}\n`);
    console.log(`Final lyric video written to ${paths.output}`);
  } catch (error) {
    console.error(error instanceof Error ? error.message : String(error));
    process.exitCode = 1;
  }
}

function parseArgs(args) {
  const parsed = {
    burnSubtitles: true
  };

  for (let index = 0; index < args.length; index += 1) {
    const arg = args[index];

    if (arg === '--audio') {
      parsed.audio = args[index + 1];
      index += 1;
    } else if (arg === '--video') {
      parsed.video = args[index + 1];
      index += 1;
    } else if (arg === '--out') {
      parsed.output = args[index + 1];
      index += 1;
    } else if (arg === '--no-subtitles') {
      parsed.burnSubtitles = false;
    } else if (arg === '--title') {
      parsed.title = args[index + 1];
      index += 1;
    } else if (arg === '--artist') {
      parsed.artist = args[index + 1];
      index += 1;
    } else if (arg === '--help' || arg === '-h') {
      printHelp();
      process.exit(0);
    } else {
      throw new Error(`Unknown argument: ${arg}`);
    }
  }

  return parsed;
}

async function resolveInputs(args) {
  const cwd = process.cwd();
  const video = path.resolve(cwd, args.video ?? DEFAULT_VIDEO);
  const subtitles = path.resolve(cwd, DEFAULT_SUBTITLES);
  const discovered = await discoverInputFiles('input');
  const audio = path.resolve(cwd, args.audio ?? discovered.audio ?? 'input/audio.wav');
  const output = path.resolve(cwd, args.output ?? DEFAULT_OUTPUT);
  const log = path.resolve(cwd, DEFAULT_LOG);
  const plan = await tryReadPlan(path.resolve(cwd, DEFAULT_PLAN));
  const audioDuration = await probeAudioDuration(audio);
  const planDuration = getTotalDuration(plan);
  const totalDuration = planDuration ?? audioDuration;

  return {
    video,
    subtitles,
    audio,
    output,
    log,
    burnSubtitles: args.burnSubtitles,
    title: args.title ?? null,
    artist: args.artist ?? null,
    videoHeight: getResolutionHeight(plan),
    videoFps: getVideoFps(plan),
    totalDuration
  };
}

function probeAudioDuration(audioPath) {
  return new Promise((resolve) => {
    const child = spawn('ffprobe', [
      '-v', 'quiet',
      '-print_format', 'json',
      '-show_streams',
      '-select_streams', 'a:0',
      audioPath
    ], {stdio: ['ignore', 'pipe', 'pipe']});

    let out = '';
    child.stdout.on('data', (chunk) => { out += chunk; });
    child.on('close', (code) => {
      if (code !== 0) { resolve(null); return; }
      try {
        const dur = Number(JSON.parse(out).streams?.[0]?.duration);
        resolve(Number.isFinite(dur) && dur > 0 ? dur : null);
      } catch {
        resolve(null);
      }
    });
    child.on('error', () => resolve(null));
  });
}

async function tryReadPlan(planPath) {
  try {
    const raw = await fs.readFile(planPath, 'utf8');
    return JSON.parse(raw.replace(/^﻿/, ''));
  } catch {
    return null;
  }
}

function getResolutionWidth(plan) {
  const resolution = String(plan?.project?.resolution ?? '1920x1080');
  const [w] = resolution.split('x').map(Number);
  return Number.isFinite(w) && w > 0 ? w : 1920;
}

function getResolutionHeight(plan) {
  const resolution = String(plan?.project?.resolution ?? '1920x1080');
  const parts = resolution.split('x').map(Number);
  const h = parts[1];
  return Number.isFinite(h) && h > 0 ? h : 1080;
}

function getVideoFps(plan) {
  const fps = Number(plan?.project?.fps ?? 30);
  return Number.isFinite(fps) && fps > 0 ? Math.round(fps) : 30;
}

function getTotalDuration(plan) {
  if (!plan) return null;

  // Try duration_total from project metadata
  const raw = plan.project?.duration_total;
  if (raw) {
    const d = parseTimestampToSeconds(raw);
    if (d !== null) return d;
  }

  // Fall back to last segment end time
  const segments = plan.segments;
  if (!Array.isArray(segments) || segments.length === 0) return null;
  return parseTimestampToSeconds(segments[segments.length - 1]?.end);
}

function parseTimestampToSeconds(ts) {
  if (typeof ts !== 'string') return null;
  const m = ts.match(/^(\d{2}):(\d{2}):(\d{2})\.(\d{3})$/);
  if (!m) return null;
  return Number(m[1]) * 3600 + Number(m[2]) * 60 + Number(m[3]) + Number(m[4]) / 1000;
}

async function validateInputs(paths) {
  const errors = [];

  if (!(await exists(paths.video))) {
    errors.push(`Typography video does not exist: ${paths.video}`);
  }

  if (!(await exists(paths.audio))) {
    errors.push(`Audio file does not exist. Add any .mp3 or .wav under input/, or pass --audio path/to/file.`);
  }

  if (paths.burnSubtitles && !(await exists(paths.subtitles))) {
    errors.push(`Subtitle file does not exist: ${paths.subtitles}`);
  }

  if (errors.length > 0) {
    throw new Error(`FFmpeg composition validation failed:\n- ${errors.join('\n- ')}`);
  }

  if (!Number.isFinite(paths.totalDuration) || paths.totalDuration <= 0) {
    throw new Error('FFmpeg composition validation failed:\n- Unable to determine output duration from production_plan.json or audio metadata.');
  }
}

function buildFfmpegCommand(paths) {
  const duration = paths.totalDuration;
  const durationText = duration.toFixed(3);

  const filterParts = [];

  // Step 1: Trim audio to the planned duration for the output audio track.
  filterParts.push(`[1:a]atrim=duration=${durationText},asetpts=PTS-STARTPTS[aout]`);

  // Step 2: Pad with the last frame if the typography render is shorter than
  // the final timeline, then trim to a finite stream so FFmpeg terminates.
  filterParts.push(`[0:v]tpad=stop_mode=clone:stop_duration=${durationText},trim=duration=${durationText},setpts=PTS-STARTPTS[vbase]`);

  let currentLabel = 'vbase';

  // Step 3: Optional subtitle burning. The standard pipeline skips this because
  // subtitles are already burned in the render phase.
  if (paths.burnSubtitles) {
    filterParts.push(
      `[${currentLabel}]subtitles=${escapeFilterPath(paths.subtitles)}[vsub]`
    );
    currentLabel = 'vsub';
  }

  // Step 4: Progress bar, growing left-to-right at the top of the screen.
  // drawbox supports time expression via 't' variable without needing eval=frame.
  // geq was correct but ~40x slower; drawbox is the right filter here.
  if (duration && duration > 0) {
    filterParts.push(
      `[${currentLabel}]drawbox=x=0:y=0:w='iw*min(t/${durationText},1)':h=5:color=white@0.70:t=fill[vprog]`
    );
    currentLabel = 'vprog';
  }

  // Step 5: Title/artist intro overlay (top area, first ~4 seconds, fade in/out)
  const titleChain = buildTitleChain(paths.title, paths.artist, duration);
  if (titleChain) {
    filterParts.push(`[${currentLabel}]${titleChain}[vtitle]`);
    currentLabel = 'vtitle';
  }

  return {
    args: [
      '-y',
      '-i', paths.video,
      '-i', paths.audio,
      '-filter_complex', filterParts.join(';'),
      '-map', `[${currentLabel}]`,
      '-map', '[aout]',
      '-c:v', 'libx264',
      '-pix_fmt', 'yuv420p',
      '-c:a', 'aac',
      '-b:a', '192k',
      '-t', durationText,
      '-movflags', '+faststart',
      paths.output
    ]
  };
}

// On Windows, fontconfig is not available so drawtext requires an explicit
// fontfile. malgun.ttf (맑은 고딕) supports Latin and Korean characters.
const DRAWTEXT_FONT_PARAM = resolveFontParam();

function resolveFontParam() {
  if (process.platform !== 'win32') return '';
  const candidates = [
    'C\\:/Windows/Fonts/malgun.ttf',
    'C\\:/Windows/Fonts/arial.ttf',
    'C\\:/Windows/Fonts/ARIALUNI.TTF'
  ];
  for (const p of candidates) {
    try {
      const fsPath = p.replace('\\:', ':').replace(/\//g, '\\');
      accessSync(fsPath);
      return `fontfile='${p}':`;
    } catch {
      // try next
    }
  }
  return '';
}

function buildTitleChain(title, artist, duration) {
  if (!title && !artist) return null;

  // Skip overlay if content is too short for a readable intro
  if (duration !== null && duration <= 4.0) return null;

  const showUntil = 4.0;
  const fadeIn = 0.7;
  const fadeOut = 0.7;
  const holdUntil = (showUntil - fadeOut).toFixed(2);
  const alphaExpr = `if(lt(t,${fadeIn}),t/${fadeIn},if(lt(t,${holdUntil}),1,max(0,(${showUntil}-t)/${fadeOut})))`;
  const enableExpr = `between(t,0,${showUntil})`;
  const fp = DRAWTEXT_FONT_PARAM;

  const filters = [];

  if (title) {
    const escaped = escapeDrawtextString(title.trim().slice(0, 60));
    filters.push(
      `drawtext=${fp}text='${escaped}':fontsize=52:fontcolor=white:x=(W-text_w)/2:y=H*0.10:shadowx=3:shadowy=3:shadowcolor=black@0.90:alpha='${alphaExpr}':enable='${enableExpr}'`
    );
  }

  if (artist) {
    const escaped = escapeDrawtextString(artist.trim().slice(0, 50));
    filters.push(
      `drawtext=${fp}text='${escaped}':fontsize=30:fontcolor=0xDDDDDD:x=(W-text_w)/2:y=H*0.10+68:shadowx=2:shadowy=2:shadowcolor=black@0.90:alpha='${alphaExpr}':enable='${enableExpr}'`
    );
  }

  return filters.join(',');
}

function escapeDrawtextString(text) {
  return String(text)
    .replace(/\\/g, '\\\\')
    .replace(/'/g, "\\'")
    .replace(/:/g, '\\:')
    .replace(/%/g, '%%')
    .replace(/\r?\n/g, ' ');
}

function runFfmpeg(args, logPath) {
  return new Promise((resolve, reject) => {
    const child = spawn('ffmpeg', args, {
      cwd: process.cwd(),
      shell: false,
      stdio: ['ignore', 'pipe', 'pipe']
    });

    child.stdout.on('data', (chunk) => {
      appendLog(logPath, chunk.toString()).catch(() => {});
    });

    child.stderr.on('data', (chunk) => {
      appendLog(logPath, chunk.toString()).catch(() => {});
    });

    child.on('error', (error) => {
      if (error.code === 'ENOENT') {
        reject(new Error('FFmpeg is not installed or not available on PATH.'));
      } else {
        reject(error);
      }
    });

    child.on('close', (code) => {
      if (code === 0) {
        resolve();
      } else {
        reject(new Error(`FFmpeg failed with exit code ${code}. See ${logPath}`));
      }
    });
  });
}

async function validateOutput(outputPath) {
  if (!(await exists(outputPath))) {
    throw new Error(`FFmpeg finished but output was not created: ${outputPath}`);
  }

  const stat = await fs.stat(outputPath);
  if (stat.size <= 0) {
    throw new Error(`FFmpeg output is empty: ${outputPath}`);
  }
}

function escapeFilterPath(filePath) {
  const normalized = filePath.replace(/\\/g, '/').replace(/:/g, '\\:').replace(/'/g, "\\'");
  return `'${normalized}'`;
}

async function exists(filePath) {
  try {
    await fs.access(filePath);
    return true;
  } catch {
    return false;
  }
}

async function writeLog(filePath, message) {
  await fs.writeFile(filePath, message, 'utf8');
}

async function appendLog(filePath, message) {
  await fs.appendFile(filePath, message, 'utf8');
}

function quoteArg(value) {
  return /\s/.test(value) ? `"${value.replace(/"/g, '\\"')}"` : value;
}

function printHelp() {
  console.log([
    'Usage: node src/ffmpeg/composeFinalVideo.js [options]',
    '',
    'Options:',
    '  --audio <path>       Audio file. Defaults to input/audio.mp3 or input/audio.wav.',
    '  --video <path>       Typography video. Defaults to output/rendered_typography_video.mp4.',
    '  --out <path>         Output MP4. Defaults to output/lyric_video.mp4.',
    '  --no-subtitles       Do not burn output/subtitles.ass.',
    '  --title <text>       Song title shown as intro overlay (first 4 seconds).',
    '  --artist <text>      Artist name shown under title in intro overlay.',
    '  -h, --help           Show this help message.'
  ].join('\n'));
}

const currentFilePath = fileURLToPath(import.meta.url);
if (process.argv[1] && path.resolve(process.argv[1]) === currentFilePath) {
  await main();
}
