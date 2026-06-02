import React, {useEffect, useState} from 'react';
import {Composition, continueRender, delayRender, staticFile} from 'remotion';
import {getAudioDurationInSeconds} from '@remotion/media-utils';
import {LyricVideo, type BackgroundKind} from './LyricVideo';
import {VIDEO_CONFIG, VIDEO_CONFIG_VERTICAL} from './config';
import {mediaManifest} from './mediaManifest';
import {parseLyrics, type ParserResult} from './parsers';


interface ProjectData {
  readonly parserResult: ParserResult;
  readonly audioDurationSeconds: number | null;
  readonly audioSrc: string;
  readonly backgroundKind: BackgroundKind;
  readonly backgroundSrc: string | null;
  readonly title: string | null;
  readonly artist: string | null;
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
  if (text === undefined) {
    return {};
  }
  if (mediaManifest.lyricKind === 'lrc') {
    return {lrc: text};
  }

  return {srt: text};
};

const loadProjectData = async (): Promise<ProjectData> => {
  const [lyrics, audioSrc] = await Promise.all([loadLyrics(), resolveAudioSrc()]);
  const audioDurationSeconds = await getAudioDurationInSeconds(staticFile(audioSrc)).catch(
    () => null,
  );

  return {
    parserResult: parseLyrics(lyrics),
    audioDurationSeconds,
    audioSrc,
    backgroundKind: mediaManifest.backgroundKind,
    backgroundSrc: mediaManifest.backgroundSrc,
    title: mediaManifest.title,
    artist: mediaManifest.artist,
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

  const durationInFrames = Math.ceil(durationSeconds * VIDEO_CONFIG.fps);
  const sharedProps = {
    audioSrc: data.audioSrc,
    backgroundKind: data.backgroundKind,
    backgroundSrc: data.backgroundSrc,
    lyrics: data.parserResult.lines,
    title: data.title,
    artist: data.artist,
  };

  return (
    <>
      <Composition
        id="lyric-video"
        component={LyricVideo}
        durationInFrames={durationInFrames}
        fps={VIDEO_CONFIG.fps}
        width={VIDEO_CONFIG.width}
        height={VIDEO_CONFIG.height}
        defaultProps={{...sharedProps, vertical: false}}
      />
      <Composition
        id="lyric-video-vertical"
        component={LyricVideo}
        durationInFrames={durationInFrames}
        fps={VIDEO_CONFIG_VERTICAL.fps}
        width={VIDEO_CONFIG_VERTICAL.width}
        height={VIDEO_CONFIG_VERTICAL.height}
        defaultProps={{...sharedProps, vertical: true}}
      />
    </>
  );
};
