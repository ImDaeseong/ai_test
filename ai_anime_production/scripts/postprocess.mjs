import fs from 'node:fs';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {ensureDir, paths, projectRoot} from './lib.mjs';

const input = path.join(projectRoot, 'output', 'final', 'final_mv.mp4');
const output = path.join(projectRoot, 'output', 'final', 'final_mv_web.mp4');

if (!fs.existsSync(input)) {
  console.error(`Missing rendered file: ${input}`);
  console.error('Run: npm run render');
  process.exit(1);
}

ensureDir(path.dirname(output));

const result = spawnSync(
  'ffmpeg',
  [
    '-y',
    '-i',
    input,
    '-c:v',
    'libx264',
    '-preset',
    'medium',
    '-crf',
    '16',
    '-profile:v',
    'high',
    '-pix_fmt',
    'yuv420p',
    '-movflags',
    '+faststart',
    '-colorspace',
    'bt709',
    '-color_primaries',
    'bt709',
    '-color_trc',
    'bt709',
    '-c:a',
    'aac',
    '-b:a',
    '192k',
    output,
  ],
  {stdio: 'inherit'},
);

if (result.status !== 0) {
  process.exit(result.status ?? 1);
}

console.log(`Wrote ${output}`);
