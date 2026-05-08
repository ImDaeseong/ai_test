import React from 'react';
import {
  AbsoluteFill,
  Audio,
  Img,
  interpolate,
  staticFile,
  Video,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import type {LyricLine} from './parsers';

export type BackgroundKind = 'none' | 'image' | 'video';

export interface LyricVideoProps extends Record<string, unknown> {
  readonly audioSrc: string;
  readonly backgroundKind: BackgroundKind;
  readonly backgroundSrc: string | null;
  readonly lyrics: LyricLine[];
}

const findActiveIndex = (lyrics: readonly LyricLine[], timeSeconds: number): number => {
  const exact = lyrics.findIndex((line) => timeSeconds >= line.start && timeSeconds < line.end);
  if (exact !== -1) {
    return exact;
  }

  const nextIndex = lyrics.findIndex((line) => timeSeconds < line.start);
  return Math.max(0, nextIndex === -1 ? lyrics.length - 1 : nextIndex - 1);
};

const useLineStyle = (line: LyricLine | undefined) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  if (!line) {
    return {
      opacity: 0,
      transform: 'translateY(0px)',
      filter: 'blur(2px)',
    };
  }

  const timeSeconds = frame / fps;
  const fadeSeconds = Math.min(0.24, Math.max(0.08, (line.end - line.start) * 0.18));
  const opacity = interpolate(
    timeSeconds,
    [line.start, line.start + fadeSeconds, line.end - fadeSeconds, line.end],
    [0, 1, 1, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );
  const blur = interpolate(opacity, [0, 1], [1.4, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return {
    opacity,
    transform: 'translateY(0px)',
    filter: `blur(${blur}px)`,
  };
};

const LyricSlot: React.FC<{
  readonly line: LyricLine | undefined;
}> = ({line}) => {
  const style = useLineStyle(line);

  return (
    <div
      style={{
        position: 'absolute',
        width: 'min(1260px, 90vw)',
        minHeight: 70,
        left: '50%',
        top: '77%',
        marginTop: -35,
        marginLeft: 'calc(min(1260px, 90vw) / -2)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        textAlign: 'center',
        color: '#ffffff',
        fontSize: 'clamp(24px, 2.8vw, 44px)',
        lineHeight: 1.18,
        fontWeight: 720,
        textWrap: 'balance',
        overflowWrap: 'anywhere',
        textShadow: '0 0 14px rgba(198, 232, 224, 0.22), 0 7px 24px rgba(0, 0, 0, 0.6)',
        willChange: 'transform, opacity, filter',
        ...style,
      }}
    >
      {line?.text ?? ''}
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
        <Video
          src={staticFile(backgroundSrc)}
          muted
          volume={0}
          loop
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
          background:
            'linear-gradient(135deg, #121820 0%, #19242b 46%, #151a22 100%)',
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

const MusicWaveform: React.FC = () => {
  const frame = useCurrentFrame();
  const width = 260;
  const height = 86;
  const centerY = height / 2;
  const samples = 120;
  const spikes = Array.from({length: 56}, (_, index) => index);
  const particles = Array.from({length: 10}, (_, index) => index);

  const amplitudeAt = (index: number): number => {
    const x = index / (samples - 1);
    const leftCluster = Math.exp(-Math.pow((x - 0.16) / 0.1, 2));
    const middleCluster = Math.exp(-Math.pow((x - 0.44) / 0.12, 2));
    const rightCluster = Math.exp(-Math.pow((x - 0.82) / 0.13, 2));
    const envelope = 0.18 + leftCluster * 0.48 + middleCluster * 0.28 + rightCluster * 0.22;
    const wave =
      Math.sin(index * 0.34 + frame * 0.2) * 0.5 +
      Math.sin(index * 0.93 - frame * 0.13) * 0.28 +
      Math.sin(index * 1.72 + frame * 0.07) * 0.16;

    return wave * envelope;
  };

  const linePoints = Array.from({length: samples}, (_, index) => {
    const x = (index / (samples - 1)) * width;
    const y = centerY + amplitudeAt(index) * 25;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(' ');

  return (
    <div
      style={{
        position: 'absolute',
        left: '50%',
        top: '82.7%',
        width,
        height,
        marginLeft: -130,
        opacity: 0.68,
      }}
    >
      <svg
        viewBox={`0 0 ${width} ${height}`}
        width="100%"
        height="100%"
        preserveAspectRatio="none"
        style={{
          overflow: 'visible',
        }}
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
        {spikes.map((spike) => {
          const sampleIndex = Math.floor((spike / (spikes.length - 1)) * (samples - 1));
          const x = (spike / (spikes.length - 1)) * width;
          const amplitude = Math.abs(amplitudeAt(sampleIndex));
          const jitter = Math.sin(spike * 2.1 + frame * 0.11) * 3;
          const spikeHeight = 6 + amplitude * 42 + Math.max(0, jitter);

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
        {particles.map((particle) => {
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

export const LyricVideo: React.FC<LyricVideoProps> = ({
  audioSrc,
  backgroundKind,
  backgroundSrc,
  lyrics,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const timeSeconds = frame / fps;
  const activeIndex = findActiveIndex(lyrics, timeSeconds);
  const activeLine = lyrics[activeIndex];

  return (
    <AbsoluteFill
      style={{
        fontFamily:
          'Inter, Pretendard, "Noto Sans KR", "Noto Sans JP", "Apple SD Gothic Neo", "Malgun Gothic", system-ui, sans-serif',
        overflow: 'hidden',
      }}
    >
      <Audio src={staticFile(audioSrc)} />
      <AnimatedBackground backgroundKind={backgroundKind} backgroundSrc={backgroundSrc} />
      <MusicWaveform />
      <LyricSlot line={activeLine} />
    </AbsoluteFill>
  );
};
