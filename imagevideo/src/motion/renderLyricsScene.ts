import fs from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';
import {spawn} from 'node:child_process';
import {fileURLToPath} from 'node:url';

const DEFAULT_PLAN = 'output/production_plan.json';
const DEFAULT_RENDER_OUTPUT = 'output/rendered_typography_video.mp4';
const GENERATED_PLAN = 'src/motion/utils/generatedPlan.ts';
const PROJECT_META = 'src/motion/project.meta';

type AspectRatio = '16:9' | '9:16' | '1:1';

interface ProductionPlan {
  project?: {
    title?: string;
    aspect_ratio?: AspectRatio;
    resolution?: string;
    fps?: number;
    font_style?: string;
    color_palette?: string[];
  };
  segments?: ProductionSegment[];
}

interface ProductionSegment {
  id?: number;
  start?: string;
  end?: string;
  duration?: number;
  lyric?: string;
  motion?: {
    camera?: string;
    background_motion?: string;
    text_animation?: string;
    transition?: string;
  };
  style?: {
    color_palette?: string;
    lighting?: string;
    background?: string;
    emotional_tone?: string;
  };
}

async function main() {
  try {
    const args = parseArgs(process.argv.slice(2));
    const planPath = path.resolve(process.cwd(), args.input ?? DEFAULT_PLAN);
    const renderOutput = path.resolve(process.cwd(), args.output ?? DEFAULT_RENDER_OUTPUT);
    const plan = await readPlan(planPath);

    validateMotionPlan(plan);
    await writeGeneratedPlan(plan);

    if (args.render) {
      await renderWithMotionCanvas(renderOutput);
    } else {
      console.log(`Motion Canvas scene data written to ${path.resolve(process.cwd(), GENERATED_PLAN)}`);
    }
  } catch (error) {
    console.error(error instanceof Error ? error.message : String(error));
    process.exitCode = 1;
  }
}

function parseArgs(args: string[]) {
  const parsed: {input?: string; output?: string; render?: boolean} = {};

  for (let index = 0; index < args.length; index += 1) {
    const arg = args[index];

    if (arg === '--input') {
      parsed.input = args[index + 1];
      index += 1;
    } else if (arg === '--output') {
      parsed.output = args[index + 1];
      index += 1;
    } else if (arg === '--render') {
      parsed.render = true;
    } else if (arg === '--generate-only') {
      parsed.render = false;
    } else if (arg === '--help' || arg === '-h') {
      printHelp();
      process.exit(0);
    } else {
      throw new Error(`Unknown argument: ${arg}`);
    }
  }

  return parsed;
}

async function readPlan(planPath: string): Promise<ProductionPlan> {
  try {
    const raw = await fs.readFile(planPath, 'utf8');
    return JSON.parse(raw.replace(/^\uFEFF/, ''));
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === 'ENOENT') {
      throw new Error(`production_plan.json does not exist: ${planPath}`);
    }
    if (error instanceof SyntaxError) {
      throw new Error(`production_plan.json is not valid JSON: ${planPath}`);
    }
    throw error;
  }
}

function validateMotionPlan(plan: ProductionPlan) {
  const errors: string[] = [];
  const aspectRatio = plan.project?.aspect_ratio;
  const allowedAspectRatios = new Set(['16:9', '9:16', '1:1']);

  if (!plan || typeof plan !== 'object' || Array.isArray(plan)) {
    throw new Error('production_plan.json must contain a JSON object.');
  }

  if (!allowedAspectRatios.has(aspectRatio ?? '')) {
    errors.push('project.aspect_ratio must be one of: 16:9, 9:16, 1:1.');
  }

  if (!Number.isFinite(plan.project?.fps) || Number(plan.project?.fps) <= 0) {
    errors.push('project.fps must be greater than zero.');
  }

  if (!Array.isArray(plan.segments) || plan.segments.length === 0) {
    errors.push('segments must be a non-empty array.');
  }

  for (const [index, segment] of (plan.segments ?? []).entries()) {
    const label = `Segment ${segment.id ?? index + 1}`;
    const startMs = parseTimestampToMs(segment.start);
    const endMs = parseTimestampToMs(segment.end);

    if (segment.id !== index + 1) {
      errors.push(`${label} id must be sequential.`);
    }
    if (startMs === null) {
      errors.push(`${label} has an invalid start timestamp.`);
    }
    if (endMs === null) {
      errors.push(`${label} has an invalid end timestamp.`);
    }
    if (startMs !== null && endMs !== null && endMs <= startMs) {
      errors.push(`${label} end time must be after start time.`);
    }
    if (!Number.isFinite(segment.duration) || Number(segment.duration) <= 0) {
      errors.push(`${label} duration must be greater than zero.`);
    }
    if (typeof segment.lyric !== 'string' || segment.lyric.trim().length === 0) {
      errors.push(`${label} lyric is required.`);
    }
    if (!segment.motion?.camera) {
      errors.push(`${label} motion.camera is required.`);
    }
    if (!segment.motion?.background_motion) {
      errors.push(`${label} motion.background_motion is required.`);
    }
    if (!segment.motion?.text_animation) {
      errors.push(`${label} motion.text_animation is required.`);
    }
    if (!segment.motion?.transition) {
      errors.push(`${label} motion.transition is required.`);
    }
  }

  if (errors.length > 0) {
    throw new Error(`Motion Canvas validation failed:\n- ${errors.join('\n- ')}`);
  }
}

async function writeGeneratedPlan(plan: ProductionPlan) {
  const safePlan = {
    project: {
      title: plan.project?.title ?? 'Generated Lyric Video',
      aspect_ratio: plan.project?.aspect_ratio ?? '16:9',
      resolution: plan.project?.resolution ?? '1920x1080',
      fps: plan.project?.fps ?? 30,
      font_style: plan.project?.font_style ?? 'modern geometric sans serif',
      color_palette: plan.project?.color_palette ?? []
    },
    segments: (plan.segments ?? []).map((segment) => ({
      id: segment.id,
      start: segment.start,
      end: segment.end,
      duration: segment.duration,
      lyric: segment.lyric,
      motion: {
        camera: segment.motion?.camera,
        background_motion: segment.motion?.background_motion,
        text_animation: segment.motion?.text_animation,
        transition: segment.motion?.transition
      },
      style: {
        color_palette: segment.style?.color_palette ?? '',
        lighting: segment.style?.lighting ?? '',
        background: segment.style?.background ?? '',
        emotional_tone: segment.style?.emotional_tone ?? ''
      }
    }))
  };

  const content = `export interface MotionPlanProject {
  title: string;
  aspect_ratio: '16:9' | '9:16' | '1:1';
  resolution: string;
  fps: number;
  font_style: string;
  color_palette: string[];
}

export interface MotionPlanSegment {
  id: number;
  start: string;
  end: string;
  duration: number;
  lyric: string;
  motion: {
    camera: string;
    background_motion: string;
    text_animation: string;
    transition: string;
  };
  style: {
    color_palette: string;
    lighting: string;
    background: string;
    emotional_tone: string;
  };
}

export interface MotionPlan {
  project: MotionPlanProject;
  segments: MotionPlanSegment[];
}

export const motionPlan: MotionPlan = ${JSON.stringify(safePlan, null, 2)} as MotionPlan;

export const motionProjectSettings = {
  aspectRatio: motionPlan.project.aspect_ratio,
  resolution: motionPlan.project.resolution,
  fps: motionPlan.project.fps
};
`;

  await fs.mkdir(path.dirname(path.resolve(process.cwd(), GENERATED_PLAN)), {recursive: true});
  await fs.writeFile(path.resolve(process.cwd(), GENERATED_PLAN), content, 'utf8');
  await writeProjectMeta(safePlan.project.resolution, safePlan.project.fps);
}

// Writes project.meta so the Motion Canvas editor picks up the correct canvas
// size and FPS from the production plan.
// Meta format confirmed from @motion-canvas/core ProjectMetadata source:
//   shared.size  → Vector2 serialised as [width, height]
//   preview.fps  → NumberMetaField keyed "fps"
async function writeProjectMeta(resolution: string, fps: number) {
  const [width, height] = resolution.split('x').map(Number);
  const meta = {
    version: 1,
    shared: {size: [width, height]},
    preview: {fps}
  };
  const metaPath = path.resolve(process.cwd(), PROJECT_META);
  await fs.writeFile(metaPath, `${JSON.stringify(meta, null, 2)}\n`, 'utf8');
}

async function renderWithMotionCanvas(renderOutput: string) {
  await fs.mkdir(path.dirname(renderOutput), {recursive: true});
  console.log('Motion Canvas source generated.');
  // Motion Canvas headless CLI export is not yet stable in v3.
  // Tip: run `npm run motion:dev` → open editor → Video (FFmpeg) exporter for full MC animation.
  // For automated pipelines, we use the FFmpeg typography renderer below.
  console.log('Note: Motion Canvas GUI export is interactive-only. Falling back to FFmpeg typography renderer.');
  console.log(`To use Motion Canvas animations: npm run motion:dev → render to ${renderOutput}`);
  await runCommand('node', ['src/render/renderTypographyVideo.js', '--output', renderOutput]);
}

function runCommand(command: string, args: string[]) {
  return new Promise<void>((resolve, reject) => {
    const executable = process.platform === 'win32' ? 'cmd.exe' : command;
    const commandArgs = process.platform === 'win32' ? ['/d', '/s', '/c', command, ...args] : args;
    const child = spawn(executable, commandArgs, {
      cwd: process.cwd(),
      shell: false,
      stdio: 'inherit'
    });

    child.on('error', reject);
    child.on('close', (code) => {
      if (code === 0) {
        resolve();
      } else {
        reject(new Error(`${command} ${args.join(' ')} failed with exit code ${code}.`));
      }
    });
  });
}

function parseTimestampToMs(timestamp: unknown) {
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

function printHelp() {
  console.log('Usage: tsx src/motion/renderLyricsScene.ts --input output/production_plan.json --output output/rendered_typography_video.mp4 --generate-only');
}

const currentFilePath = fileURLToPath(import.meta.url);
if (process.argv[1] && path.resolve(process.argv[1]) === currentFilePath) {
  await main();
}
