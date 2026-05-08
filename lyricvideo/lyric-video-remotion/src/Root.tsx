import React, {useEffect, useState} from 'react';
import {Composition, continueRender, delayRender, staticFile} from 'remotion';
import {getAudioDurationInSeconds} from '@remotion/media-utils';
import {LyricVideo} from './LyricVideo';
import {mediaManifest} from './mediaManifest';
import {parseLyrics, type ParserResult} from './parsers';

const FPS = 30;
const WIDTH = 1920;
const HEIGHT = 1080;

interface ProjectData {
  readonly parserResult: ParserResult;
  readonly audioDurationSeconds: number | null;
  readonly audioSrc: string;
  readonly backgroundKind: 'none' | 'image' | 'video';
  readonly backgroundSrc: string | null;
}

const fetchOptionalText = async (src: string): Promise<string | undefined> => {
  const response = await fetch(staticFile(src));
  if (!response.ok) {
    return undefined;
  }

  return response.text();
};

const resolveAudioSrc = async (): Promise<string> => {
  if (mediaManifest.audioSrc !== null) {
    return mediaManifest.audioSrc;
  }

  throw new Error('No audio file found. Add an MP3 or WAV file to public/media.');
};

const loadLyrics = async (): Promise<{readonly lrc?: string; readonly srt?: string}> => {
  if (mediaManifest.lyricSrc === null || mediaManifest.lyricKind === null) {
    return {};
  }

  const text = await fetchOptionalText(mediaManifest.lyricSrc);
  if (mediaManifest.lyricKind === 'lrc') {
    return {lrc: text};
  }

  return {srt: text};
};

const loadProjectData = async (): Promise<ProjectData> => {
  const [lyrics, audioSrc] = await Promise.all([
    loadLyrics(),
    resolveAudioSrc(),
  ]);
  const audioDurationSeconds = await getAudioDurationInSeconds(staticFile(audioSrc)).catch(() => null);

  return {
    parserResult: parseLyrics(lyrics),
    audioDurationSeconds,
    audioSrc,
    backgroundKind: mediaManifest.backgroundKind,
    backgroundSrc: mediaManifest.backgroundSrc,
  };
};

export const Root: React.FC = () => {
  const [handle] = useState(() => delayRender('Loading lyric timing and audio metadata'));
  const [data, setData] = useState<ProjectData | null>(null);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    loadProjectData()
      .then((loadedData) => {
        setData(loadedData);
        continueRender(handle);
      })
      .catch((caught: unknown) => {
        const normalizedError = caught instanceof Error ? caught : new Error(String(caught));
        setError(normalizedError);
        continueRender(handle);
      });
  }, [handle]);

  if (error) {
    throw error;
  }

  if (!data) {
    return null;
  }

  const durationSeconds = Math.max(
    data.parserResult.durationSeconds,
    data.audioDurationSeconds === null ? 0 : data.audioDurationSeconds + 1,
  );

  return (
    <Composition
      id="lyric-video"
      component={LyricVideo}
      durationInFrames={Math.ceil(durationSeconds * FPS)}
      fps={FPS}
      width={WIDTH}
      height={HEIGHT}
      defaultProps={{
        audioSrc: data.audioSrc,
        backgroundKind: data.backgroundKind,
        backgroundSrc: data.backgroundSrc,
        lyrics: data.parserResult.lines,
      }}
    />
  );
};
