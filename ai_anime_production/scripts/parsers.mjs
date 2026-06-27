/**
 * parsers.mjs — 씬 프롬프트 마크다운에서 값을 추출하는 순수 함수 모음
 * import_input.mjs에서 분리하여 단위 테스트 가능하게 만든 모듈.
 */

export const SCENE_BASENAME_RE = /^scene_(\d+)_(.+)$/i;
export const DEFAULT_DURATION_SECONDS = 30;

export function sceneNum(base) {
  const m = base.match(SCENE_BASENAME_RE);
  return m ? parseInt(m[1], 10) : 999;
}

export function sectionName(base) {
  const m = base.match(SCENE_BASENAME_RE);
  return m ? m[2].replace(/_/g, ' ') : base;
}

export function extractTitle(content) {
  const m = content.match(/^#\s+(.+?)$/m);
  return m ? m[1].trim() : null;
}

export function extractBpm(content) {
  const m = content.match(/\b(\d+)\s*BPM\b/i);
  return m ? parseInt(m[1], 10) : null;
}

export function extractDuration(content) {
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

export function extractIntensity(content) {
  const keywords = 'emotional\\s+peak|medium[-\\s]?high|medium|low|high|rising|falling|subtle';
  const m = content.match(new RegExp(`\\bintensity[:\\s=]+\\s*(${keywords})\\b`, 'i'));
  return m ? m[1].trim().toLowerCase() : '';
}

export function extractCameraDirection(content) {
  const m = content.match(/Camera\s+(?:motion|direction|move|movement)\s*:\s*([^\n;]+)/i)
    ?? content.match(/Camera\s*:\s*([^\n;]+)/i);
  if (!m) return '';
  return m[1].split(/[;,]/)[0].trim();
}
