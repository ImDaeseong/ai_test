import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

export const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

export const paths = {
  projectRoot,
  sourceDir: path.join(projectRoot, 'manifests', 'source'),
  manifest: path.join(projectRoot, 'manifests', 'render_manifest.json'),
  publicAssets: path.join(projectRoot, 'public', 'assets'),
  prompts: path.join(projectRoot, 'prompts'),
  finalOutput: path.join(projectRoot, 'output', 'final'),
};

export function ensureDir(dir) {
  fs.mkdirSync(dir, {recursive: true});
}

export function readJson(file) {
  return JSON.parse(fs.readFileSync(file, 'utf8'));
}

export function writeJson(file, data) {
  ensureDir(path.dirname(file));
  fs.writeFileSync(file, `${JSON.stringify(data, null, 2)}\n`, 'utf8');
}

export function copyFileIfExists(source, target) {
  if (!source || !fs.existsSync(source)) {
    return false;
  }
  ensureDir(path.dirname(target));
  fs.copyFileSync(source, target);
  return true;
}

export function copyDirIfExists(source, target) {
  if (!fs.existsSync(source)) {
    return false;
  }
  ensureDir(target);
  fs.cpSync(source, target, {recursive: true});
  return true;
}

export function slugify(value) {
  return String(value)
    .normalize('NFC')
    .replace(/[^\p{Letter}\p{Number}\s_-]/gu, '')
    .trim()
    .replace(/[-\s]+/g, '_')
    .toLowerCase() || 'scene';
}

export function sceneSlug(scene) {
  return `scene_${String(scene.scene_number).padStart(2, '0')}_${slugify(scene.music_section || 'scene')}`;
}

export function parseArgs(argv) {
  const args = {};
  for (let i = 0; i < argv.length; i += 1) {
    const item = argv[i];
    if (!item.startsWith('--')) {
      continue;
    }
    const key = item.slice(2);
    const next = argv[i + 1];
    if (!next || next.startsWith('--')) {
      args[key] = true;
    } else {
      args[key] = next;
      i += 1;
    }
  }
  return args;
}

export function findFileRecursive(root, filename) {
  if (!fs.existsSync(root)) {
    return null;
  }
  const stack = [root];
  while (stack.length > 0) {
    const current = stack.pop();
    const entries = fs.readdirSync(current, {withFileTypes: true});
    for (const entry of entries) {
      const fullPath = path.join(current, entry.name);
      if (entry.isDirectory()) {
        stack.push(fullPath);
      } else if (entry.name === filename) {
        return fullPath;
      }
    }
  }
  return null;
}

export function toPublicAssetPath(...parts) {
  return path.posix.join('assets', ...parts.map((part) => String(part).replaceAll(path.sep, '/')));
}
