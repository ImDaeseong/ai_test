import fs from 'node:fs';
import path from 'node:path';
import {parseArgs, paths, readJson} from './lib.mjs';

const args = parseArgs(process.argv.slice(2));
const allowPlaceholders = Boolean(args['allow-placeholders']);

if (!fs.existsSync(paths.manifest)) {
  console.error('Missing manifests/render_manifest.json');
  console.error('Run: npm run manifest');
  process.exit(1);
}

const manifest = readJson(paths.manifest);
const missingImages = [];
const optionalVideos = [];
const missingRequiredAssets = [];

function publicAssetPath(assetPath) {
  return path.join(paths.projectRoot, 'public', assetPath);
}

if (manifest.audio) {
  const audioPath = publicAssetPath(manifest.audio);
  if (!fs.existsSync(audioPath)) {
    missingRequiredAssets.push(`audio: ${manifest.audio}`);
  }
} else {
  // Audio is intentionally optional in the simplified image-to-video workflow.
}

if (manifest.subtitles) {
  const subtitlePath = publicAssetPath(manifest.subtitles);
  if (!fs.existsSync(subtitlePath)) {
    missingRequiredAssets.push(`subtitles: ${manifest.subtitles}`);
  }
}

for (const scene of manifest.scenes || []) {
  const imagePath = publicAssetPath(scene.image);
  const videoPath = publicAssetPath(scene.video);
  if (!fs.existsSync(imagePath)) {
    missingImages.push(scene);
  }
  if (!fs.existsSync(videoPath)) {
    optionalVideos.push(scene);
  }
}

console.log(`Title: ${manifest.title}`);
console.log(`Scenes: ${manifest.scenes.length}`);
console.log(`Audio: ${manifest.audio || 'not used'}`);
console.log(`Subtitles: ${manifest.subtitles || 'not used'}`);
if (manifest.character_image) {
  const charStatus = manifest.character_image_exists ? 'ready' : 'NOT FOUND';
  console.log(`Character image: ${manifest.character_image} [${charStatus}]`);
  if (!manifest.character_image_exists) {
    console.log('  <- Generate from: prompts/image_prompts/00_character_turnaround_model_sheet.md');
  }
} else {
  console.log('Character image: none (landscape/environment-first mode)');
}

if (missingRequiredAssets.length > 0) {
  console.log('\nMissing required assets:');
  for (const asset of missingRequiredAssets) {
    console.log(`- ${asset}`);
  }
}

if (missingImages.length > 0) {
  console.log('\nMissing images:');
  for (const scene of missingImages) {
    console.log(`- ${scene.slug}.png  <- create from ${scene.image_prompt}`);
  }
}

const activePlatforms = new Set(
  manifest.scenes
    .map((scene) => scene.selected_video_prompt_platform)
    .filter(Boolean),
);
if (activePlatforms.size > 0) {
  const platformList = [...activePlatforms].join(', ');
  console.log(`\nVideo prompt platform: ${platformList}`);
  if ([...activePlatforms].every((platform) => platform.includes('from Runway') || platform === 'Runway')) {
    console.log('  Note: set VIDEO_PROMPT_PLATFORM=<tool> and re-run npm run manifest');
    console.log('  Available: Runway Kling Pika Luma Veo Flow Sora Hailuo PixVerse');
  }
}

const longScenes = manifest.scenes.filter((scene) => !scene.video_exists && scene.duration > 30);
if (longScenes.length > 0) {
  console.log('\nLong scenes (>30s): external video clips will loop in Remotion:');
  for (const scene of longScenes) {
    console.log(`  ${scene.slug}: ${scene.duration.toFixed(1)}s - generate multiple clips or expect looping`);
  }
}

if (optionalVideos.length > 0) {
  console.log('\nSource videos: not provided (OK)');
  for (const scene of optionalVideos) {
    const platform = scene.selected_video_prompt_platform ? ` [${scene.selected_video_prompt_platform}]` : '';
    console.log(`- ${scene.slug}.mp4 is not provided; Remotion will make a fallback animation from ${scene.image} and ${scene.video_prompt}${platform}`);
  }
}

const scenesNeedingVideo = manifest.scenes.filter((scene) => !scene.video_exists);
if (scenesNeedingVideo.length > 0 && scenesNeedingVideo.some((scene) => scene.video_gen_images?.length)) {
  console.log('\nVideo generation inputs (scenes without video):');
  for (const scene of scenesNeedingVideo) {
    const imgs = scene.video_gen_images || [];
    const readyCount = imgs.filter((img) => img.exists).length;
    const parts = imgs.map((img) => `${img.role}:${img.exists ? 'ready' : 'missing'}`).join(' ');
    console.log(`  ${scene.slug}: ${readyCount}/${imgs.length} images ready [${parts}]`);
    if (readyCount < imgs.length) {
      for (const img of imgs.filter((i) => !i.exists)) {
        if (img.role === 'character') {
          console.log('    character <- prompts/image_prompts/00_character_turnaround_model_sheet.md');
        } else {
          console.log(`    scene     <- ${scene.image_prompt}`);
        }
      }
    }
  }
}

if (missingImages.length === 0 && optionalVideos.length === 0) {
  console.log('\nOK: all assets are ready.');
} else if (missingImages.length === 0) {
  console.log('\nOK: render can run from images and selected video prompts.');
} else {
  console.log('\nRender needs scene images. Source videos are optional.');
}

if (missingRequiredAssets.length > 0 || (missingImages.length > 0 && !allowPlaceholders)) {
  if (missingImages.length > 0 && !allowPlaceholders) {
    console.log('\nUse -- --allow-placeholders to intentionally render placeholder scenes.');
  }
  process.exit(1);
}
