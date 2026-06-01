/**
 * import_input.mjs
 * Builds production source directly from input/.
 *
 * Accepted input files:
 *   character_reference_prompt.{png,jpg,jpeg,webp}  optional, max 1
 *   scene_NN_name.{png,jpg,jpeg,webp}               required, one or more
 *   scene_NN_name.md                                 required, one per scene image
 *
 * Multiple scene pairs are supported.
 * The character reference is optional. If omitted, all scenes are treated as
 * landscape/environment-first and no character reference is added to video inputs.
 */

import fs from 'node:fs';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {ensureDir, paths, projectRoot, slugify, writeJson} from './lib.mjs';

const INPUT_DIR = path.join(projectRoot, 'input');
const IMAGE_EXTS = new Set(['.png', '.jpg', '.jpeg', '.webp']);
const SCENE_BASENAME_RE = /^scene_(\d+)_(.+)$/i;
const DEFAULT_DURATION_SECONDS = 30;

function fail(message) {
  console.error(message);
  process.exit(1);
}

function fileInfo(name) {
  const ext = path.extname(name).toLowerCase();
  const base = path.basename(name, ext);
  return {name, ext, base, fullPath: path.join(INPUT_DIR, name)};
}

function sceneNum(base) {
  const m = base.match(SCENE_BASENAME_RE);
  return m ? parseInt(m[1], 10) : 999;
}

function sectionName(base) {
  const m = base.match(SCENE_BASENAME_RE);
  return m ? m[2].replace(/_/g, ' ') : base;
}

function scanInput() {
  if (!fs.existsSync(INPUT_DIR)) {
    fail(`input/ folder not found: ${INPUT_DIR}`);
  }

  const files = fs
    .readdirSync(INPUT_DIR, {withFileTypes: true})
    .filter((entry) => entry.isFile())
    .map((entry) => fileInfo(entry.name));

  const characterImages = files.filter(
    (f) => IMAGE_EXTS.has(f.ext) && f.base.toLowerCase() === 'character_reference_prompt',
  );
  const sceneImages = files.filter(
    (f) => IMAGE_EXTS.has(f.ext) && SCENE_BASENAME_RE.test(f.base),
  );
  const scenePrompts = files.filter(
    (f) => f.ext === '.md' && SCENE_BASENAME_RE.test(f.base),
  );
  const accepted = new Set([...characterImages, ...sceneImages, ...scenePrompts]);
  const unexpected = files.filter((f) => !accepted.has(f));

  if (unexpected.length > 0) {
    fail(
      'Unexpected input file(s):\n' +
        unexpected.map((f) => `  - ${f.name}`).join('\n') +
        '\n\nAllowed: character_reference_prompt.png, scene_NN_name.png, scene_NN_name.md',
    );
  }
  if (characterImages.length > 1) {
    fail('Only one character_reference_prompt image is allowed.');
  }
  if (sceneImages.length === 0) {
    fail('At least one scene image is required: scene_NN_name.png');
  }
  if (scenePrompts.length === 0) {
    fail('At least one scene prompt is required: scene_NN_name.md');
  }

  // Match each image to its prompt by basename
  const scenePairs = [];
  for (const img of sceneImages) {
    const prompt = scenePrompts.find((p) => p.base.toLowerCase() === img.base.toLowerCase());
    if (!prompt) {
      fail(`Scene image has no matching prompt (.md): ${img.name}`);
    }
    scenePairs.push({image: img, prompt});
  }
  // Check for prompts without a matching image
  for (const p of scenePrompts) {
    const img = sceneImages.find((i) => i.base.toLowerCase() === p.base.toLowerCase());
    if (!img) {
      fail(`Scene prompt has no matching image: ${p.name}`);
    }
  }

  // Sort scenes by scene number
  scenePairs.sort((a, b) => sceneNum(a.image.base) - sceneNum(b.image.base));

  return {character: characterImages[0] ?? null, scenes: scenePairs};
}

function extractTitle(content) {
  const m = content.match(/^#\s+(.+?)$/m);
  return m ? m[1].trim() : null;
}

function extractBpm(content) {
  const m = content.match(/\b(\d+)\s*BPM\b/i);
  return m ? parseInt(m[1], 10) : null;
}

function extractDuration(content) {
  const patterns = [
    /\bduration_seconds\s*[:=]\s*(\d+(?:\.\d+)?)/i,
    /\bduration\s*[:=]\s*(\d+(?:\.\d+)?)\s*(?:s|sec|seconds?)\b/i,
    /\b(\d+(?:\.\d+)?)\s*(?:s|sec|seconds?)\s+(?:duration|long)\b/i,
  ];
  for (const pattern of patterns) {
    const m = content.match(pattern);
    if (!m) continue;
    const seconds = Number(m[1]);
    if (Number.isFinite(seconds) && seconds > 0) return seconds;
  }
  return DEFAULT_DURATION_SECONDS;
}

function extractIntensity(content) {
  const keywords = 'emotional\\s+peak|medium[-\\s]?high|medium|low|high|rising|falling|subtle';
  // matches: "intensity low", "intensity: high", "intensity = medium"
  const m = content.match(new RegExp(`\\bintensity[:\\s=]+\\s*(${keywords})\\b`, 'i'));
  return m ? m[1].trim().toLowerCase() : '';
}

function extractCameraDirection(content) {
  // matches: "Camera motion: ...", "Camera direction: ...", "Camera: ..."
  const m = content.match(/Camera\s+(?:motion|direction|move|movement)\s*:\s*([^\n;]+)/i)
    ?? content.match(/Camera\s*:\s*([^\n;]+)/i);
  if (!m) return '';
  return m[1].split(/[;,]/)[0].trim();
}

// --- Main ---
const input = scanInput();

ensureDir(path.join(paths.publicAssets, 'images'));
const characterTarget = path.join(paths.publicAssets, 'images', 'character_reference.png');
if (input.character) {
  fs.copyFileSync(input.character.fullPath, characterTarget);
  console.log(`Character reference: ${input.character.name} -> character_reference.png`);
} else {
  if (fs.existsSync(characterTarget)) fs.unlinkSync(characterTarget);
  console.log('No character reference. Landscape/environment-first mode.');
}

const promptsVideoDir = path.join(paths.prompts, 'video_prompts');
ensureDir(promptsVideoDir);

let projectTitle = null;
let projectBpm = null;
let totalDuration = 0;
const sceneEntries = [];

for (const pair of input.scenes) {
  const {image, prompt: promptFile} = pair;
  const content = fs.readFileSync(promptFile.fullPath, 'utf8');
  const num = sceneNum(image.base);
  const section = sectionName(image.base);
  const slug = `scene_${String(num).padStart(2, '0')}_${slugify(section)}`;
  const duration = extractDuration(content);
  const bpm = extractBpm(content);
  const title = extractTitle(content);

  if (!projectTitle && title) projectTitle = title;
  if (!projectBpm && bpm) projectBpm = bpm;
  totalDuration += duration;

  fs.copyFileSync(image.fullPath, path.join(paths.publicAssets, 'images', `${slug}.png`));
  console.log(`Scene image: ${image.name} -> ${slug}.png`);

  fs.copyFileSync(promptFile.fullPath, path.join(promptsVideoDir, `${slug}.md`));
  console.log(`Video prompt: ${promptFile.name} -> prompts/video_prompts/${slug}.md`);

  sceneEntries.push({
    scene_number: num,
    music_section: section,
    duration_seconds: duration,
    camera_direction: extractCameraDirection(content),
    movement: '',
    intensity: extractIntensity(content),
    emotion: '',
  });
}

const finalTitle = projectTitle || 'AI Anime Scene';

const songMaster = {
  title: finalTitle,
  duration_seconds: totalDuration,
  bpm: projectBpm,
  audio_files: [],
  timed_lyrics: [],
  character_reference_enabled: Boolean(input.character),
  subtitle_enabled: false,
};

const sceneList = {
  song_title: finalTitle,
  scenes: sceneEntries,
};

ensureDir(paths.sourceDir);
writeJson(path.join(paths.sourceDir, 'song_master.json'), songMaster);
writeJson(path.join(paths.sourceDir, 'scene_list.json'), sceneList);
console.log('Source manifests generated.');

const result = spawnSync(
  process.execPath,
  [path.join(projectRoot, 'scripts', 'create_manifest.mjs')],
  {cwd: projectRoot, stdio: 'inherit'},
);
if (result.status !== 0) process.exit(result.status ?? 1);

console.log(
  `\ninput/ import complete: ${input.scenes.length} scene(s), total ${totalDuration.toFixed(1)}s`,
);
if (projectBpm) console.log(`BPM: ${projectBpm}`);
