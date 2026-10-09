/** Build a bounded, non-saturating zoom/pan filter for a still-image background. */
export function continuousZoompanFilter(settings, motion) {
  const cycleFrames = settings.fps * motion.zoomPeriodSeconds;
  const zoom = `1+${motion.zoomAmplitude}*(0.5-0.5*cos(2*PI*on/${cycleFrames}))`;
  const x = `(iw-iw/zoom)/2+((iw-iw/zoom)/2)*0.6*sin(2*PI*on/${Math.round(cycleFrames * 1.3)})`;
  const y = `(ih-ih/zoom)/2+((ih-ih/zoom)/2)*0.4*cos(2*PI*on/${Math.round(cycleFrames * 1.7)})`;
  return `zoompan=z='${zoom}':x='${x}':y='${y}':d=1:s=${settings.width}x${settings.height}:fps=${settings.fps}`;
}
