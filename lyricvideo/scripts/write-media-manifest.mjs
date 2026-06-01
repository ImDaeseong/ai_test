import {readdir, readFile, writeFile} from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const projectDir = path.resolve(scriptDir, '..');
const mediaDir = path.join(projectDir, 'public', 'media');
const manifestPath = path.join(projectDir, 'src', 'mediaManifest.ts');
const audioExtensions = new Set(['.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a']);
const lyricExtensions = new Set(['.lrc', '.srt']);
const imageExtensions = new Set(['.jpg', '.jpeg', '.png', '.webp']);
const videoExtensions = new Set(['.mp4', '.mov', '.webm']);

const readMediaFiles = async () => {
  try {
    return await readdir(mediaDir, {withFileTypes: true});
  } catch {
    return [];
  }
};

const readMeta = async () => {
  try {
    const raw = await readFile(path.join(mediaDir, 'meta.json'), 'utf8');
    const parsed = JSON.parse(raw);
    return {
      title: typeof parsed.title === 'string' && parsed.title.trim() ? parsed.title.trim() : null,
      artist: typeof parsed.artist === 'string' && parsed.artist.trim() ? parsed.artist.trim() : null,
    };
  } catch {
    return {title: null, artist: null};
  }
};

const scoreImage = (fileName) => {
  const lower = fileName.toLowerCase();
  if (lower.startsWith('background.')) return 0;
  if (lower.startsWith('bg.')) return 1;
  if (lower.includes('background')) return 2;
  if (lower.includes('bg')) return 3;
  return 4;
};

const scoreAudio = (fileName) => {
  const lower = fileName.toLowerCase();
  if (lower === 'audio.mp3') return 0;
  if (lower === 'audio.wav') return 1;
  return 2;
};

const scoreLyric = (fileName) => {
  const lower = fileName.toLowerCase();
  if (lower === 'lyrics.lrc') return 0;
  if (lower.endsWith('.lrc')) return 1;
  if (lower === 'lyrics.srt') return 2;
  return 3;
};

const entries = await readMediaFiles();
const mediaFiles = entries.filter((entry) => entry.isFile()).map((entry) => entry.name);

const audioFile = mediaFiles
  .filter((fileName) => audioExtensions.has(path.extname(fileName).toLowerCase()))
  .sort((a, b) => {
    const delta = scoreAudio(a) - scoreAudio(b);
    return delta !== 0 ? delta : a.localeCompare(b);
  })[0];

const lyricFile = mediaFiles
  .filter((fileName) => lyricExtensions.has(path.extname(fileName).toLowerCase()))
  .sort((a, b) => {
    const delta = scoreLyric(a) - scoreLyric(b);
    return delta !== 0 ? delta : a.localeCompare(b);
  })[0];

const backgroundVideo = mediaFiles
  .filter((fileName) => videoExtensions.has(path.extname(fileName).toLowerCase()))
  .sort((a, b) => {
    const delta = scoreImage(a) - scoreImage(b);
    return delta !== 0 ? delta : a.localeCompare(b);
  })[0];

const backgroundImage = mediaFiles
  .filter((fileName) => imageExtensions.has(path.extname(fileName).toLowerCase()))
  .sort((a, b) => {
    const delta = scoreImage(a) - scoreImage(b);
    return delta !== 0 ? delta : a.localeCompare(b);
  })[0];

const {title, artist} = await readMeta();

const backgroundKind =
  backgroundVideo !== undefined ? 'video' : backgroundImage !== undefined ? 'image' : 'none';
const backgroundFile = backgroundVideo ?? backgroundImage;
const audioSrc = audioFile === undefined ? null : `/media/${audioFile.replaceAll('\\', '/')}`;
const lyricSrc = lyricFile === undefined ? null : `/media/${lyricFile.replaceAll('\\', '/')}`;
const lyricKind = lyricFile === undefined ? null : path.extname(lyricFile).toLowerCase().slice(1);
const backgroundSrc =
  backgroundFile === undefined ? null : `/media/${backgroundFile.replaceAll('\\', '/')}`;

const source = `export const mediaManifest = {
  audioSrc: ${JSON.stringify(audioSrc)},
  lyricKind: ${JSON.stringify(lyricKind)},
  lyricSrc: ${JSON.stringify(lyricSrc)},
  backgroundKind: ${JSON.stringify(backgroundKind)},
  backgroundSrc: ${JSON.stringify(backgroundSrc)},
  title: ${JSON.stringify(title)},
  artist: ${JSON.stringify(artist)},
} as const;
`;

await writeFile(manifestPath, source, 'utf8');
console.log('mediaManifest.ts updated.');
