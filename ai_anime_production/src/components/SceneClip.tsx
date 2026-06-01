import React from 'react';
import {
  AbsoluteFill,
  Html5Video,
  Img,
  interpolate,
  staticFile,
  useCurrentFrame,
} from 'remotion';
import {RenderScene} from '../data/manifest';
import {getPromptMotion} from '../lib/promptMotion';

type Props = {
  scene: RenderScene;
  fps: number;
  bpm: number;
};

export const SceneClip: React.FC<Props> = ({scene, fps, bpm}) => {
  const frame = useCurrentFrame();
  const promptText = scene.selected_video_prompt || '';
  const visual = getVirtualShot({
    frame,
    durationInFrames: scene.duration_frames,
    prompt: promptText,
  });
  const motion = getPromptMotion({
    frame,
    durationInFrames: scene.duration_frames,
    fps,
    bpm,
    prompt: promptText,
    movement: scene.movement,
    cameraDirection: scene.camera_direction,
    intensity: scene.intensity,
  });

  if (scene.video_exists) {
    return (
      <AbsoluteFill style={{opacity: motion.fade}}>
        <Html5Video
          src={staticFile(scene.video)}
          muted
          loop
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'cover',
          }}
        />
        <LookOverlay motion={motion} frame={frame} fps={fps} prompt={promptText} />
      </AbsoluteFill>
    );
  }

  if (scene.image_exists) {
    return (
      <AbsoluteFill style={{overflow: 'hidden', backgroundColor: '#050509', opacity: motion.fade}}>
        <Img
          src={staticFile(scene.image)}
          style={{
            position: 'absolute',
            inset: '-8%',
            width: '116%',
            height: '116%',
            objectFit: 'cover',
            transform: visual.backgroundTransform,
            filter: 'blur(16px) saturate(1.08) contrast(1.05)',
            opacity: 0.38,
          }}
        />
        <Img
          src={staticFile(scene.image)}
          style={{
            position: 'absolute',
            inset: 0,
            width: '100%',
            height: '100%',
            objectFit: 'cover',
            transform: visual.mainTransform,
            filter: `contrast(${motion.contrast}) saturate(${motion.saturation})`,
          }}
        />
        <Img
          src={staticFile(scene.image)}
          style={{
            position: 'absolute',
            inset: 0,
            width: '100%',
            height: '100%',
            objectFit: 'cover',
            transform: visual.closeTransform,
            filter: `contrast(${motion.contrast + 0.04}) saturate(${motion.saturation + 0.05})`,
            opacity: visual.closeOpacity,
            mixBlendMode: 'normal',
          }}
        />
        <div
          style={{
            position: 'absolute',
            inset: 0,
            background: 'rgba(255,255,255,0.10)',
            opacity: visual.cutWash,
            pointerEvents: 'none',
          }}
        />
        <LookOverlay motion={motion} frame={frame} fps={fps} prompt={promptText} />
      </AbsoluteFill>
    );
  }

  return (
    <AbsoluteFill
      style={{
        alignItems: 'center',
        justifyContent: 'center',
        background: 'linear-gradient(135deg, #050509 0%, #1a0b1c 55%, #2b0712 100%)',
        color: 'white',
        fontFamily: 'Arial, sans-serif',
        opacity: interpolate(frame, [0, 18], [0, 1], {
          extrapolateLeft: 'clamp',
          extrapolateRight: 'clamp',
        }),
      }}
    >
      <div style={{fontSize: 42, fontWeight: 700}}>{scene.section}</div>
      <div style={{marginTop: 18, fontSize: 24, opacity: 0.72}}>{scene.slug}</div>
    </AbsoluteFill>
  );
};

const clamp01 = (value: number) => Math.max(0, Math.min(1, value));
const smooth = (value: number) => {
  const t = clamp01(value);
  return t * t * (3 - 2 * t);
};

const fadeWindow = (progress: number, start: number, end: number) => {
  const fadeIn = smooth((progress - start) / 0.08);
  const fadeOut = 1 - smooth((progress - end) / 0.08);
  return clamp01(Math.min(fadeIn, fadeOut));
};

const getVirtualShot = ({
  frame,
  durationInFrames,
  prompt,
}: {
  frame: number;
  durationInFrames: number;
  prompt: string;
}) => {
  const endFrame = Math.max(1, durationInFrames - 1);
  const progress = clamp01(frame / endFrame);
  const push = hasAny(prompt, ['push-in', 'push in', 'push/pull', 'camera push']);
  const wide = hasAny(prompt, ['wide establishing', 'establishing']);
  const close = hasAny(prompt, ['close-up', 'close up', 'medium shot', 'medium close']);

  const first = smooth(progress / 0.34);
  const middle = smooth((progress - 0.34) / 0.33);
  const final = smooth((progress - 0.67) / 0.33);
  const phraseDrift = Math.sin(progress * Math.PI * 2);

  const baseZoom = wide ? 1.02 : 1.08;
  const pushZoom = push ? 0.18 : 0.12;
  const mainScale =
    progress < 0.34
      ? baseZoom + first * pushZoom
      : progress < 0.67
        ? 1.12 + middle * 0.12
        : 1.2 - final * 0.08;
  const mainX =
    progress < 0.34
      ? -36 + first * 52
      : progress < 0.67
        ? 28 - middle * 58
        : -24 + final * 44;
  const mainY =
    progress < 0.34
      ? 14 - first * 24
      : progress < 0.67
        ? -18 + middle * 12
        : -8 - final * 16;

  const closeOpacity = fadeWindow(progress, 0.28, 0.72) * (close ? 0.62 : 0.48);
  const closeScale = 1.34 + middle * 0.12 - final * 0.04;
  const closeX = -44 + middle * 56 + phraseDrift * 5;
  const closeY = -26 + middle * 18;

  const cutWash =
    Math.max(
      0,
      1 - Math.abs(progress - 0.34) / 0.018,
      1 - Math.abs(progress - 0.67) / 0.018,
    ) * 0.22;

  return {
    backgroundTransform: `translate3d(${-mainX * 0.25}px, ${-mainY * 0.25}px, 0) scale(${1.08 + progress * 0.08})`,
    mainTransform: `translate3d(${mainX}px, ${mainY}px, 0) scale(${mainScale})`,
    closeTransform: `translate3d(${closeX}px, ${closeY}px, 0) scale(${closeScale})`,
    closeOpacity,
    cutWash,
  };
};

const colorFromPrompt = (prompt: string) => {
  const text = prompt.toLowerCase();
  if (text.includes('coral') || text.includes('orange') || text.includes('rose-gold')) {
    return {main: '255,118,64', second: '255,210,168', name: 'coral'};
  }
  if (text.includes('amber') || text.includes('gold')) {
    return {main: '255,188,64', second: '94,210,255', name: 'amber'};
  }
  if (text.includes('crimson') || text.includes('red')) {
    return {main: '255,38,82', second: '88,210,255', name: 'crimson'};
  }
  if (text.includes('cyan') || text.includes('blue')) {
    return {main: '88,210,255', second: '255,255,255', name: 'cyan'};
  }
  return {main: '255,0,96', second: '0,200,255', name: 'magenta'};
};

const hasAny = (prompt: string, words: string[]) => {
  const text = prompt.toLowerCase();
  return words.some((word) => text.includes(word));
};

const LookOverlay: React.FC<{
  motion: ReturnType<typeof getPromptMotion>;
  frame: number;
  fps: number;
  prompt: string;
}> = ({motion, frame, fps, prompt}) => {
  const pulse = motion.pulse;
  const glow = motion.glow;
  const color = colorFromPrompt(prompt);
  const remotionPlan = prompt.toLowerCase().includes('layer plan') || prompt.toLowerCase().includes('animation plan');
  const reflections = hasAny(prompt, ['reflection', 'wet', 'bass pulses']);
  const motif = hasAny(prompt, ['motif', 'particle', 'memory', 'lyric note', 'waveform']);
  const fracture = hasAny(prompt, ['fracture', 'crimson', 'sharp']);
  const phrasePulse = (Math.sin((frame / fps) * Math.PI * 2 * 0.5) + 1) / 2;
  const slowDrift = frame / Math.max(1, fps);

  return (
    <>
      <AbsoluteFill
        style={{
          pointerEvents: 'none',
          background:
            `radial-gradient(circle at 50% 48%, rgba(255,255,255,${0.018 + pulse * 0.015}), transparent 36%), linear-gradient(90deg, rgba(${color.main},${0.055 + glow * 0.12}), transparent 32%, transparent 72%, rgba(${color.second},0.045))`,
          boxShadow: `inset 0 0 180px rgba(0,0,0,${motion.vignette}), inset 0 0 ${50 + pulse * 70}px rgba(${color.main},${glow})`,
          mixBlendMode: 'screen',
        }}
      />
      {remotionPlan ? (
        <AbsoluteFill
          style={{
            pointerEvents: 'none',
            background:
              `linear-gradient(180deg, rgba(8,4,14,0.28), transparent 28%, transparent 68%, rgba(8,4,14,0.36)), radial-gradient(circle at ${48 + Math.sin(slowDrift * 0.35) * 8}% ${58 + Math.cos(slowDrift * 0.25) * 5}%, rgba(${color.main},${0.08 + phrasePulse * 0.04}), transparent 42%)`,
            mixBlendMode: 'overlay',
            opacity: 0.86,
          }}
        />
      ) : null}
      {reflections ? (
        <AbsoluteFill
          style={{
            pointerEvents: 'none',
            top: '58%',
            height: '42%',
            background:
              `repeating-linear-gradient(${88 + Math.sin(slowDrift) * 2}deg, transparent 0px, transparent 18px, rgba(${color.main},${0.08 + pulse * 0.06}) 19px, transparent 22px), linear-gradient(180deg, transparent, rgba(${color.second},0.08))`,
            filter: `blur(${1.2 + phrasePulse * 0.8}px)`,
            mixBlendMode: 'screen',
            opacity: 0.48,
            transform: `translate3d(${Math.sin(slowDrift * 1.2) * 14}px, ${Math.cos(slowDrift * 0.9) * 6}px, 0)`,
          }}
        />
      ) : null}
      {motif ? (
        <MotifLayer color={color.main} frame={frame} fps={fps} pulse={pulse} />
      ) : null}
      {fracture ? (
        <AbsoluteFill
          style={{
            pointerEvents: 'none',
            background:
              `linear-gradient(118deg, transparent 0%, transparent ${36 + Math.sin(slowDrift * 0.7) * 4}%, rgba(${color.main},${0.08 + pulse * 0.08}) 45%, transparent 47%, transparent 100%), linear-gradient(64deg, transparent 0%, transparent 61%, rgba(${color.main},0.06) 63%, transparent 66%)`,
            mixBlendMode: 'screen',
            opacity: 0.55,
          }}
        />
      ) : null}
      <AbsoluteFill
        style={{
          pointerEvents: 'none',
          background:
            `linear-gradient(105deg, transparent 0%, transparent 40%, rgba(255,255,255,${0.025 + pulse * 0.035}) 49%, transparent 59%, transparent 100%)`,
          mixBlendMode: 'screen',
          opacity: 0.42,
          transform: `translate3d(${motion.streakX}px, 0, 0)`,
        }}
      />
      <AbsoluteFill
        style={{
          pointerEvents: 'none',
          background:
            'repeating-linear-gradient(0deg, rgba(255,255,255,0.035) 0px, rgba(255,255,255,0.035) 1px, transparent 1px, transparent 4px)',
          mixBlendMode: 'overlay',
          opacity: motion.grain,
        }}
      />
      <AbsoluteFill
        style={{
          pointerEvents: 'none',
          borderTop: '58px solid rgba(0,0,0,0.58)',
          borderBottom: '58px solid rgba(0,0,0,0.58)',
          boxSizing: 'border-box',
        }}
      />
    </>
  );
};

const MotifLayer: React.FC<{color: string; frame: number; fps: number; pulse: number}> = ({
  color,
  frame,
  fps,
  pulse,
}) => {
  const time = frame / Math.max(1, fps);
  const particles = Array.from({length: 18}, (_, index) => {
    const x = (index * 37) % 100;
    const y = 18 + ((index * 23) % 64);
    const drift = Math.sin(time * (0.35 + index * 0.01) + index) * 18;
    const rise = ((time * (6 + (index % 4)) + index * 13) % 100) / 100;
    return (
      <div
        key={index}
        style={{
          position: 'absolute',
          left: `${x}%`,
          top: `${y - rise * 18}%`,
          width: 2 + (index % 3),
          height: 14 + (index % 5) * 3,
          borderRadius: 999,
          background: `rgba(${color},${0.18 + pulse * 0.2})`,
          boxShadow: `0 0 ${10 + pulse * 18}px rgba(${color},0.55)`,
          opacity: 0.26 + ((index % 5) * 0.035),
          transform: `translate3d(${drift}px, 0, 0) rotate(${index * 17}deg)`,
        }}
      />
    );
  });

  return (
    <AbsoluteFill
      style={{
        pointerEvents: 'none',
        overflow: 'hidden',
        mixBlendMode: 'screen',
      }}
    >
      {particles}
      <div
        style={{
          position: 'absolute',
          left: '8%',
          right: '8%',
          bottom: '16%',
          height: 56,
          opacity: 0.22 + pulse * 0.14,
          background: `repeating-linear-gradient(90deg, rgba(${color},0.0) 0px, rgba(${color},0.0) 12px, rgba(${color},0.55) 13px, rgba(${color},0.08) 16px)`,
          clipPath:
            'polygon(0 55%, 6% 45%, 12% 62%, 18% 35%, 25% 58%, 31% 42%, 38% 65%, 45% 40%, 51% 55%, 58% 34%, 64% 64%, 71% 48%, 78% 61%, 85% 38%, 92% 58%, 100% 48%, 100% 100%, 0 100%)',
          filter: 'blur(0.4px)',
        }}
      />
    </AbsoluteFill>
  );
};
