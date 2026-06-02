import React from 'react';
import {
  AbsoluteFill,
  Html5Audio,
  Img,
  interpolate,
  Sequence,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
  Video,
} from 'remotion';
import {useAudioData, visualizeAudio} from '@remotion/media-utils';
import type {LyricLine} from './parsers';
import {FONT_FAMILY, LYRIC_STYLE, TIMING_CONFIG, WAVEFORM_STYLE} from './config';

export type BackgroundKind = 'none' | 'image' | 'video';

export interface LyricVideoProps extends Record<string, unknown> {
  readonly audioSrc: string;
  readonly backgroundKind: BackgroundKind;
  readonly backgroundSrc: string | null;
  readonly lyrics: LyricLine[];
  readonly title: string | null;
  readonly artist: string | null;
  readonly vertical?: boolean;
}

const SPIKE_INDICES = Array.from({length: WAVEFORM_STYLE.numSpikes}, (_, i) => i);
const PARTICLE_INDICES = Array.from({length: WAVEFORM_STYLE.numParticles}, (_, i) => i);

const findActiveIndex = (lyrics: readonly LyricLine[], timeSeconds: number): number => {
  if (lyrics.length === 0) return -1;
  const exact = lyrics.findIndex((line) => timeSeconds >= line.start && timeSeconds < line.end);
  if (exact !== -1) return exact;
  // 아직 첫 가사 전이면 -1, 모든 가사 지났으면 마지막 인덱스
  if (timeSeconds < lyrics[0]!.start) return -1;
  const nextIndex = lyrics.findIndex((line) => timeSeconds < line.start);
  return nextIndex === -1 ? lyrics.length - 1 : nextIndex - 1;
};

const useCurrentLineStyle = (line: LyricLine | undefined) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  if (!line) return {opacity: 0, filter: 'blur(2px)'};

  const t = frame / fps;
  const fade = Math.min(0.24, Math.max(0.08, (line.end - line.start) * 0.18));
  const opacity = interpolate(
    t,
    [line.start, line.start + fade, line.end - fade, line.end],
    [0, 1, 1, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );
  const blur = interpolate(opacity, [0, 1], [1.4, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return {opacity, filter: `blur(${blur}px)`};
};

// 이전/현재/다음 3줄을 동시 표시 — 현재 줄만 완전 밝음, 나머지는 희미하게
const LyricDisplay: React.FC<{
  readonly prev: LyricLine | undefined;
  readonly current: LyricLine | undefined;
  readonly next: LyricLine | undefined;
  readonly vertical?: boolean;
}> = ({prev, current, next, vertical = false}) => {
  const currentStyle = useCurrentLineStyle(current);

  const sharedBase: React.CSSProperties = {
    width: 'min(1260px, 90vw)',
    textAlign: 'center',
    overflowWrap: 'anywhere',
    lineHeight: 1.3,
    transition: 'opacity 0.2s',
  };

  return (
    <div
      style={{
        position: 'absolute',
        left: '50%',
        top: vertical ? '72%' : `${LYRIC_STYLE.containerTopPercent}%`,
        transform: 'translateX(-50%)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: LYRIC_STYLE.lineGap,
      }}
    >
      <div
        style={{
          ...sharedBase,
          fontSize: vertical ? 'clamp(18px, 3vw, 36px)' : LYRIC_STYLE.contextFontSize,
          fontWeight: LYRIC_STYLE.contextFontWeight,
          color: LYRIC_STYLE.prevColor,
          opacity: prev ? 1 : 0,
          textShadow: LYRIC_STYLE.contextTextShadow,
        }}
      >
        {prev?.text ?? ''}
      </div>
      <div
        style={{
          ...sharedBase,
          fontSize: vertical ? 'clamp(30px, 5.5vw, 60px)' : LYRIC_STYLE.currentFontSize,
          fontWeight: LYRIC_STYLE.currentFontWeight,
          color: LYRIC_STYLE.currentColor,
          textShadow: LYRIC_STYLE.currentTextShadow,
          willChange: 'opacity, filter',
          ...currentStyle,
        }}
      >
        {current?.text ?? ''}
      </div>
      <div
        style={{
          ...sharedBase,
          fontSize: vertical ? 'clamp(18px, 3vw, 36px)' : LYRIC_STYLE.contextFontSize,
          fontWeight: LYRIC_STYLE.contextFontWeight,
          color: LYRIC_STYLE.nextColor,
          opacity: next ? 1 : 0,
          textShadow: LYRIC_STYLE.contextTextShadow,
        }}
      >
        {next?.text ?? ''}
      </div>
    </div>
  );
};

const BackgroundOverlays: React.FC = () => (
  <>
    <div
      style={{
        position: 'absolute',
        inset: 0,
        background:
          'linear-gradient(180deg, rgba(4, 7, 14, 0.28), rgba(4, 7, 14, 0.12) 42%, rgba(4, 7, 14, 0.72))',
      }}
    />
    <div
      style={{
        position: 'absolute',
        inset: 0,
        background:
          'radial-gradient(circle at 50% 74%, rgba(0, 0, 0, 0.05), rgba(0, 0, 0, 0.4) 72%)',
      }}
    />
  </>
);

const AnimatedBackground: React.FC<{
  readonly backgroundKind: BackgroundKind;
  readonly backgroundSrc: string | null;
}> = ({backgroundKind, backgroundSrc}) => {
  const frame = useCurrentFrame();
  const drift = Math.sin(frame / 150) * 18;
  const pulse = 0.18 + Math.sin(frame / 90) * 0.03;

  if (backgroundKind === 'video' && backgroundSrc !== null) {
    return (
      <>
        {/* OffthreadVideo는 loop 미지원 — 배경 전용이므로 frame 정확도 불필요, Video로 교체 */}
        <Video
          src={staticFile(backgroundSrc)}
          loop
          muted
          volume={0}
          style={{
            position: 'absolute',
            inset: 0,
            width: '100%',
            height: '100%',
            objectFit: 'cover',
            filter: 'brightness(0.62) saturate(0.9)',
          }}
        />
        <BackgroundOverlays />
      </>
    );
  }

  if (backgroundKind === 'image' && backgroundSrc !== null) {
    const gentleZoom = 1.035 + Math.sin(frame / 260) * 0.006;

    return (
      <>
        <Img
          src={staticFile(backgroundSrc)}
          style={{
            position: 'absolute',
            inset: 0,
            width: '100%',
            height: '100%',
            objectFit: 'cover',
            transform: `scale(${gentleZoom})`,
            filter: 'brightness(0.62) saturate(0.9)',
          }}
        />
        <BackgroundOverlays />
      </>
    );
  }

  return (
    <>
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background: 'linear-gradient(135deg, #121820 0%, #19242b 46%, #151a22 100%)',
        }}
      />
      <div
        style={{
          position: 'absolute',
          inset: '-12%',
          background:
            'linear-gradient(115deg, transparent 0%, rgba(126, 199, 190, 0.1) 34%, transparent 62%)',
          opacity: 0.58,
          transform: `translateX(${drift}px) rotate(${frame / 520}deg)`,
        }}
      />
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background:
            'repeating-linear-gradient(90deg, rgba(190,232,224,0.028) 0px, rgba(190,232,224,0.028) 1px, transparent 1px, transparent 82px), repeating-linear-gradient(0deg, rgba(190,232,224,0.018) 0px, rgba(190,232,224,0.018) 1px, transparent 1px, transparent 82px)',
          opacity: pulse,
          transform: `translate3d(${-(frame % 82)}px, ${-(frame % 82)}px, 0)`,
        }}
      />
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background:
            'linear-gradient(180deg, rgba(4, 7, 14, 0.12), transparent 42%, rgba(4, 7, 14, 0.66))',
        }}
      />
    </>
  );
};

const MusicWaveform: React.FC<{readonly audioSrc: string; readonly vertical?: boolean}> = ({audioSrc, vertical = false}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const audioData = useAudioData(staticFile(audioSrc));

  const width = vertical ? 480 : WAVEFORM_STYLE.width;
  const {height} = WAVEFORM_STYLE;
  const topPercent = vertical ? 88 : WAVEFORM_STYLE.topPercent;
  const centerY = height / 2;

  // Real frequency data per frame; falls back to silence while audio loads
  const lineData = audioData
    ? visualizeAudio({fps, frame, audioData, numberOfSamples: WAVEFORM_STYLE.numLineSamples, smoothing: true})
    : new Array(WAVEFORM_STYLE.numLineSamples).fill(0) as number[];

  // Downsample line data for spike bars
  const barAmplitude = (spike: number): number => {
    const idx = Math.floor((spike / (SPIKE_INDICES.length - 1)) * (WAVEFORM_STYLE.numLineSamples - 1));
    return lineData[idx] ?? 0;
  };

  const linePoints = lineData
    .map((amp, index) => {
      const x = (index / (WAVEFORM_STYLE.numLineSamples - 1)) * width;
      const y = centerY - amp * 32;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(' ');

  return (
    <div
      style={{
        position: 'absolute',
        left: '50%',
        top: `${topPercent}%`,
        width,
        height,
        marginLeft: -(width / 2),
        opacity: WAVEFORM_STYLE.opacity,
      }}
    >
      <svg
        viewBox={`0 0 ${width} ${height}`}
        width="100%"
        height="100%"
        preserveAspectRatio="none"
        style={{overflow: 'visible'}}
      >
        <defs>
          <linearGradient id="waveSoft" x1="0" x2="1" y1="0" y2="0">
            <stop offset="0%" stopColor="rgba(68, 214, 224, 0.3)" />
            <stop offset="18%" stopColor="rgba(82, 226, 232, 0.92)" />
            <stop offset="50%" stopColor="rgba(170, 242, 235, 0.78)" />
            <stop offset="82%" stopColor="rgba(82, 226, 232, 0.78)" />
            <stop offset="100%" stopColor="rgba(68, 214, 224, 0.28)" />
          </linearGradient>
          <filter id="waveGlow" x="-20%" y="-80%" width="140%" height="260%">
            <feGaussianBlur stdDeviation="2.2" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>
        <line
          x1={0}
          y1={centerY}
          x2={width}
          y2={centerY}
          stroke="rgba(154, 232, 226, 0.22)"
          strokeWidth={1}
        />
        {SPIKE_INDICES.map((spike) => {
          const x = (spike / (SPIKE_INDICES.length - 1)) * width;
          const amplitude = barAmplitude(spike);
          const jitter = Math.sin(spike * 2.1 + frame * 0.11) * 2;
          const spikeHeight = 4 + amplitude * 52 + Math.max(0, jitter);

          return (
            <line
              key={spike}
              x1={x}
              y1={centerY - spikeHeight / 2}
              x2={x}
              y2={centerY + spikeHeight / 2}
              stroke="rgba(97, 225, 231, 0.42)"
              strokeWidth={spike % 7 === 0 ? 1.5 : 0.9}
              strokeLinecap="round"
            />
          );
        })}
        <polyline
          points={linePoints}
          fill="none"
          stroke="url(#waveSoft)"
          strokeWidth={1.9}
          strokeLinejoin="round"
          strokeLinecap="round"
          filter="url(#waveGlow)"
        />
        {PARTICLE_INDICES.map((particle) => {
          const x = ((particle * 37 + frame * 0.28) % 100) / 100;
          const cluster = Math.sin(particle * 1.7) * 0.5 + 0.5;
          const cx = x * width;
          const cy = centerY + (cluster - 0.5) * 42 + Math.sin(frame * 0.025 + particle) * 5;
          const opacity = 0.12 + (Math.sin(frame * 0.05 + particle * 1.4) * 0.5 + 0.5) * 0.28;

          return (
            <circle
              key={particle}
              cx={cx}
              cy={cy}
              r={particle % 4 === 0 ? 1.5 : 1}
              fill="rgba(185, 244, 240, 0.72)"
              opacity={opacity}
            />
          );
        })}
      </svg>
    </div>
  );
};

// 배경을 그대로 유지한 채 곡 정보만 오버레이 — 배경이 곡마다 달라 자연스럽게 개성이 생김
const IntroOverlay: React.FC<{
  readonly title: string;
  readonly artist: string;
}> = ({title, artist}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t = frame / fps;

  const opacity = interpolate(
    t,
    [0, 0.5, TIMING_CONFIG.introSeconds - 0.8, TIMING_CONFIG.introSeconds],
    [0, 1, 1, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  const translateY = spring({
    fps,
    frame,
    config: {damping: 14, stiffness: 100, mass: 0.8},
    from: 20,
    to: 0,
  });

  return (
    <>
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background: 'rgba(0, 0, 0, 0.42)',
          opacity,
        }}
      />
      <div
        style={{
          position: 'absolute',
          inset: 0,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          opacity,
          transform: `translateY(${translateY}px)`,
        }}
      >
        <div
          style={{
            fontSize: 'clamp(36px, 4.5vw, 72px)',
            fontWeight: 700,
            color: '#ffffff',
            letterSpacing: '0.02em',
            textAlign: 'center',
            textShadow: '0 2px 32px rgba(0,0,0,0.7), 0 0 12px rgba(190,232,224,0.15)',
          }}
        >
          {title}
        </div>
        {artist && (
          <>
            <div
              style={{
                width: 48,
                height: 1.5,
                background: 'rgba(255, 255, 255, 0.45)',
                margin: '18px auto',
                borderRadius: 1,
              }}
            />
            <div
              style={{
                fontSize: 'clamp(18px, 2.2vw, 36px)',
                fontWeight: 400,
                color: 'rgba(255, 255, 255, 0.72)',
                letterSpacing: '0.07em',
                textAlign: 'center',
                textShadow: '0 2px 16px rgba(0,0,0,0.6)',
              }}
            >
              {artist}
            </div>
          </>
        )}
      </div>
    </>
  );
};

const OutroFade: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();
  const t = frame / fps;
  const totalSeconds = durationInFrames / fps;
  const outroStart = totalSeconds - TIMING_CONFIG.outroSeconds;

  const opacity = interpolate(
    t,
    [outroStart, totalSeconds - 0.1],
    [0, 1],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  if (opacity <= 0) return null;

  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        background: '#000000',
        opacity,
      }}
    />
  );
};

export const LyricVideo: React.FC<LyricVideoProps> = ({
  audioSrc,
  backgroundKind,
  backgroundSrc,
  lyrics,
  title,
  artist,
  vertical = false,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const timeSeconds = frame / fps;
  const activeIndex = findActiveIndex(lyrics, timeSeconds);
  const prevLine = activeIndex > 0 ? lyrics[activeIndex - 1] : undefined;
  const activeLine = activeIndex >= 0 ? lyrics[activeIndex] : undefined;
  const nextLine = activeIndex >= 0 ? lyrics[activeIndex + 1] : undefined;

  return (
    <AbsoluteFill
      style={{
        fontFamily: FONT_FAMILY,
        overflow: 'hidden',
      }}
    >
      <Html5Audio src={staticFile(audioSrc)} />
      <AnimatedBackground backgroundKind={backgroundKind} backgroundSrc={backgroundSrc} />
      <MusicWaveform audioSrc={audioSrc} vertical={vertical} />
      <LyricDisplay prev={prevLine} current={activeLine} next={nextLine} vertical={vertical} />
      <OutroFade />
      {title !== null && (
        <Sequence durationInFrames={Math.ceil(TIMING_CONFIG.introSeconds * fps)}>
          <IntroOverlay title={title} artist={artist ?? ''} />
        </Sequence>
      )}
    </AbsoluteFill>
  );
};
