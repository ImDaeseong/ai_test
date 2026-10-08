import {existsSync} from 'node:fs';
import {mkdir, readdir, unlink} from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {bundle} from '@remotion/bundler';
import {renderStill, selectComposition} from '@remotion/renderer';

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const projectDir = path.resolve(scriptDir, '..');
const outputDir = path.join(projectDir, 'out', 'verification');
const chromeCandidates = [
  'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
  'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
];
const browserExecutable = chromeCandidates.find(existsSync);

if (browserExecutable === undefined) {
  throw new Error('Render verification HOLD: Google Chrome executable was not found.');
}

await mkdir(outputDir, {recursive: true});
for (const fileName of await readdir(outputDir)) {
  if (/^lyric-video(?:-vertical)?-\d{5}\.png$/.test(fileName)) {
    await unlink(path.join(outputDir, fileName));
  }
}
const serveUrl = await bundle({entryPoint: path.join(projectDir, 'src', 'index.ts')});

for (const id of ['lyric-video', 'lyric-video-vertical']) {
  const composition = await selectComposition({serveUrl, id, browserExecutable});
  const frames = [...new Set([0, 0.25, 0.5, 0.75, 1].map((ratio) =>
    Math.round((composition.durationInFrames - 1) * ratio),
  ))];

  for (const frame of frames) {
    await renderStill({
      composition,
      serveUrl,
      browserExecutable,
      frame,
      imageFormat: 'png',
      output: path.join(outputDir, `${id}-${String(frame).padStart(5, '0')}.png`),
      overwrite: true,
    });
  }

  console.log(`${id}: ${frames.length} sampled frames PASS`);
}
