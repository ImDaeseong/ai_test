import path from 'node:path';
import process from 'node:process';
import {fileURLToPath} from 'node:url';
import {validateFinalMediaOutput} from '../utils/mediaProbe.js';

async function main() {
  try {
    const args = parseArgs(process.argv.slice(2));
    const report = await validateFinalMediaOutput({
      mediaPath: path.resolve(process.cwd(), args.media ?? 'output/lyric_video.mp4'),
      planPath: path.resolve(process.cwd(), args.plan ?? 'output/production_plan.json')
    });

    console.log(`Media validation passed: ${report.width}x${report.height}, ${report.videoCodec}/${report.audioCodec}, ${report.durationSeconds.toFixed(3)}s, ${report.size} bytes`);
  } catch (error) {
    console.error(error instanceof Error ? error.message : String(error));
    process.exitCode = 1;
  }
}

function parseArgs(args) {
  const parsed = {};

  for (let index = 0; index < args.length; index += 1) {
    const arg = args[index];

    if (arg === '--media') {
      parsed.media = args[index + 1];
      index += 1;
    } else if (arg === '--plan') {
      parsed.plan = args[index + 1];
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

function printHelp() {
  console.log([
    'Usage: node src/validate/validateMediaOutput.js [options]',
    '',
    'Options:',
    '  --media <path>   Defaults to output/lyric_video.mp4.',
    '  --plan <path>    Defaults to output/production_plan.json.',
    '  -h, --help       Show this help message.'
  ].join('\n'));
}

const currentFilePath = fileURLToPath(import.meta.url);
if (process.argv[1] && path.resolve(process.argv[1]) === currentFilePath) {
  await main();
}
