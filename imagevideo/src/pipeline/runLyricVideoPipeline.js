import fs from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';
import {spawn, execSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {discoverInputFiles} from '../utils/inputDiscovery.js';
import {validateFinalMediaOutput} from '../utils/mediaProbe.js';

const FILES = {
  inputDir: 'input',
  productionPlan: 'output/production_plan.json',
  subtitles: 'output/subtitles.ass',
  typographyVideo: 'output/rendered_typography_video.mp4',
  finalVideo: 'output/lyric_video.mp4',
  pipelineLog: 'output/logs/pipeline.log',
  motionLog: 'output/logs/motion.log',
  renderLog: 'output/logs/render.log',
  ffmpegLog: 'output/logs/ffmpeg.log'
};

const CLEAN_TARGETS = [
  FILES.productionPlan,
  FILES.subtitles,
  FILES.typographyVideo,
  FILES.finalVideo,
  FILES.pipelineLog,
  FILES.motionLog,
  FILES.renderLog,
  FILES.ffmpegLog
];

const PHASES = [
  {
    id: 'plan',
    label: 'Generate production_plan.json',
    script: 'plan',
    skipFlag: 'skipPlan',
    requiredOutput: FILES.productionPlan
  },
  {
    id: 'subtitles',
    label: 'Generate subtitles.ass',
    script: 'subtitles',
    skipFlag: 'skipSubtitles',
    requiredOutput: FILES.subtitles
  },
  {
    id: 'motion',
    label: 'Render FFmpeg typography video',
    script: 'render:typography',
    skipFlag: 'skipMotion',
    requiredOutput: FILES.typographyVideo,
    dedicatedLog: FILES.renderLog,
    argsForPhase: (context) => {
      const args = [];
      if (context.motionStrength) args.push('--motion-strength', context.motionStrength);
      return args;
    }
  },
  {
    id: 'compose',
    label: 'Compose final MP4 with FFmpeg',
    script: 'compose',
    skipFlag: 'skipCompose',
    requiredOutput: FILES.finalVideo,
    dedicatedLog: FILES.ffmpegLog,
    argsForPhase: (context) => {
      const args = ['--audio', context.audioPath, '--no-subtitles'];
      if (context.title) args.push('--title', context.title);
      if (context.artist) args.push('--artist', context.artist);
      return args;
    }
  }
];

function checkFFmpeg() {
  try {
    execSync('ffmpeg -version', {stdio: 'ignore'});
  } catch {
    throw new Error('FFmpeg is not installed or not in PATH. Install it from https://ffmpeg.org/download.html');
  }
}

async function main() {
  const startedAt = Date.now();
  let args;
  try {
    args = parseArgs(process.argv.slice(2));
  } catch (error) {
    console.error(`Argument error: ${error instanceof Error ? error.message : String(error)}`);
    console.error('Run with --help to see usage.');
    process.exitCode = 1;
    return;
  }
  const logPath = absolute(FILES.pipelineLog);

  try {
    if (args.clean) {
      await cleanOutputs();
    }

    await fs.mkdir(path.dirname(logPath), {recursive: true});
    await writeLog(logPath, [
      `Lyric video pipeline started: ${new Date().toISOString()}`,
      `Command: npm run lyric-video -- ${process.argv.slice(2).join(' ')}`,
      `Debug: ${args.debug ? 'on' : 'off'}`,
      ''
    ].join('\n'));

    checkFFmpeg();
    const inputFiles = await validateRequiredInputs(args);
    const context = {...inputFiles, debug: args.debug, title: args.title, artist: args.artist, motionStrength: args.motionStrength};

    await logLine(logPath, `[INPUT] Lyrics: ${context.lyricsPath}`);
    await logLine(logPath, `[INPUT] Audio: ${context.audioPath}`);
    await logLine(logPath, `[INPUT] Background image: ${context.backgroundImagePath ?? 'none'}`);
    await logLine(logPath, '');

    for (const phase of PHASES) {
      await runOrValidatePhase(phase, args, context, logPath);
    }

    const finalStat = await validateRequiredFile(FILES.finalVideo, 'Final MP4');
    const mediaReport = await validateFinalMediaOutput({
      mediaPath: absolute(FILES.finalVideo),
      planPath: absolute(FILES.productionPlan)
    });
    const totalDuration = formatDuration(Date.now() - startedAt);

    await logLine(logPath, `[SUCCESS] Pipeline completed in ${totalDuration}`);
    await logLine(logPath, `[SUCCESS] Final output: ${absolute(FILES.finalVideo)} (${finalStat.size} bytes)`);
    await logLine(logPath, `[SUCCESS] Media validation: ${mediaReport.width}x${mediaReport.height}, ${mediaReport.videoCodec}, ${mediaReport.audioCodec}, ${mediaReport.durationSeconds.toFixed(3)}s`);

    console.log('');
    console.log('Lyric video pipeline completed successfully.');
    console.log(`Final output: ${absolute(FILES.finalVideo)}`);
    console.log(`Final size: ${finalStat.size} bytes`);
    console.log(`Media: ${mediaReport.width}x${mediaReport.height}, ${mediaReport.videoCodec}/${mediaReport.audioCodec}, ${mediaReport.durationSeconds.toFixed(3)}s`);
    console.log(`Total duration: ${totalDuration}`);
    console.log(`Pipeline log: ${logPath}`);
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    await safeLogFailure(logPath, message, startedAt);

    console.error(`Lyric video pipeline failed: ${message}`);
    console.error(`See log: ${logPath}`);
    process.exitCode = 1;
  }
}

function parseArgs(args) {
  const parsed = {
    skipPlan: false,
    skipSubtitles: false,
    skipMotion: false,
    skipCompose: false,
    clean: false,
    debug: false,
    audio: null,
    title: null,
    artist: null,
    motionStrength: null
  };

  for (let index = 0; index < args.length; index += 1) {
    const arg = args[index];

    if (arg === '--skip-plan') {
      parsed.skipPlan = true;
    } else if (arg === '--skip-subtitles') {
      parsed.skipSubtitles = true;
    } else if (arg === '--skip-motion') {
      parsed.skipMotion = true;
    } else if (arg === '--skip-compose') {
      parsed.skipCompose = true;
    } else if (arg === '--clean') {
      parsed.clean = true;
    } else if (arg === '--debug') {
      parsed.debug = true;
    } else if (arg === '--audio') {
      parsed.audio = args[index + 1];
      index += 1;
    } else if (arg === '--title') {
      parsed.title = args[index + 1];
      index += 1;
    } else if (arg === '--artist') {
      parsed.artist = args[index + 1];
      index += 1;
    } else if (arg === '--motion-strength') {
      const value = args[index + 1];
      if (!['low', 'medium', 'high'].includes(value)) {
        throw new Error(`--motion-strength must be low, medium, or high. Got: ${value}`);
      }
      parsed.motionStrength = value;
      index += 1;
    } else if (arg === '--help' || arg === '-h') {
      printHelp();
      process.exit(0);
    } else {
      throw new Error(`Unknown argument: ${arg}`);
    }
  }

  if (parsed.audio !== null && (!parsed.audio || parsed.audio.startsWith('--'))) {
    throw new Error('--audio requires a file path.');
  }

  return parsed;
}

async function validateRequiredInputs(args) {
  const discovered = await discoverInputFiles(FILES.inputDir);
  const lyricsPath = discovered.lyrics;

  if (!lyricsPath) {
    throw new Error('Required lyric file is missing. Add a .srt, .lrc, or lyrics.json file under input/.');
  }

  await validateRequiredFile(lyricsPath, 'Lyrics input');

  const audioPath = args.audio ? absolute(args.audio) : discovered.audio;
  if (!audioPath) {
    throw new Error('Required audio file is missing. Add any .mp3 or .wav file under input/, or pass --audio path/to/audio.wav.');
  }

  await validateRequiredFile(audioPath, 'Audio input');
  return {
    lyricsPath,
    audioPath,
    backgroundImagePath: discovered.backgroundImage
  };
}

async function runOrValidatePhase(phase, args, context, logPath) {
  if (args[phase.skipFlag]) {
    console.log(`[SKIP] ${phase.label}`);
    await logLine(logPath, `[SKIP] ${phase.label}`);
    const stat = await validateRequiredFile(phase.requiredOutput, `${phase.label} output`);
    await logLine(logPath, `[OK] Existing output: ${absolute(phase.requiredOutput)} (${stat.size} bytes)`);
    await logLine(logPath, '');
    return;
  }

  await runPhase(phase, context, logPath);
  const stat = await validateRequiredFile(phase.requiredOutput, `${phase.label} output`);
  await logLine(logPath, `[OK] Verified output: ${absolute(phase.requiredOutput)} (${stat.size} bytes)`);
  await logLine(logPath, '');
}

async function runPhase(phase, context, logPath) {
  const startedAt = Date.now();
  const extraArgs = phase.argsForPhase ? phase.argsForPhase(context) : [];
  const {command, commandArgs} = npmRunCommand(phase.script, extraArgs);
  const commandText = `${command} ${commandArgs.join(' ')}`;

  if (phase.dedicatedLog) {
    await writeLog(absolute(phase.dedicatedLog), [
      `${phase.label} started: ${new Date().toISOString()}`,
      `Command: ${commandText}`,
      ''
    ].join('\n'));
  }

  console.log(`[START] ${phase.label}`);
  if (context.debug) {
    console.log(`[DEBUG] ${commandText}`);
  }

  await logLine(logPath, `[START] ${phase.label}`);
  await logLine(logPath, `Command: ${commandText}`);

  try {
    await runCommand(command, commandArgs, {
      pipelineLog: logPath,
      dedicatedLog: phase.dedicatedLog ? absolute(phase.dedicatedLog) : null
    });
  } catch (error) {
    const duration = formatDuration(Date.now() - startedAt);
    await logLine(logPath, `[FAILED] ${phase.label} after ${duration}`);
    throw new Error(`${phase.label} failed: ${error instanceof Error ? error.message : String(error)}`);
  }

  const duration = formatDuration(Date.now() - startedAt);
  console.log(`[DONE] ${phase.label} (${duration})`);
  await logLine(logPath, `[DONE] ${phase.label} (${duration})`);
}

function runCommand(command, args, logs) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, {
      cwd: process.cwd(),
      shell: false,
      stdio: ['ignore', 'pipe', 'pipe']
    });

    child.stdout.on('data', (chunk) => {
      const text = chunk.toString();
      process.stdout.write(text);
      appendToLogs(logs, text);
    });

    child.stderr.on('data', (chunk) => {
      const text = chunk.toString();
      process.stderr.write(text);
      appendToLogs(logs, text);
    });

    child.on('error', (error) => {
      reject(new Error(`failed to start command: ${error.message}`));
    });

    child.on('close', (code) => {
      if (code === 0) {
        resolve();
      } else {
        reject(new Error(`command exited with code ${code}`));
      }
    });
  });
}

function appendToLogs(logs, text) {
  appendLog(logs.pipelineLog, text).catch(() => {});
  if (logs.dedicatedLog) {
    appendLog(logs.dedicatedLog, text).catch(() => {});
  }
}

async function validateRequiredFile(filePath, label) {
  const resolved = absolute(filePath);
  let stat;

  try {
    stat = await fs.stat(resolved);
  } catch (error) {
    if (error.code === 'ENOENT') {
      throw new Error(`${label} is missing: ${resolved}`);
    }
    throw error;
  }

  if (!stat.isFile()) {
    throw new Error(`${label} is not a file: ${resolved}`);
  }

  if (stat.size <= 0) {
    throw new Error(`${label} is empty: ${resolved}`);
  }

  return stat;
}

async function cleanOutputs() {
  for (const target of CLEAN_TARGETS) {
    const resolved = absolute(target);
    try {
      await fs.rm(resolved, {force: true});
    } catch (error) {
      throw new Error(`Failed to clean ${resolved}: ${error.message}`);
    }
  }
}

async function writeLog(filePath, message) {
  await fs.mkdir(path.dirname(filePath), {recursive: true});
  await fs.writeFile(filePath, `${message}\n`, 'utf8');
}

async function appendLog(filePath, message) {
  await fs.mkdir(path.dirname(filePath), {recursive: true});
  await fs.appendFile(filePath, message, 'utf8');
}

async function logLine(filePath, message) {
  await appendLog(filePath, `${message}\n`);
}

async function safeLogFailure(logPath, message, startedAt) {
  try {
    await logLine(logPath, '');
    await logLine(logPath, `[FAILURE] ${message}`);
    await logLine(logPath, `[FAILURE] Pipeline stopped after ${formatDuration(Date.now() - startedAt)}`);
  } catch {
    // If logging itself is broken, still surface the original failure.
  }
}

function npmRunCommand(script, extraArgs = []) {
  if (process.platform === 'win32') {
    // cmd.exe /c 로 npm을 실행할 때 '--' 이후 인수가 npm 7+ 에서만 안정적으로 전달된다.
    // npm 스크립트 이름과 추가 인수를 하나의 문자열로 합쳐서 cmd /c 에 넘겨
    // 인수 파싱 불일치를 피한다.
    const npmArgs = ['run', script, ...(extraArgs.length > 0 ? ['--', ...extraArgs] : [])];
    return {
      command: 'cmd.exe',
      commandArgs: ['/d', '/s', '/c', `npm ${npmArgs.join(' ')}`]
    };
  }

  return {
    command: 'npm',
    commandArgs: ['run', script, ...(extraArgs.length > 0 ? ['--', ...extraArgs] : [])]
  };
}

function absolute(filePath) {
  return path.isAbsolute(filePath) ? filePath : path.resolve(process.cwd(), filePath);
}

function formatDuration(milliseconds) {
  return `${(milliseconds / 1000).toFixed(2)}s`;
}

function printHelp() {
  console.log([
    'Usage: npm run lyric-video -- [options]',
    '',
    'Required inputs (auto-discovered from input/ folder):',
    '  lyrics:              any .srt, .lrc, or lyrics.json under input/',
    '  audio:               any .mp3 or .wav under input/',
    '',
    'Optional inputs:',
    '  background image:    .png, .jpg, .jpeg, or .webp under input/',
    '  background video:    .mp4, .mov, .webm under input/ (loops if shorter than audio)',
    '',
    'Options:',
    '  --audio <path>               Override input audio file path.',
    '  --title <text>               Song title shown as intro overlay (first 4 seconds).',
    '  --artist <text>              Artist name shown under the title in intro overlay.',
    '  --motion-strength <level>    Camera and background motion: low | medium | high (default: low).',
    '  --clean                      Remove all outputs and logs before running.',
    '  --debug                      Print full phase commands.',
    '  --skip-plan                  Skip regenerating output/production_plan.json.',
    '  --skip-subtitles             Skip regenerating output/subtitles.ass.',
    '  --skip-motion                Skip rendering output/rendered_typography_video.mp4.',
    '  --skip-compose               Skip the final FFmpeg composition.',
    '  -h, --help                   Show this help message.',
    '',
    'Examples:',
    '  npm run lyric-video -- --title "환승역" --artist "아티스트" --motion-strength medium',
    '  npm run lyric-video -- --clean --motion-strength high',
    '  npm run lyric-video -- --skip-plan --skip-subtitles  (re-render only)'
  ].join('\n'));
}

const currentFilePath = fileURLToPath(import.meta.url);
if (process.argv[1] && path.resolve(process.argv[1]) === currentFilePath) {
  await main();
}
