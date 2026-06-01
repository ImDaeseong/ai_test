import fs from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';
import {spawn} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {discoverInputFiles} from '../utils/inputDiscovery.js';

const DEFAULT_PLAN = 'output/production_plan.json';
const DEFAULT_SUBTITLES = 'output/subtitles.ass';
const DEFAULT_OUTPUT = 'output/rendered_typography_video.mp4';
const DEFAULT_LOG = 'output/logs/render.log';

const RESOLUTION_BY_ASPECT_RATIO = {
  '16:9': {width: 1920, height: 1080},
  '9:16': {width: 1080, height: 1920},
  '1:1': {width: 1080, height: 1080}
};

async function main() {
  try {
    const args = parseArgs(process.argv.slice(2));
    const discovered = await discoverInputFiles('input');
    const paths = {
      plan: absolute(args.plan ?? DEFAULT_PLAN),
      subtitles: absolute(args.subtitles ?? DEFAULT_SUBTITLES),
      output: absolute(args.output ?? DEFAULT_OUTPUT),
      log: absolute(args.log ?? DEFAULT_LOG),
      backgroundImage: args.background
        ? absolute(args.background)
        : discovered.backgroundImage,
      backgroundVideo: args.backgroundVideo
        ? absolute(args.backgroundVideo)
        : discovered.backgroundVideo,
      noMotion: args.noMotion === true,
      motionStrength: args.motionStrength ?? 'low'
    };

    await validateReadableFile(paths.plan, 'production_plan.json');
    await validateReadableFile(paths.subtitles, 'subtitles.ass');
    if (paths.backgroundImage) {
      await validateReadableFile(paths.backgroundImage, 'background image');
    }

    if (paths.backgroundVideo) {
      await validateReadableFile(paths.backgroundVideo, 'background video');
    }

    const plan = await readJson(paths.plan);
    const renderSettings = getRenderSettings(plan);
    const command = buildFfmpegCommand(paths, renderSettings);
    const effectSummary = describeEffectChain(paths);

    await fs.mkdir(path.dirname(paths.output), {recursive: true});
    await fs.mkdir(path.dirname(paths.log), {recursive: true});
    await writeLog(paths.log, [
      `Typography render started: ${new Date().toISOString()}`,
      `Plan: ${paths.plan}`,
      `Subtitles: ${paths.subtitles}`,
      `Output: ${paths.output}`,
      `Resolution: ${renderSettings.width}x${renderSettings.height}`,
      `FPS: ${renderSettings.fps}`,
      `Duration: ${renderSettings.durationSeconds.toFixed(3)}s`,
      `Background image: ${paths.backgroundImage ?? 'none'}`,
      `Background video: ${paths.backgroundVideo ?? 'none'}`,
      `Motion: ${paths.noMotion ? 'off' : paths.motionStrength}`,
      `Effect chain: ${effectSummary}`,
      `Command: ffmpeg ${command.map(quoteArg).join(' ')}`,
      ''
    ].join('\n'));

    await runFfmpeg(command, paths.log);
    await validateOutput(paths.output);

    await appendLog(paths.log, `\nTypography render completed: ${new Date().toISOString()}\n`);
    console.log(`Typography video written to ${paths.output}`);
  } catch (error) {
    console.error(error instanceof Error ? error.message : String(error));
    process.exitCode = 1;
  }
}

function parseArgs(args) {
  const parsed = {};

  for (let index = 0; index < args.length; index += 1) {
    const arg = args[index];

    if (arg === '--plan') {
      parsed.plan = args[index + 1];
      index += 1;
    } else if (arg === '--subtitles') {
      parsed.subtitles = args[index + 1];
      index += 1;
    } else if (arg === '--out') {
      parsed.output = args[index + 1];
      index += 1;
    } else if (arg === '--log') {
      parsed.log = args[index + 1];
      index += 1;
    } else if (arg === '--background') {
      parsed.background = args[index + 1];
      index += 1;
    } else if (arg === '--background-video') {
      parsed.backgroundVideo = args[index + 1];
      index += 1;
    } else if (arg === '--no-motion') {
      parsed.noMotion = true;
    } else if (arg === '--motion-strength') {
      parsed.motionStrength = args[index + 1];
      index += 1;
    } else if (arg === '--help' || arg === '-h') {
      printHelp();
      process.exit(0);
    } else {
      throw new Error(`Unknown argument: ${arg}`);
    }
  }

  if (parsed.motionStrength && !['low', 'medium', 'high'].includes(parsed.motionStrength)) {
    throw new Error('--motion-strength must be one of: low, medium, high.');
  }

  return parsed;
}

async function readJson(filePath) {
  try {
    const raw = await fs.readFile(filePath, 'utf8');
    return JSON.parse(raw.replace(/^﻿/, ''));
  } catch (error) {
    if (error instanceof SyntaxError) {
      throw new Error(`production_plan.json is not valid JSON: ${filePath}`);
    }

    throw error;
  }
}

// Per-tone color tints applied as time-windowed drawbox overlays
const EMOTIONAL_TINT_COLORS = {
  uplifting:     {hex: '0xFFAA33', opacity: 0.18},
  introspective: {hex: '0x1A4080', opacity: 0.22},
  reflective:    {hex: '0x442288', opacity: 0.18},
  energetic:     {hex: '0xFF5522', opacity: 0.20},
  melancholy:    {hex: '0x284060', opacity: 0.22},
  hopeful:       {hex: '0x33AA88', opacity: 0.16},
  joyful:        {hex: '0xFFCC00', opacity: 0.15},
  sad:           {hex: '0x1A3560', opacity: 0.24}
};

const TINT_CYCLE = [
  {hex: '0x1A3060', opacity: 0.15},
  {hex: '0x3D1A60', opacity: 0.15},
  {hex: '0x1A5045', opacity: 0.15},
  {hex: '0x3A1A40', opacity: 0.13},
  {hex: '0x1A3550', opacity: 0.14},
  {hex: '0x402040', opacity: 0.14}
];

function getRenderSettings(plan) {
  const aspectRatio = plan?.project?.aspect_ratio ?? '16:9';
  const resolution = RESOLUTION_BY_ASPECT_RATIO[aspectRatio];
  if (!resolution) {
    throw new Error('project.aspect_ratio must be one of: 16:9, 9:16, 1:1.');
  }

  if (!Array.isArray(plan.segments) || plan.segments.length === 0) {
    throw new Error('production_plan.json must contain at least one segment.');
  }

  const lastSegment = plan.segments[plan.segments.length - 1];
  const endMs = parseTimestampToMs(lastSegment?.end);
  if (endMs === null || endMs <= 0) {
    throw new Error('Last segment end timestamp is invalid.');
  }

  const fps = Number.isFinite(Number(plan.project?.fps)) && Number(plan.project.fps) > 0
    ? Math.round(Number(plan.project.fps))
    : 30;

  return {
    ...resolution,
    fps,
    durationSeconds: endMs / 1000,
    segments: plan.segments
  };
}

function buildFfmpegCommand(paths, settings) {
  const subtitlesFilter = `subtitles=${escapeFilterPath(paths.subtitles)}`;
  const duration = settings.durationSeconds.toFixed(3);
  const motion = motionSettings(paths.motionStrength, paths.noMotion);
  const segmentTints = buildSegmentColorFilters(settings.segments);

  // --- Video background path (loops the source video)
  if (paths.backgroundVideo) {
    const videoFilter = [
      `scale=${settings.width}:${settings.height}:force_original_aspect_ratio=increase`,
      `crop=${settings.width}:${settings.height}`,
      'setsar=1',
      segmentTints,
      readabilityFilter(settings, motion),
      subtitlesFilter
    ].filter(Boolean).join(',');

    return [
      '-y',
      '-stream_loop', '-1',
      '-i', paths.backgroundVideo,
      '-vf', videoFilter,
      '-t', duration,
      '-r', String(settings.fps),
      '-an',
      '-c:v', 'libx264',
      '-pix_fmt', 'yuv420p',
      '-movflags', '+faststart',
      paths.output
    ];
  }

  // --- Still image path (zoompan or static crop)
  if (paths.backgroundImage) {
    const imageFilter = [
      paths.noMotion
        ? `scale=${settings.width}:${settings.height}:force_original_aspect_ratio=increase,crop=${settings.width}:${settings.height}`
        : [
            `scale=${Math.ceil(settings.width * motion.scale)}:${Math.ceil(settings.height * motion.scale)}:force_original_aspect_ratio=increase`,
            `zoompan=z='min(zoom+${motion.zoomIncrement},${motion.maxZoom})':x='iw/2-(iw/zoom/2)+sin(on/${motion.panSlow})*${motion.panPixels}':y='ih/2-(ih/zoom/2)+cos(on/${motion.panSlow * 1.25})*${motion.panPixels * 0.6}':d=1:s=${settings.width}x${settings.height}:fps=${settings.fps}`
          ].join(','),
      'setsar=1',
      segmentTints,
      readabilityFilter(settings, motion),
      subtitlesFilter
    ].filter(Boolean).join(',');

    return [
      '-y',
      '-loop', '1',
      '-framerate', String(settings.fps),
      '-t', duration,
      '-i', paths.backgroundImage,
      '-vf', imageFilter,
      '-t', duration,
      '-r', String(settings.fps),
      '-an',
      '-c:v', 'libx264',
      '-pix_fmt', 'yuv420p',
      '-movflags', '+faststart',
      paths.output
    ];
  }

  // --- No-background path (solid color or animated gradient)
  const background = paths.noMotion
    ? `color=c=#08101f:s=${settings.width}x${settings.height}:r=${settings.fps}:d=${duration}`
    : `nullsrc=s=${settings.width}x${settings.height}:r=${settings.fps}:d=${duration}`;

  const fallbackFilter = paths.noMotion
    ? [segmentTints, subtitlesFilter].filter(Boolean).join(',')
    : [
        animatedFallbackFilter(settings, motion),
        segmentTints,
        readabilityFilter(settings, motion),
        subtitlesFilter
      ].filter(Boolean).join(',');

  return [
    '-y',
    '-f', 'lavfi',
    '-i', background,
    '-vf', fallbackFilter,
    '-t', duration,
    '-r', String(settings.fps),
    '-an',
    '-c:v', 'libx264',
    '-pix_fmt', 'yuv420p',
    '-movflags', '+faststart',
    paths.output
  ];
}

function buildSegmentColorFilters(segments) {
  if (!Array.isArray(segments) || segments.length === 0) {
    return null;
  }

  return segments.map((segment, index) => {
    const startSec = (parseTimestampToMs(segment.start) ?? 0) / 1000;
    const endSec = (parseTimestampToMs(segment.end) ?? 0) / 1000;
    if (endSec <= startSec) {
      return null;
    }

    const tone = (segment.style?.emotional_tone ?? '').toLowerCase().trim();
    const tint = EMOTIONAL_TINT_COLORS[tone] ?? TINT_CYCLE[index % TINT_CYCLE.length];
    return `drawbox=x=0:y=0:w=iw:h=ih:color=${tint.hex}@${tint.opacity}:thickness=fill:enable='between(t,${startSec.toFixed(3)},${endSec.toFixed(3)})'`;
  }).filter(Boolean).join(',') || null;
}

function motionSettings(strength, noMotion) {
  if (noMotion) {
    return {
      scale: 1,
      zoomIncrement: 0,
      maxZoom: 1,
      panPixels: 0,
      panSlow: 999999,
      vignetteStrength: 0.28,
      grainStrength: 0,
      darkOverlay: 0.22
    };
  }

  const settings = {
    low: {
      scale: 1.08,
      zoomIncrement: 0.00008,
      maxZoom: 1.04,
      panPixels: 10,
      panSlow: 95,
      vignetteStrength: 0.33,
      grainStrength: 7,
      darkOverlay: 0.24
    },
    medium: {
      scale: 1.12,
      zoomIncrement: 0.00014,
      maxZoom: 1.08,
      panPixels: 22,
      panSlow: 70,
      vignetteStrength: 0.38,
      grainStrength: 10,
      darkOverlay: 0.29
    },
    high: {
      scale: 1.18,
      zoomIncrement: 0.00022,
      maxZoom: 1.13,
      panPixels: 38,
      panSlow: 52,
      vignetteStrength: 0.44,
      grainStrength: 13,
      darkOverlay: 0.34
    }
  };

  return settings[strength] ?? settings.medium;
}

function readabilityFilter(_settings, motion) {
  // FFmpeg vignette positional order: angle, x0, y0, mode, eval, dither, aspect
  // (confirmed via `ffmpeg -h filter=vignette`)
  // vignetteStrength 0.28→PI/4 (subtle) … 0.44→PI/7 (strong): smaller angle = stronger effect
  const vignetteAngle = (Math.PI / (4 + (motion.vignetteStrength - 0.28) * 18.75)).toFixed(4);
  return [
    `drawbox=x=0:y=0:w=iw:h=ih:color=black@${motion.darkOverlay}:thickness=fill`,
    `vignette=angle=${vignetteAngle}`,
    motion.grainStrength > 0
      ? `noise=alls=${motion.grainStrength}:allf=t+u`
      : null,
    'format=yuv420p'
  ].filter(Boolean).join(',');
}

function animatedFallbackFilter(settings, motion) {
  // Deep blue-purple animated gradient: brighter and more dynamic than the previous formula.
  // r: 0–95 range (dark reds/purples), g: 0–57 range (subtle greens), b: 0–195 range (dominant blues)
  const geq = [
    `r='35+28*sin((X/W)*3.8+T*0.22)+14*sin((Y/H)*2.5+T*0.38)'`,
    `g='20+22*sin((Y/H)*4.2-T*0.19)+10*sin((X/W)*3.1+T*0.28)'`,
    `b='95+72*sin((X+Y)/(W*0.55)+T*0.17)+28*sin((X/W)*4.8-T*0.26)+16*sin(T*0.47)'`
  ].join(':');

  return [
    `geq=${geq}`,
    `scale=${settings.width}:${settings.height}`,
    motion.grainStrength > 0 ? `noise=alls=${Math.max(4, motion.grainStrength - 2)}:allf=t+u` : null
  ].filter(Boolean).join(',');
}

function describeEffectChain(paths) {
  if (paths.backgroundVideo) {
    return `background video loop, dark overlay, vignette, subtitles`;
  }

  if (paths.backgroundImage) {
    return paths.noMotion
      ? 'background image scale/crop, dark overlay, vignette, subtitles'
      : `background image slow zoom/pan (${paths.motionStrength}), dark overlay, vignette, light grain, subtitles`;
  }

  return paths.noMotion
    ? 'solid color background, subtitles'
    : `animated gradient/noise background (${paths.motionStrength}), dark overlay, vignette, subtitles`;
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
        reject(new Error(`FFmpeg typography render failed with exit code ${code}. See ${logPath}`));
      }
    });
  });
}

async function validateReadableFile(filePath, label) {
  let stat;
  try {
    stat = await fs.stat(filePath);
  } catch (error) {
    if (error.code === 'ENOENT') {
      throw new Error(`${label} is missing: ${filePath}`);
    }

    throw error;
  }

  if (!stat.isFile()) {
    throw new Error(`${label} is not a file: ${filePath}`);
  }

  if (stat.size <= 0) {
    throw new Error(`${label} is empty: ${filePath}`);
  }
}

async function validateOutput(outputPath) {
  const stat = await fs.stat(outputPath).catch(() => null);
  if (!stat) {
    throw new Error(`Typography render finished but output was not created: ${outputPath}`);
  }

  if (stat.size <= 0) {
    throw new Error(`Typography render output is empty: ${outputPath}`);
  }
}

function parseTimestampToMs(timestamp) {
  if (typeof timestamp !== 'string') {
    return null;
  }

  const match = timestamp.match(/^(\d{2}):([0-5]\d):([0-5]\d)\.(\d{3})$/);
  if (!match) {
    return null;
  }

  const [, hours, minutes, seconds, milliseconds] = match;
  return (
    Number(hours) * 60 * 60 * 1000 +
    Number(minutes) * 60 * 1000 +
    Number(seconds) * 1000 +
    Number(milliseconds)
  );
}

function escapeFilterPath(filePath) {
  const normalized = filePath.replace(/\\/g, '/').replace(/:/g, '\\:').replace(/'/g, "\\'");
  return `'${normalized}'`;
}

function absolute(filePath) {
  return path.isAbsolute(filePath) ? filePath : path.resolve(process.cwd(), filePath);
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
    'Usage: node src/render/renderTypographyVideo.js [options]',
    '',
    'Options:',
    '  --plan <path>             Defaults to output/production_plan.json.',
    '  --subtitles <path>        Defaults to output/subtitles.ass.',
    '  --out <path>              Defaults to output/rendered_typography_video.mp4.',
    '  --log <path>              Defaults to output/logs/render.log.',
    '  --background <path>       Background image. Defaults to first image under input/.',
    '  --background-video <path> Background video (loops). Defaults to first .mp4/.mov under input/.',
    '  --no-motion               Disable zoom/pan or animated fallback background.',
    '  --motion-strength         low, medium, or high. Defaults to low.',
    '  -h, --help                Show this help message.'
  ].join('\n'));
}

const currentFilePath = fileURLToPath(import.meta.url);
if (process.argv[1] && path.resolve(process.argv[1]) === currentFilePath) {
  await main();
}
