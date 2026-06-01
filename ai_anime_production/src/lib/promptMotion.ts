import {interpolate} from 'remotion';

export type PromptMotion = {
  scale: number;
  x: number;
  y: number;
  rotate: number;
  contrast: number;
  saturation: number;
  pulse: number;
  glow: number;
  fade: number;
  vignette: number;
  streakX: number;
  grain: number;
};

type Options = {
  frame: number;
  durationInFrames: number;
  fps: number;
  bpm: number;
  prompt: string;
  movement: string;
  cameraDirection: string;
  intensity: string;
};

const includesAny = (text: string, keywords: string[]) => keywords.some((keyword) => text.includes(keyword));

const intensityAmount = (value: string) => {
  const text = value.toLowerCase();
  if (includesAny(text, ['emotional peak', 'peak'])) {
    return 1.35;
  }
  if (includesAny(text, ['medium-high', 'high'])) {
    return 1.15;
  }
  if (includesAny(text, ['medium'])) {
    return 1;
  }
  if (includesAny(text, ['falling', 'low', 'subtle'])) {
    return 0.7;
  }
  return 0.9;
};

const beatAmount = (value: string) => {
  const text = value.toLowerCase();
  if (includesAny(text, ['emotional peak', 'peak'])) {
    return 0.75;
  }
  if (includesAny(text, ['medium-high', 'high'])) {
    return 0.55;
  }
  if (includesAny(text, ['medium'])) {
    return 0.38;
  }
  if (includesAny(text, ['falling', 'low', 'subtle'])) {
    return 0.14;
  }
  return 0.25;
};

export const getPromptMotion = ({
  frame,
  durationInFrames,
  fps,
  bpm,
  prompt,
  movement,
  cameraDirection,
  intensity,
}: Options): PromptMotion => {
  const text = `${prompt} ${movement} ${cameraDirection}`.toLowerCase();
  const amount = intensityAmount(`${intensity} ${text}`);
  const beatStrength = beatAmount(`${intensity} ${text}`);
  const endFrame = Math.max(1, durationInFrames - 1);
  const progress = interpolate(frame, [0, endFrame], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const pushIn = includesAny(text, ['push-in', 'push in', 'dolly forward', 'forward dolly', 'zoom in']);
  const pullback = includesAny(text, ['pullback', 'pull back', 'pull-out', 'pull out', 'zoom out']);
  const lateral = includesAny(text, ['lateral', 'tracking', 'track', 'pan']);
  const tilt = includesAny(text, ['tilt']);
  const handheld = includesAny(text, ['handheld', 'shake']);
  const beat = includesAny(text, ['beat', 'strobing', 'pulse', 'impact flashes', 'drum accents']);
  const close = includesAny(text, ['close-up', 'close up', 'intimate']);
  const neon = includesAny(text, ['neon', 'cyber', 'crimson', 'magenta', 'pink']);
  const dark = includesAny(text, ['dark', 'near-black', 'graphite', 'shadow']);

  // Ken Burns: linear interpolation — smooth, consistent motion throughout the full clip.
  // spring() was removed because overdamped config (damping:140) front-loaded 98% of motion
  // into the first 40% of the clip, making the rest appear static.
  const zoomRange = ((pushIn || pullback ? 0.18 : 0.10) + (close ? 0.06 : 0)) * amount;
  const scale = interpolate(
    progress,
    [0, 1],
    [pullback ? 1.0 + zoomRange : 1.0, pullback ? 1.0 : 1.0 + zoomRange],
  );

  const lateralPx = lateral ? 90 * amount : 50 * amount;
  const x = interpolate(progress, [0, 1], [-lateralPx / 2, lateralPx / 2]);
  const y = tilt ? interpolate(progress, [0, 1], [40 * amount, -40 * amount]) : 0;

  const beatHz = bpm / 60;
  const fadeDuration = Math.max(6, Math.round((60 / bpm) * fps));

  const jitter = handheld ? Math.sin(frame * 1.7) * 2.2 * amount : 0;
  const rawBeatPulse = beat ? Math.max(0, Math.sin((frame / fps) * Math.PI * 2 * beatHz)) : 0;
  const beatPulse = rawBeatPulse * rawBeatPulse * beatStrength;
  const fadeIn = interpolate(frame, [0, Math.min(fadeDuration, endFrame)], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const fadeOut = interpolate(frame, [Math.max(0, endFrame - fadeDuration), endFrame], [1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return {
    scale: scale + beatPulse * 0.002 * amount,
    x: x + jitter,
    y: y + jitter * 0.55,
    rotate: handheld ? Math.sin(frame * 0.35) * 0.16 * amount : 0,
    contrast: 1.02 + beatPulse * 0.02 * amount,
    saturation: 1.01 + beatPulse * 0.015 * amount,
    pulse: beatPulse,
    glow: 0.08 + beatPulse * 0.06 * amount,
    fade: Math.min(fadeIn, fadeOut),
    vignette: dark ? 0.82 : 0.68,
    streakX: interpolate(progress, [0, 1], [-120, 120]) + beatPulse * 12 * amount,
    grain: neon ? 0.12 : 0.075,
  };
};
