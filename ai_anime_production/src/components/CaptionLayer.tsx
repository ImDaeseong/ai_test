import React, {useEffect, useMemo, useState} from 'react';
import {
  AbsoluteFill,
  cancelRender,
  continueRender,
  delayRender,
  staticFile,
  useCurrentFrame,
} from 'remotion';

type Caption = {
  start: number;
  end: number;
  text: string;
};

type Props = {
  src: string;
  fps: number;
};

export const CaptionLayer: React.FC<Props> = ({src, fps}) => {
  const frame = useCurrentFrame();
  const [captions, setCaptions] = useState<Caption[]>([]);
  const [handle] = useState(() => delayRender('Loading subtitles'));

  useEffect(() => {
    fetch(staticFile(src))
      .then((response) => {
        if (!response.ok) {
          throw new Error(`Failed to load subtitles: ${src} (${response.status})`);
        }
        return response.text();
      })
      .then((text) => setCaptions(parseSrt(text)))
      .then(() => continueRender(handle))
      .catch((error) => cancelRender(error));
  }, [handle, src]);

  const time = frame / fps;
  const active = useMemo(
    () => captions.find((caption) => time >= caption.start && time < caption.end),
    [captions, time],
  );

  if (!active?.text) {
    return null;
  }

  return (
    <AbsoluteFill
      style={{
        justifyContent: 'flex-end',
        alignItems: 'center',
        paddingBottom: 96,
        pointerEvents: 'none',
      }}
    >
      <div
        style={{
          maxWidth: 1320,
          padding: '18px 34px',
          color: '#f8f8fb',
          fontFamily: 'Arial, sans-serif',
          fontSize: 46,
          fontWeight: 800,
          lineHeight: 1.18,
          textAlign: 'center',
          textShadow: '0 3px 18px rgba(0,0,0,0.9), 0 0 12px rgba(255,0,90,0.45)',
          whiteSpace: 'pre-wrap',
        }}
      >
        {active.text}
      </div>
    </AbsoluteFill>
  );
};

function parseSrt(input: string): Caption[] {
  const captions = input
    .replace(/\r/g, '')
    .split(/\n\n+/)
    .map((block) => {
      const lines = block.split('\n').filter(Boolean);
      const timingLine = lines.find((line) => line.includes('-->'));
      if (!timingLine) {
        return null;
      }
      const [startRaw, endRaw] = timingLine.split('-->').map((part) => part.trim());
      const text = lines.slice(lines.indexOf(timingLine) + 1).join('\n').trim();
      const start = parseTimestamp(startRaw);
      const end = parseTimestamp(endRaw);

      if (end <= start) {
        throw new Error(`Invalid subtitle timing: ${timingLine}`);
      }

      return {start, end, text};
    })
    .filter((caption): caption is Caption => Boolean(caption));

  return captions;
}

function parseTimestamp(value: string): number {
  const match = value.match(/^(\d+):(\d{2}):(\d{2}),(\d{1,3})$/);
  if (!match) {
    throw new Error(`Invalid subtitle timestamp: ${value}`);
  }
  const [, hours, minutes, seconds, millis] = match;
  return (
    Number(hours) * 3600 +
    Number(minutes) * 60 +
    Number(seconds) +
    Number(millis.padEnd(3, '0')) / 1000
  );
}
