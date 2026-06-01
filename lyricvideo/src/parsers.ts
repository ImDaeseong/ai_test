import {TIMING_CONFIG} from './config';

export interface LyricLine {
  readonly id: string;
  readonly start: number;
  readonly end: number;
  readonly text: string;
}

export interface TimingEntry {
  readonly start: number;
  readonly end?: number;
  readonly text: string;
}

export interface ParserResult {
  readonly source: 'lrc' | 'srt';
  readonly lines: LyricLine[];
  readonly durationSeconds: number;
}

const DEFAULT_LINE_SECONDS = 3.2;
// 비디오 총 길이: 마지막 가사 종료 + 여백 + 페이드 (config.ts에서 일원화 관리)
const OUTRO_TOTAL_SECONDS = TIMING_CONFIG.outroSeconds + TIMING_CONFIG.outroBufferSeconds;

const stripLyricDirectives = (text: string): string => text.replace(/\[[^\]]+\]/g, ' ');

const normalizeText = (text: string): string =>
  stripLyricDirectives(text)
    .replace(/\r/g, '')
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
    .join(' ');

const secondsFromLrcStamp = (stamp: string): number | null => {
  const match = /^(?<minutes>\d{1,3}):(?<seconds>\d{2})(?:[.:](?<fraction>\d{1,3}))?$/.exec(stamp);
  if (!match?.groups) {
    return null;
  }

  const minutes = Number(match.groups.minutes);
  const seconds = Number(match.groups.seconds);
  const fraction = match.groups.fraction ?? '0';
  const milliseconds = Number(fraction.padEnd(3, '0').slice(0, 3));

  if (!Number.isFinite(minutes) || !Number.isFinite(seconds) || seconds >= 60) {
    return null;
  }

  return minutes * 60 + seconds + milliseconds / 1000;
};

const secondsFromSrtStamp = (stamp: string): number | null => {
  const match =
    /^(?<hours>\d{2}):(?<minutes>\d{2}):(?<seconds>\d{2}),(?<milliseconds>\d{3})$/.exec(stamp.trim());
  if (!match?.groups) {
    return null;
  }

  const hours = Number(match.groups.hours);
  const minutes = Number(match.groups.minutes);
  const seconds = Number(match.groups.seconds);
  const milliseconds = Number(match.groups.milliseconds);

  if (
    !Number.isFinite(hours) ||
    !Number.isFinite(minutes) ||
    !Number.isFinite(seconds) ||
    minutes >= 60 ||
    seconds >= 60
  ) {
    return null;
  }

  return hours * 3600 + minutes * 60 + seconds + milliseconds / 1000;
};

const finalizeEntries = (entries: TimingEntry[], source: ParserResult['source']): ParserResult => {
  const sorted = [...entries]
    .map((entry) => ({...entry, text: normalizeText(entry.text)}))
    .filter((entry) => entry.text.length > 0)
    .sort((a, b) => a.start - b.start);

  const lines: LyricLine[] = sorted.map((entry, index) => {
    const nextStart = sorted[index + 1]?.start;
    const inferredEnd = nextStart ?? entry.start + DEFAULT_LINE_SECONDS;
    const end = Math.max(entry.end ?? inferredEnd, entry.start + 0.35);

    return {
      id: `${source}-${index}-${entry.start.toFixed(3)}`,
      start: entry.start,
      end,
      text: entry.text,
    };
  });

  const latestEnd = lines.reduce((latest, line) => Math.max(latest, line.end), 0);

  return {
    source,
    lines,
    durationSeconds: Math.max(10, latestEnd + OUTRO_TOTAL_SECONDS),
  };
};

export const parseLrc = (content: string): ParserResult => {
  const entries: TimingEntry[] = [];

  for (const rawLine of content.replace(/^\uFEFF/, '').split(/\r?\n/)) {
    const stamps = [...rawLine.matchAll(/\[(\d{1,3}:\d{2}(?:[.:]\d{1,3})?)\]/g)];
    if (stamps.length === 0) {
      continue;
    }

    const text = rawLine.replace(/\[(?:\d{1,3}:\d{2}(?:[.:]\d{1,3})?|[a-zA-Z]+:.*?)\]/g, '').trim();

    for (const stamp of stamps) {
      const start = secondsFromLrcStamp(stamp[1] ?? '');
      if (start !== null) {
        entries.push({start, text});
      }
    }
  }

  return finalizeEntries(entries, 'lrc');
};

export const parseSrt = (content: string): ParserResult => {
  const entries: TimingEntry[] = [];
  const blocks = content.replace(/^\uFEFF/, '').replace(/\r/g, '').split(/\n{2,}/);

  for (const block of blocks) {
    const lines = block
      .split('\n')
      .map((line) => line.trim())
      .filter(Boolean);
    const timingIndex = lines.findIndex((line) => line.includes('-->'));
    if (timingIndex === -1) {
      continue;
    }

    const [rawStart, rawEnd] = lines[timingIndex].split('-->').map((part) => part.trim());
    const start = secondsFromSrtStamp(rawStart ?? '');
    const end = secondsFromSrtStamp((rawEnd ?? '').split(/\s+/)[0] ?? '');
    const text = lines.slice(timingIndex + 1).join('\n');

    if (start !== null && end !== null) {
      entries.push({start, end, text});
    }
  }

  return finalizeEntries(entries, 'srt');
};

export const parseLyrics = (input: {lrc?: string; srt?: string}): ParserResult => {
  if (input.lrc?.trim()) {
    const parsed = parseLrc(input.lrc);
    if (parsed.lines.length > 0) {
      return parsed;
    }
  }

  if (input.srt?.trim()) {
    const parsed = parseSrt(input.srt);
    if (parsed.lines.length > 0) {
      return parsed;
    }
  }

  throw new Error('No timed lyric lines were found in the provided LRC/SRT files.');
};
