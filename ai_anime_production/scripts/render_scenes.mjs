/**
 * Render every scene listed in manifests/render_manifest.json to output/clips/.
 *
 * This creates Remotion fallback clips from either:
 * - public/assets/videos/{slug}.mp4, when an external AI video is present
 * - public/assets/images/{slug}.png, when only a scene image is present
 */

import fs from 'node:fs';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {ensureDir, paths, projectRoot, readJson} from './lib.mjs';

const CLIPS_DIR = path.join(projectRoot, 'output', 'clips');
const PROPS_DIR = path.join(projectRoot, 'manifests', 'scene_props');
const REMOTION_CLI = path.join(projectRoot, 'node_modules', '@remotion', 'cli', 'remotion-cli.js');

if (!fs.existsSync(paths.manifest)) {
  console.error('Missing manifests/render_manifest.json. Run: npm run import:input');
  process.exit(1);
}

if (!fs.existsSync(REMOTION_CLI)) {
  console.error(`Missing Remotion CLI: ${REMOTION_CLI}`);
  console.error('Run: npm install');
  process.exit(1);
}

const manifest = readJson(paths.manifest);
ensureDir(CLIPS_DIR);
ensureDir(PROPS_DIR);

const renderableScenes = (manifest.scenes || []).filter((scene) => scene.image_exists || scene.video_exists);

if (renderableScenes.length === 0) {
  console.error('No renderable scenes. Add a scene image to input/ and run npm run import:input.');
  process.exit(1);
}

const fps = manifest.fps ?? 30;
const bpm = manifest.bpm ?? 120; // 120 = safe neutral default when prompt has no BPM
const failed = [];

console.log('Resolution: 1920x1080 (16:9 HD)');
console.log(`Scenes to render: ${renderableScenes.length}`);
console.log(`Output folder: ${CLIPS_DIR}\n`);

for (const scene of renderableScenes) {
  const propsFile = path.join(PROPS_DIR, `${scene.slug}.json`);
  const outputFile = path.join(CLIPS_DIR, `${scene.slug}.mp4`);
  const durationSec = (scene.duration_frames / fps).toFixed(1);

  fs.writeFileSync(
    propsFile,
    JSON.stringify({scene, fps, bpm}, null, 2),
    'utf8',
  );

  console.log(`Rendering ${scene.slug} (${durationSec}s, ${scene.duration_frames}f)`);

  const result = spawnSync(
    process.execPath,
    [REMOTION_CLI, 'render', 'src/index.ts', 'SceneOnly', outputFile, `--props=${propsFile}`],
    {
      cwd: projectRoot,
      stdio: 'inherit',
      shell: false,
    },
  );

  if (result.status !== 0) {
    console.error(`Render failed: ${scene.slug}`);
    failed.push(scene.slug);
    continue;
  }

  const size = fs.existsSync(outputFile)
    ? `${(fs.statSync(outputFile).size / 1024 / 1024).toFixed(1)} MB`
    : '?';
  console.log(`Done: ${path.basename(outputFile)} (${size})\n`);
}

if (failed.length > 0) {
  console.error(`Failed scene(s): ${failed.join(', ')}`);
  process.exit(1);
}

console.log(`Complete. Rendered ${renderableScenes.length} clip(s) to ${CLIPS_DIR}`);
console.log('For AI-generated motion, place external clips in public/assets/videos/{slug}.mp4 and re-run manifest/render.');
