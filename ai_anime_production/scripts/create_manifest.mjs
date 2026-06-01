import fs from 'node:fs';
import path from 'node:path';
import {paths, readJson, sceneSlug, toPublicAssetPath, writeJson} from './lib.mjs';

const preferredVideoPromptPlatform = process.env.VIDEO_PROMPT_PLATFORM || 'Remotion';
const songMasterFile = path.join(paths.sourceDir, 'song_master.json');
const sceneListFile = path.join(paths.sourceDir, 'scene_list.json');

const CHARACTER_IMAGE_CANDIDATES = [
  'character_reference.png',
  '00_character_turnaround_model_sheet.png',
];

function resolveCharacterImage({enabled = true} = {}) {
  if (!enabled) {
    return {path: null, exists: false};
  }
  for (const name of CHARACTER_IMAGE_CANDIDATES) {
    if (fs.existsSync(path.join(paths.publicAssets, 'images', name))) {
      return {path: toPublicAssetPath('images', name), exists: true};
    }
  }
  return {path: toPublicAssetPath('images', 'character_reference.png'), exists: false};
}

if (!fs.existsSync(songMasterFile) || !fs.existsSync(sceneListFile)) {
  console.error('Missing manifests/source/song_master.json or manifests/source/scene_list.json');
  console.error('Run: npm run import -- --from ../ai_anime');
  process.exit(1);
}

const songMaster = readJson(songMasterFile);
const sceneList = readJson(sceneListFile);
const duration = Number(songMaster.duration_seconds || songMaster.audio_analysis?.duration_seconds || 60);
const fps = 30;

function normalizeSection(value) {
  return String(value || '')
    .toLowerCase()
    .replaceAll('-', ' ')
    .replace(/\d+/g, '')
    .replace(/\s+/g, ' ')
    .trim();
}

function findSceneStarts() {
  // If every scene has an explicit duration_seconds, derive start times from those
  const hasDurations = sceneList.scenes.every((s) => Number(s.duration_seconds) > 0);
  if (hasDurations) {
    let time = 0;
    return sceneList.scenes.map((scene) => {
      const start = time;
      time += Number(scene.duration_seconds);
      return start;
    });
  }

  const timed = songMaster.timed_lyrics || [];
  let searchIndex = 0;
  return sceneList.scenes.map((scene, index) => {
    const wanted = normalizeSection(scene.music_section);
    for (let i = searchIndex; i < timed.length; i += 1) {
      const text = String(timed[i].text || '');
      if (!text.startsWith('[') || !text.endsWith(']')) {
        continue;
      }
      const marker = normalizeSection(text.slice(1, -1));
      if (marker === wanted || marker.includes(wanted) || wanted.includes(marker)) {
        searchIndex = i + 1;
        return Number(timed[i].time || 0);
      }
    }
    return (duration / sceneList.scenes.length) * index;
  });
}

function parseSelectedPrompt(promptPath, preferredPlatform) {
  if (!fs.existsSync(promptPath)) {
    return {
      platform: '',
      text: '',
    };
  }

  const markdown = fs.readFileSync(promptPath, 'utf8').trim();
  const sections = [];
  let current = null;

  for (const line of markdown.split(/\r?\n/)) {
    const heading = line.match(/^##\s+(.+?)\s*$/);
    if (heading) {
      if (current) {
        current.text = current.lines.join('\n').trim();
        sections.push(current);
      }
      current = {
        platform: heading[1].trim(),
        lines: [],
        text: '',
      };
      continue;
    }

    if (current) {
      current.lines.push(line);
    }
  }

  if (current) {
    current.text = current.lines.join('\n').trim();
    sections.push(current);
  }

  if (sections.length === 0) {
    return {
      platform: 'default',
      text: markdown.replace(/^#\s+.+?\s*$/m, '').trim(),
    };
  }

  const preferred = sections.find(
    (section) => section.platform.toLowerCase() === preferredPlatform.toLowerCase(),
  );
  const runwayFallback = sections.find((section) => section.platform.toLowerCase() === 'runway');
  const selected = preferred || runwayFallback || sections[0];
  const selectedPlatform =
    !preferred && runwayFallback && preferredPlatform.toLowerCase() === 'remotion'
      ? 'Remotion (from Runway)'
      : selected.platform;

  return {
    platform: selectedPlatform,
    text: selected.text,
  };
}

const starts = findSceneStarts();
if (starts.length > 0 && starts[0] > 1) {
  starts[0] = 0;
}

const audioFile = songMaster.audio_files?.[0]?.file || '';
const audioPublicPath = audioFile ? toPublicAssetPath('audio', path.basename(audioFile)) : null;
const subtitlePath =
  songMaster.subtitle_enabled === false
    ? null
    : fs.existsSync(path.join(paths.publicAssets, 'subtitles', 'lyrics_clean.srt'))
      ? toPublicAssetPath('subtitles', 'lyrics_clean.srt')
      : fs.existsSync(path.join(paths.publicAssets, 'subtitles', 'lyrics_original.srt'))
        ? toPublicAssetPath('subtitles', 'lyrics_original.srt')
        : null;

const characterImg = resolveCharacterImage({
  enabled: songMaster.character_reference_enabled !== false,
});

const scenes = sceneList.scenes.map((scene, index) => {
  const slug = sceneSlug(scene);
  const start = Math.max(0, starts[index] ?? 0);
  const end = Math.max(start + 1, starts[index + 1] ?? duration);
  const imageFile = `${slug}.png`;
  const videoFile = `${slug}.mp4`;
  const imagePrompt = `prompts/image_prompts/${slug}.md`;
  const videoPrompt = `prompts/video_prompts/${slug}.md`;
  const selectedVideoPrompt = parseSelectedPrompt(
    path.join(paths.projectRoot, videoPrompt),
    preferredVideoPromptPlatform,
  );
  const sceneImagePath = toPublicAssetPath('images', imageFile);
  const imageExists = fs.existsSync(path.join(paths.publicAssets, 'images', imageFile));
  const videoExists = fs.existsSync(path.join(paths.publicAssets, 'videos', videoFile));

  const videoGenImages = [];
  if (characterImg.path) {
    videoGenImages.push({path: characterImg.path, exists: characterImg.exists, role: 'character'});
  }
  videoGenImages.push({path: sceneImagePath, exists: imageExists, role: 'scene'});

  return {
    scene_number: scene.scene_number,
    section: scene.music_section,
    slug,
    start,
    end,
    duration: end - start,
    start_frame: Math.round(start * fps),
    duration_frames: Math.max(1, Math.round((end - start) * fps)),
    image: sceneImagePath,
    image_exists: imageExists,
    video: toPublicAssetPath('videos', videoFile),
    video_exists: videoExists,
    image_prompt: imagePrompt,
    video_prompt: videoPrompt,
    selected_video_prompt_platform: selectedVideoPrompt.platform,
    selected_video_prompt: selectedVideoPrompt.text,
    video_gen_images: videoGenImages,
    camera_direction: scene.camera_direction || '',
    movement: scene.movement || '',
    intensity: scene.intensity || '',
    emotion: scene.emotion || '',
  };
});

writeJson(paths.manifest, {
  title: songMaster.title || sceneList.song_title || 'AI Anime Music Video',
  fps,
  width: 1920,
  height: 1080,
  duration_seconds: duration,
  duration_frames: Math.ceil(duration * fps),
  bpm: songMaster.bpm || null,
  audio: audioPublicPath,
  subtitles: subtitlePath,
  subtitle_note: subtitlePath?.includes('lyrics_original') ? 'Original subtitle file may need encoding cleanup.' : '',
  character_image: characterImg.path,
  character_image_exists: characterImg.exists,
  scenes,
});

console.log(`Wrote ${paths.manifest}`);
