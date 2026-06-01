import fs from 'node:fs';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {
  copyDirIfExists,
  copyFileIfExists,
  ensureDir,
  findFileRecursive,
  parseArgs,
  paths,
  projectRoot,
  readJson,
} from './lib.mjs';

const args = parseArgs(process.argv.slice(2));
const sourceRoot = path.resolve(projectRoot, args.from || '../ai_anime');

const songMasterPath = path.join(sourceRoot, 'input', 'song_master.json');
const sceneListPath = path.join(sourceRoot, 'storyboard', 'scene_list.json');

if (!fs.existsSync(songMasterPath) || !fs.existsSync(sceneListPath)) {
  console.error(`Could not find ai_anime outputs under: ${sourceRoot}`);
  console.error('Expected input/song_master.json and storyboard/scene_list.json');
  process.exit(1);
}

ensureDir(paths.sourceDir);
copyFileIfExists(songMasterPath, path.join(paths.sourceDir, 'song_master.json'));
copyFileIfExists(sceneListPath, path.join(paths.sourceDir, 'scene_list.json'));

copyDirIfExists(path.join(sourceRoot, 'prompts', 'image_prompts'), path.join(paths.prompts, 'image_prompts'));
copyDirIfExists(path.join(sourceRoot, 'prompts', 'video_prompts'), path.join(paths.prompts, 'video_prompts'));
copyFileIfExists(
  path.join(sourceRoot, 'character', 'character_reference_prompt.md'),
  path.join(paths.prompts, 'character_reference_prompt.md'),
);

const songMaster = readJson(songMasterPath);
const audio = songMaster.audio_files?.[0]?.file;
if (audio) {
  const foundAudio = findFileRecursive(sourceRoot, audio);
  if (foundAudio) {
    copyFileIfExists(foundAudio, path.join(paths.publicAssets, 'audio', path.basename(audio)));
  }
}

const sourceFiles = songMaster.source_files || [];
for (const sourceFile of sourceFiles) {
  const ext = path.extname(sourceFile).toLowerCase();
  if (ext !== '.srt' && ext !== '.lrc') {
    continue;
  }
  const found = findFileRecursive(sourceRoot, sourceFile);
  if (found) {
    const targetName = ext === '.srt' ? 'lyrics_original.srt' : 'lyrics_original.lrc';
    copyFileIfExists(found, path.join(paths.publicAssets, 'subtitles', targetName));
  }
}

const result = spawnSync(process.execPath, [path.join(projectRoot, 'scripts', 'create_manifest.mjs')], {
  cwd: projectRoot,
  stdio: 'inherit',
});

if (result.status !== 0) {
  process.exit(result.status ?? 1);
}

console.log(`Imported production sources from ${sourceRoot}`);
