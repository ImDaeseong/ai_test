import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';

const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const remotionCli = path.join(
  projectRoot,
  'node_modules',
  '@remotion',
  'cli',
  'remotion-cli.js',
);

test('MusicVideo metadata uses the generated manifest passed by the render command', () => {
  const folder = fs.mkdtempSync(path.join(os.tmpdir(), 'ai-anime-render-contract-'));
  const propsFile = path.join(folder, 'render_manifest.json');
  try {
    fs.writeFileSync(
      propsFile,
      JSON.stringify({
        title: 'Render contract fixture',
        fps: 30,
        width: 640,
        height: 360,
        duration_seconds: 2,
        duration_frames: 60,
        bpm: 120,
        bpm_source: 'prompt',
        beat_times_seconds: [],
        first_beat_seconds: null,
        audio: null,
        subtitles: null,
        subtitle_note: '',
        character_image: '',
        character_image_exists: false,
        scenes: [],
      }),
      'utf8',
    );

    const run = spawnSync(
      process.execPath,
      [remotionCli, 'compositions', 'src/index.ts', `--props=${propsFile}`],
      {cwd: projectRoot, encoding: 'utf8', shell: false},
    );
    assert.equal(run.status, 0, `${run.stdout}\n${run.stderr}`);
    assert.match(run.stdout, /MusicVideo\s+30\s+640x360\s+60 \(2\.00 sec\)/);
  } finally {
    fs.rmSync(folder, {recursive: true, force: true});
  }
});
