import fs from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';
import {spawn} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {formatTimestamp} from '../utils/timecode.js';
import {validatePlannerInput, validateProductionPlan} from '../utils/validation.js';
import {discoverInputFiles} from '../utils/inputDiscovery.js';
import {readLyricInput} from '../utils/lyricParsers.js';

const RESOLUTION_BY_ASPECT_RATIO = {
  '16:9': '1920x1080',
  '9:16': '1080x1920',
  '1:1': '1080x1080'
};

const DEFAULTS = {
  aspectRatio: '16:9',
  durationPerLine: 4,
  mood: 'reflective',
  genre: 'contemporary pop',
  language: 'auto',
  visualStyle: 'original kinetic typography with soft abstract backgrounds',
  fps: 30
};

async function main() {
  try {
    const args = parseArgs(process.argv.slice(2));
    const discovered = await discoverInputFiles('input');
    const inputPath = path.resolve(process.cwd(), args.input ?? discovered.lyrics ?? 'input/lyrics.json');
    const outputPath = path.resolve(process.cwd(), args.output ?? 'output/production_plan.json');

    const input = await readInput(inputPath);
    const inputErrors = validatePlannerInput(input);
    if (inputErrors.length > 0) {
      throw new Error(`Planner input validation failed:\n- ${inputErrors.join('\n- ')}`);
    }

    const audioDurationSeconds = await probeAudioDuration(discovered.audio);
    const plan = createProductionPlan(input, {minimumDurationSeconds: audioDurationSeconds});
    const planErrors = validateProductionPlan(plan);
    if (planErrors.length > 0) {
      throw new Error(`Production plan validation failed:\n- ${planErrors.join('\n- ')}`);
    }

    await fs.mkdir(path.dirname(outputPath), {recursive: true});
    await fs.writeFile(outputPath, `${JSON.stringify(plan, null, 2)}\n`, 'utf8');

    console.log(`Production plan written to ${outputPath}`);
  } catch (error) {
    console.error(error.message);
    process.exitCode = 1;
  }
}

export function createProductionPlan(input, options = {}) {
  const timedSegments = Array.isArray(input.timed_segments)
    ? input.timed_segments.map(normalizeTimedSegment).filter(Boolean)
    : [];
  const lyricLines = input.lyrics
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);

  if (lyricLines.length === 0) {
    throw new Error('lyrics must contain at least one non-empty line.');
  }

  const aspectRatio = input.aspect_ratio ?? DEFAULTS.aspectRatio;
  const durationPerLine = Number(input.duration_per_line ?? DEFAULTS.durationPerLine);
  const mood = normalizeText(input.mood, DEFAULTS.mood);
  const genre = normalizeText(input.genre, DEFAULTS.genre);
  const language = normalizeText(input.language, DEFAULTS.language);
  const visualStyle = normalizeText(input.visual_style, DEFAULTS.visualStyle);
  const colorPalette = inferColorPalette(mood, genre);
  const lightingStyle = inferLighting(mood);
  const fontStyle = inferFontStyle(genre, visualStyle);
  const lyricDurationTotal = timedSegments.length > 0
    ? timestampToSeconds(timedSegments[timedSegments.length - 1].end)
    : lyricLines.length * durationPerLine;
  const minimumDurationSeconds = Number(options.minimumDurationSeconds);
  const durationTotal = Number.isFinite(minimumDurationSeconds) && minimumDurationSeconds > lyricDurationTotal
    ? minimumDurationSeconds
    : lyricDurationTotal;

  const sourceSegments = timedSegments.length > 0
    ? timedSegments
    : lyricLines.map((lyric, index) => {
        const startSeconds = index * durationPerLine;
        const endSeconds = startSeconds + durationPerLine;
        return {
          start: formatTimestamp(startSeconds),
          end: formatTimestamp(endSeconds),
          duration: Number(durationPerLine.toFixed(3)),
          lyric
        };
      });

  const segments = sourceSegments.map((sourceSegment, index) => {
    const lyric = sourceSegment.lyric;
    const emotionalTone = inferEmotionalTone(lyric, mood);

    return {
      id: index + 1,
      start: sourceSegment.start,
      end: sourceSegment.end,
      duration: Number(sourceSegment.duration.toFixed(3)),
      lyric,
      scene_summary: buildSceneSummary(lyric, mood, visualStyle),
      image_prompt: buildImagePrompt(lyric, mood, genre, visualStyle, colorPalette),
      negative_prompt: 'copyrighted characters, artist imitation, studio imitation, logos, watermarks, explicit content, unsafe imagery, low resolution, unreadable text',
      motion: {
        camera: inferCameraMotion(index),
        background_motion: inferBackgroundMotion(mood),
        text_animation: inferTextAnimation(index, input.karaoke_highlight === true),
        transition: inferTransition(index, lyricLines.length)
      },
      style: {
        color_palette: colorPalette.join(', '),
        lighting: lightingStyle,
        background: inferBackgroundStyle(visualStyle, mood),
        emotional_tone: emotionalTone
      },
      ffmpeg_notes: 'Reserve this segment for typography compositing over original abstract background assets.'
    };
  });

  return {
    project: {
      title: inferTitle(sourceSegments.map((segment) => segment.lyric)),
      language,
      aspect_ratio: aspectRatio,
      fps: DEFAULTS.fps,
      resolution: RESOLUTION_BY_ASPECT_RATIO[aspectRatio],
      duration_total: formatTimestamp(durationTotal),
      visual_style: visualStyle,
      global_mood: mood,
      genre,
      color_palette: colorPalette,
      lighting_style: lightingStyle,
      font_style: fontStyle,
      text_safe_area: 'Keep primary lyric text inside the center 80% width and 75% height.'
    },
    segments,
    subtitles: {
      format: 'ass',
      karaoke_highlight: input.karaoke_highlight === true,
      ass_style: {
        font: fontStyle,
        font_size: aspectRatio === '9:16' ? '72' : '64',
        primary_color: '&H00FFFFFF',
        highlight_color: '&H0000D7FF',
        outline_color: '&H00202020',
        alignment: 'bottom'
      }
    },
    motion_canvas: {
      scene_structure: segments.map((segment) => ({
        segment_id: segment.id,
        start: segment.start,
        end: segment.end,
        layers: ['background', 'lyric_text', 'transition']
      })),
      components: ['BackgroundLayer', 'LyricText', 'SceneTransition'],
      animation_strategy: 'Generate one reusable timeline where each lyric segment animates text over a consistent original abstract background system.'
    },
    assets: [],
    render: {
      motion_canvas: true,
      ffmpeg: true,
      intermediate_files: ['output/subtitles.ass', 'output/rendered_typography_video.mp4'],
      final_output: 'lyric_video.mp4',
      export_command: ''
    }
  };
}

function parseArgs(args) {
  const parsed = {};

  for (let index = 0; index < args.length; index += 1) {
    const arg = args[index];
    if (arg === '--input') {
      parsed.input = args[index + 1];
      index += 1;
    } else if (arg === '--output') {
      parsed.output = args[index + 1];
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

async function readInput(filePath) {
  try {
    return await readLyricInput(filePath);
  } catch (error) {
    if (error.code === 'ENOENT') {
      throw new Error(`Input file does not exist: ${filePath}`);
    }
    if (error instanceof SyntaxError) {
      throw new Error(`Input file is not valid JSON: ${filePath}`);
    }
    throw error;
  }
}

function printHelp() {
  console.log(`Usage: node src/planner/generateProductionPlan.js --input input/lyrics.srt --output output/production_plan.json`);
}

function normalizeTimedSegment(segment) {
  if (!segment || typeof segment !== 'object') {
    return null;
  }

  const lyric = typeof segment.lyric === 'string' ? segment.lyric.trim() : '';
  const start = typeof segment.start === 'string' ? segment.start : '';
  const end = typeof segment.end === 'string' ? segment.end : '';
  const duration = Number(segment.duration ?? timestampToSeconds(end) - timestampToSeconds(start));

  if (!lyric || !start || !end || !Number.isFinite(duration) || duration <= 0) {
    return null;
  }

  return {lyric, start, end, duration};
}

function timestampToSeconds(timestamp) {
  const match = timestamp?.match(/^(\d{2}):(\d{2}):(\d{2})\.(\d{3})$/);
  if (!match) {
    return 0;
  }

  const [, hours, minutes, seconds, milliseconds] = match;
  return Number(hours) * 3600 + Number(minutes) * 60 + Number(seconds) + Number(milliseconds) / 1000;
}

function normalizeText(value, fallback) {
  return typeof value === 'string' && value.trim().length > 0 ? value.trim() : fallback;
}

function inferTitle(lines) {
  const firstLine = lines[0] ?? 'Untitled Lyric Video';
  return firstLine.length <= 48 ? firstLine : `${firstLine.slice(0, 45).trim()}...`;
}

function inferColorPalette(mood, genre) {
  const normalized = `${mood} ${genre}`.toLowerCase();

  if (normalized.includes('hope')) {
    return ['deep navy', 'warm gold', 'soft cyan', 'clean white'];
  }
  if (normalized.includes('sad') || normalized.includes('melancholy')) {
    return ['midnight blue', 'mist gray', 'pale silver', 'muted teal'];
  }
  if (normalized.includes('energetic') || normalized.includes('dance')) {
    return ['charcoal black', 'electric cyan', 'hot coral', 'white'];
  }

  return ['ink black', 'soft violet', 'cool blue', 'warm white'];
}

function inferLighting(mood) {
  const normalized = mood.toLowerCase();
  if (normalized.includes('hope')) {
    return 'gentle rim light with warm highlights';
  }
  if (normalized.includes('dark') || normalized.includes('sad')) {
    return 'low contrast ambient light with subtle glows';
  }
  return 'soft cinematic lighting with clear lyric readability';
}

function inferFontStyle(genre, visualStyle) {
  const normalized = `${genre} ${visualStyle}`.toLowerCase();
  if (normalized.includes('rock')) {
    return 'bold condensed sans serif';
  }
  if (normalized.includes('acoustic') || normalized.includes('folk')) {
    return 'warm humanist sans serif';
  }
  return 'modern geometric sans serif';
}

function inferEmotionalTone(lyric, mood) {
  const text = lyric.toLowerCase();
  if (/\b(rise|start|light|spark|hope|again)\b/.test(text)) {
    return 'uplifting';
  }
  if (/\b(lost|alone|rain|night|goodbye)\b/.test(text)) {
    return 'introspective';
  }
  return mood;
}

function buildSceneSummary(lyric, mood, visualStyle) {
  return `Original ${visualStyle} scene expressing a ${mood} feeling for the lyric: "${lyric}".`;
}

function buildImagePrompt(lyric, mood, genre, visualStyle, colorPalette) {
  return [
    `Original abstract lyric video background for the line "${lyric}"`,
    `${mood} mood`,
    `${genre} energy`,
    visualStyle,
    `palette of ${colorPalette.join(', ')}`,
    'no artist imitation, no recognizable copyrighted media, leave clean space for large readable typography'
  ].join(', ');
}

function inferCameraMotion(index) {
  const motions = [
    'slow push-in with stable center framing',
    'gentle lateral drift with subtle parallax',
    'small pull-back revealing more negative space'
  ];
  return motions[index % motions.length];
}

function inferBackgroundMotion(mood) {
  return mood.toLowerCase().includes('energetic')
    ? 'rhythmic abstract pulses synced to segment changes'
    : 'slow atmospheric movement with soft particles and gradient shifts';
}

function inferTextAnimation(index, karaokeHighlight) {
  const entrance = index % 2 === 0 ? 'fade and rise' : 'slide in with slight scale settle';
  return karaokeHighlight
    ? `${entrance}; word-level highlight sweep across the lyric`
    : `${entrance}; hold with subtle breathing scale`;
}

function inferTransition(index, totalSegments) {
  if (index === totalSegments - 1) {
    return 'soft fade out';
  }
  return index % 2 === 0 ? 'crossfade with light streak' : 'quick blur dissolve';
}

function inferBackgroundStyle(visualStyle, mood) {
  return `${visualStyle}; original abstract environment with ${mood} atmosphere and uncluttered text-safe center.`;
}

function probeAudioDuration(audioPath) {
  if (!audioPath) {
    return Promise.resolve(null);
  }

  return new Promise((resolve) => {
    const child = spawn('ffprobe', [
      '-v', 'quiet',
      '-print_format', 'json',
      '-show_streams',
      '-select_streams', 'a:0',
      audioPath
    ], {stdio: ['ignore', 'pipe', 'pipe']});

    let stdout = '';
    child.stdout.on('data', (chunk) => {
      stdout += chunk.toString();
    });
    child.on('close', (code) => {
      if (code !== 0) {
        resolve(null);
        return;
      }
      try {
        const duration = Number(JSON.parse(stdout).streams?.[0]?.duration);
        resolve(Number.isFinite(duration) && duration > 0 ? duration : null);
      } catch {
        resolve(null);
      }
    });
    child.on('error', () => resolve(null));
  });
}

const currentFilePath = fileURLToPath(import.meta.url);
if (process.argv[1] && path.resolve(process.argv[1]) === currentFilePath) {
  await main();
}
