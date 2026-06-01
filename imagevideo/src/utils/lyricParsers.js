import fs from 'node:fs/promises';
import path from 'node:path';
import {formatTimestamp} from './timecode.js';

export async function readLyricInput(filePath) {
  const extension = path.extname(filePath).toLowerCase();
  const raw = (await fs.readFile(filePath, 'utf8')).replace(/^\uFEFF/, '');

  if (extension === '.json') {
    return JSON.parse(raw);
  }

  if (extension === '.srt') {
    return {
      lyrics: parseSrt(raw).map((segment) => segment.lyric).join('\n'),
      timed_segments: parseSrt(raw),
      source_format: 'srt'
    };
  }

  if (extension === '.lrc') {
    const timedSegments = parseLrc(raw);
    return {
      lyrics: timedSegments.map((segment) => segment.lyric).join('\n'),
      timed_segments: timedSegments,
      source_format: 'lrc'
    };
  }

  throw new Error(`Unsupported lyric input format: ${extension}`);
}

export function parseSrt(raw) {
  const blocks = raw.replace(/\r/g, '').split(/\n{2,}/);
  const segments = [];

  for (const block of blocks) {
    const lines = block.split('\n').map((line) => line.trim()).filter(Boolean);
    if (lines.length < 2) {
      continue;
    }

    const timeLineIndex = lines.findIndex((line) => line.includes('-->'));
    if (timeLineIndex === -1) {
      continue;
    }

    const [startRaw, endRaw] = lines[timeLineIndex].split('-->').map((part) => part.trim().split(/\s+/)[0]);
    const lyric = lines.slice(timeLineIndex + 1).join(' ').trim();
    const startSeconds = parseSrtTimestamp(startRaw);
    const endSeconds = parseSrtTimestamp(endRaw);

    if (!lyric || isMetadataLyric(lyric) || startSeconds === null || endSeconds === null || endSeconds <= startSeconds) {
      continue;
    }

    segments.push({
      start: formatTimestamp(startSeconds),
      end: formatTimestamp(endSeconds),
      duration: Number((endSeconds - startSeconds).toFixed(3)),
      lyric
    });
  }

  return segments;
}

export function parseLrc(raw) {
  const lines = raw.replace(/\r/g, '').split('\n');
  const points = [];

  for (const line of lines) {
    const matches = [...line.matchAll(/\[(\d{1,2}):(\d{2})(?:\.(\d{1,3}))?\]/g)];
    const lyric = line.replace(/\[[^\]]+\]/g, '').trim();

    if (!matches.length || !lyric || isMetadataLyric(lyric)) {
      continue;
    }

    for (const match of matches) {
      const minutes = Number(match[1]);
      const seconds = Number(match[2]);
      const fraction = match[3] ?? '0';
      const milliseconds = Number(fraction.padEnd(3, '0').slice(0, 3));
      points.push({
        seconds: minutes * 60 + seconds + milliseconds / 1000,
        lyric
      });
    }
  }

  points.sort((a, b) => a.seconds - b.seconds);

  return points.map((point, index) => {
    const next = points[index + 1];
    const endSeconds = next ? Math.max(next.seconds, point.seconds + 0.25) : point.seconds + 4;
    return {
      start: formatTimestamp(point.seconds),
      end: formatTimestamp(endSeconds),
      duration: Number((endSeconds - point.seconds).toFixed(3)),
      lyric: point.lyric
    };
  });
}

function isMetadataLyric(value) {
  return /^\[[^\]]+\]$/.test(value.trim());
}

function parseSrtTimestamp(value) {
  const match = value?.match(/^(\d{1,2}):(\d{2}):(\d{2})[,.](\d{1,3})$/);
  if (!match) {
    return null;
  }

  const [, hours, minutes, seconds, milliseconds] = match;
  return (
    Number(hours) * 3600 +
    Number(minutes) * 60 +
    Number(seconds) +
    Number(milliseconds.padEnd(3, '0').slice(0, 3)) / 1000
  );
}
