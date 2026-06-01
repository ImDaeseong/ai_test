export function typographyStartFor(textAnimation: string, aspectRatio: string) {
  const animation = textAnimation.toLowerCase();
  const verticalOffset = aspectRatio === '9:16' ? 120 : 80;

  if (animation.includes('slide')) {
    return {x: 0, y: verticalOffset, scale: 0.96, blur: 10};
  }

  if (animation.includes('scale')) {
    return {x: 0, y: 0, scale: 0.86, blur: 6};
  }

  return {x: 0, y: 40, scale: 0.98, blur: 8};
}

export function typographyTargetFor(textAnimation: string) {
  const animation = textAnimation.toLowerCase();
  return {
    x: 0,
    y: 0,
    scale: animation.includes('breathing') ? 1.015 : 1,
    blur: 0
  };
}

export function transitionDurationFor(transition: string, duration: number) {
  const normalized = transition.toLowerCase();
  const cap = Math.max(0.2, Math.min(0.6, duration * 0.18));

  if (normalized.includes('quick')) {
    return Math.min(0.28, cap);
  }

  if (normalized.includes('fade')) {
    return Math.min(0.5, cap);
  }

  return cap;
}

export function cameraOffsetFor(camera: string, aspectRatio: string): [number, number] {
  const normalized = camera.toLowerCase();
  const distance = aspectRatio === '9:16' ? 36 : 48;

  if (normalized.includes('lateral')) {
    return [distance, 0];
  }

  if (normalized.includes('pull-back')) {
    return [0, -distance * 0.5];
  }

  return [0, distance * 0.35];
}
