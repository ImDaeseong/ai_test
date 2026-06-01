import fs from 'node:fs/promises';
import path from 'node:path';

const AUDIO_EXTENSIONS = new Set(['.mp3', '.wav']);
const LYRIC_EXTENSIONS = new Set(['.json', '.srt', '.lrc']);
const BACKGROUND_IMAGE_EXTENSIONS = new Set(['.png', '.jpg', '.jpeg', '.webp']);
const BACKGROUND_VIDEO_EXTENSIONS = new Set(['.mp4', '.mov', '.webm', '.avi', '.mkv']);

export async function discoverInputFiles(inputDir = 'input') {
  const absoluteInputDir = path.resolve(process.cwd(), inputDir);
  let entries;

  try {
    entries = await fs.readdir(absoluteInputDir, {withFileTypes: true});
  } catch (error) {
    if (error.code === 'ENOENT') {
      throw new Error(`Input directory does not exist: ${absoluteInputDir}`);
    }

    throw error;
  }

  const files = entries
    .filter((entry) => entry.isFile())
    .map((entry) => path.join(absoluteInputDir, entry.name));

  return {
    lyrics: pickLyricFile(files),
    audio: pickFirstByExtensions(files, AUDIO_EXTENSIONS),
    backgroundImage: pickFirstByExtensions(files, BACKGROUND_IMAGE_EXTENSIONS),
    backgroundVideo: pickFirstByExtensions(files, BACKGROUND_VIDEO_EXTENSIONS)
  };
}

function pickLyricFile(files) {
  const byName = files.find((file) => path.basename(file).toLowerCase() === 'lyrics.json');
  if (byName) {
    return byName;
  }

  for (const extension of ['.srt', '.lrc', '.json']) {
    const match = files.find((file) => path.extname(file).toLowerCase() === extension);
    if (match) {
      return match;
    }
  }

  return null;
}

function pickFirstByExtensions(files, extensions) {
  return files.find((file) => extensions.has(path.extname(file).toLowerCase())) ?? null;
}

export function isAudioFile(filePath) {
  return AUDIO_EXTENSIONS.has(path.extname(filePath).toLowerCase());
}

export function isLyricFile(filePath) {
  return LYRIC_EXTENSIONS.has(path.extname(filePath).toLowerCase());
}

export function isBackgroundImageFile(filePath) {
  return BACKGROUND_IMAGE_EXTENSIONS.has(path.extname(filePath).toLowerCase());
}

export function isBackgroundVideoFile(filePath) {
  return BACKGROUND_VIDEO_EXTENSIONS.has(path.extname(filePath).toLowerCase());
}
